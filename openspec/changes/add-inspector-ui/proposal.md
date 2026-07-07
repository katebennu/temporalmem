# Proposal: add-inspector-ui

## Why

Debugging memory quality currently means hand-written Cypher and grepping results JSON — the run-2 regression and the ablation's over-invalidation finding were both diagnosed that way. A read-only inspector makes the system's two differentiators visible (fact validity over time, the agent's tool trace) and turns eval iteration into a browsing task instead of a scripting task.

## What Changes

- Streamlit app (`src/temporalmem/inspector.py`, `ui` dependency group) with four tabs:
  - **Ask** — question + optional date → agent answer plus full tool trace (every search/inspect call with inputs and what came back)
  - **Search** — hybrid retrieval results with scores, validity windows, and source-episode drill-down
  - **Timeline** — per-entity fact-validity bars (valid_at → invalid_at/now) grouped by predicate; superseded facts listed
  - **Runs** — accuracy per question type across selected results files (ablation arms side by side) plus a failure browser
- `MemoryAgent.answer_traced()` — returns the answer and the tool trace; `answer()` unchanged for callers.

## Capabilities

### New Capabilities
- `inspector-ui`: read-only inspection surface over the graph, retrieval, agent, and eval results

### Modified Capabilities
- `memory-agent`: agent exposes its tool trace programmatically

## Non-goals

- No writes from the UI (ingestion/wipes stay in the CLI)
- No auth/multi-user anything — this is a local dev tool
- Not the future typed API / MCP layer; the inspector calls internal functions directly

## Impact

- New `ui` dependency group (streamlit, plotly, pandas) — core install unaffected
- Run: `uv run --group ui streamlit run src/temporalmem/inspector.py`
- Long-lived process keeps the embedding model warm — queries are sub-second after first load
