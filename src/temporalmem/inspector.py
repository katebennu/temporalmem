"""Memory inspector — read/debug UI over the temporal graph.

Run with: uv run --group ui streamlit run src/temporalmem/inspector.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from temporalmem.agent.memory_agent import MemoryAgent
from temporalmem.graph.client import GraphClient
from temporalmem.retrieval.hybrid import MemorySearch

PALETTE = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
SURFACE = "#fcfcfb"
GRID = "#e1e0d9"
MUTED = "#898781"

st.set_page_config(page_title="temporalmem inspector", page_icon="🧠", layout="wide")


@st.cache_resource
def graph() -> GraphClient:
    return GraphClient()


@st.cache_resource
def search_engine() -> MemorySearch:
    return MemorySearch(graph())


@st.cache_resource
def agent() -> MemoryAgent:
    return MemoryAgent(graph(), search=search_engine())


def style(fig):
    fig.update_layout(
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        colorway=PALETTE,
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color="#0b0b0b"),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, tickfont=dict(color=MUTED)),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, tickfont=dict(color=MUTED)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=40, r=20),
    )
    return fig


def parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def episode_expander(episode_ids: list[str]) -> None:
    for episode in search_engine().get_episodes(episode_ids):
        with st.expander(f"episode {episode['id']} ({episode['occurred_at']})"):
            st.text(episode["text"])


def ask_tab() -> None:
    question = st.text_input("Question", placeholder="Which device did I get first, ...?")
    date_raw = st.text_input("Question date (ISO, optional)", placeholder="2023-03-15T03:53:00")
    if st.button("Ask", type="primary") and question:
        question_date = parse_dt(date_raw)
        with st.spinner("agent thinking (can take a minute)..."):
            text, trace = agent().answer_traced(question, question_date)
        st.markdown(text)
        st.subheader(f"Tool trace — {len(trace)} call(s)")
        for step, event in enumerate(trace, 1):
            with st.expander(f"{step}. {event['tool']}({json.dumps(event['input'])[:100]})"):
                st.code(event["output"], language=None)


def search_tab() -> None:
    left, mid, right = st.columns([3, 1, 1])
    query = left.text_input("Search memory", placeholder="where does the user live")
    as_of_raw = mid.text_input("as of (ISO, optional)")
    limit = right.slider("limit", 5, 50, 10)
    if not query:
        return
    results = search_engine().search(query, as_of=parse_dt(as_of_raw), limit=limit)
    if not results:
        st.info("No matching facts.")
        return
    for result in results:
        window = f"{(result.valid_at or '?')[:10]} → {(result.invalid_at or 'present')[:10]}"
        st.markdown(
            f"**{result.score:.4f}** · `{result.via}` · {result.fact}  \n"
            f"<span style='color:{MUTED}'>{result.subject} -[{result.predicate}]-> {result.object} · "
            f"valid {window}</span>",
            unsafe_allow_html=True,
        )
        episode_expander(result.episode_ids)


def timeline_tab() -> None:
    rows = graph().run(
        """MATCH (n:Entity)<-[:MENTIONS]-(e:Episode)
           RETURN n.name AS name, count(e) AS mentions ORDER BY mentions DESC LIMIT 200"""
    )
    if not rows:
        st.info("Graph is empty — ingest something first.")
        return
    entity = st.selectbox("Entity", [row["name"] for row in rows])
    facts = graph().run(
        """MATCH (s:Entity)-[r:RELATES_TO]->(o:Entity)
           WHERE s.name = $name OR o.name = $name
           RETURN s.name AS subject, r.predicate AS predicate, o.name AS object,
                  toString(r.valid_at) AS valid_at, toString(r.invalid_at) AS invalid_at,
                  r.fact AS fact, r.episode_ids AS episode_ids""",
        name=entity,
    )
    if not facts:
        st.info("No facts for this entity.")
        return
    now = datetime.now(timezone.utc)
    frame = pd.DataFrame(
        [
            {
                "predicate": fact["predicate"],
                "object": fact["object"] if fact["subject"] == entity else f"⟵ {fact['subject']}",
                "start": parse_dt(fact["valid_at"]),
                "end": parse_dt(fact["invalid_at"]) or now,
                "status": "superseded" if fact["invalid_at"] else "current",
                "fact": fact["fact"],
            }
            for fact in facts
        ]
    )
    fig = px.timeline(
        frame,
        x_start="start",
        x_end="end",
        y="predicate",
        color="object",
        text="object",
        hover_data={"fact": True, "status": True, "object": False},
        color_discrete_sequence=PALETTE,
    )
    fig.update_traces(textposition="inside", insidetextanchor="start", width=0.6)
    fig.update_layout(showlegend=False, height=max(300, 60 * frame["predicate"].nunique()))
    st.plotly_chart(style(fig), width="stretch")
    st.caption("Bar = fact validity window (valid_at → invalid_at or now). Labels carry identity; superseded facts end where their successor begins.")
    superseded = frame[frame["status"] == "superseded"]
    if not superseded.empty:
        st.markdown("**Superseded facts:**")
        st.dataframe(superseded[["predicate", "object", "start", "end", "fact"]], hide_index=True)


def runs_tab() -> None:
    paths = sorted(Path("results").glob("*.json"))
    if not paths:
        st.info("No results files yet — run `temporalmem eval` first.")
        return
    chosen = st.multiselect("Results files", [str(p) for p in paths], default=[str(p) for p in paths if "ablation" in p.name])
    if not chosen:
        return
    rows = []
    for path in chosen:
        records = json.loads(Path(path).read_text())
        label = records[0].get("strategy") if records and records[0].get("strategy") else Path(path).stem
        for record in records:
            if "correct" in record:
                rows.append({"arm": label, "question_type": record["question_type"], "correct": record["correct"]})
    if not rows:
        st.warning("Selected files have no judged records — run `temporalmem score` first.")
        return
    frame = pd.DataFrame(rows)
    accuracy = (
        frame.groupby(["arm", "question_type"])["correct"].mean().reset_index(name="accuracy")
    )
    fig = px.bar(
        accuracy,
        x="question_type",
        y="accuracy",
        color="arm",
        barmode="group",
        text=accuracy["accuracy"].map(lambda value: f"{value:.2f}"),
        color_discrete_sequence=PALETTE,
    )
    fig.update_traces(textposition="outside")
    fig.update_yaxes(range=[0, 1.1])
    st.plotly_chart(style(fig), width="stretch")
    overall = frame.groupby("arm")["correct"].agg(["mean", "count"]).rename(columns={"mean": "accuracy", "count": "n"})
    st.dataframe(overall.round(3))

    st.subheader("Failure browser")
    target = st.selectbox("File", chosen)
    for record in json.loads(Path(target).read_text()):
        if record.get("correct") is False:
            with st.expander(f"[{record['question_type']}] {record['question'][:90]}"):
                st.markdown(f"**gold:** {record['gold']}")
                st.markdown(f"**hypothesis:** {record['hypothesis']}")


def main() -> None:
    st.title("temporalmem inspector")
    tab_ask, tab_search, tab_timeline, tab_runs = st.tabs(["Ask", "Search", "Timeline", "Runs"])
    with tab_ask:
        ask_tab()
    with tab_search:
        search_tab()
    with tab_timeline:
        timeline_tab()
    with tab_runs:
        runs_tab()


main()
