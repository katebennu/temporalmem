from __future__ import annotations

from datetime import datetime

import anthropic

from ..config import settings
from ..graph.client import GraphClient
from ..retrieval.hybrid import MemorySearch, SearchResult

SYSTEM_PROMPT = """You answer questions about a user's chat history using a long-term memory store.

- Search memory before answering. For multi-part or multi-hop questions, search multiple times
  with different phrasings; follow leads from one result into the next search.
- Answer ONLY from retrieved memory. If searches return no sufficient evidence, say the
  information is not in the history — never guess or use outside knowledge.
- The question date is provided. Resolve relative time expressions ("last month") against it.
- Facts carry validity windows (valid_at / invalid_at). Prefer facts valid at the time the
  question asks about; use as_of when the question targets a specific time.
- If the retrieved facts lack a detail the question needs — a date, a count, a duration,
  a starting point — you MUST call inspect_episodes on the source episodes of the closest
  facts and read the transcripts before concluding the information is missing. Only state
  that the history lacks the information after inspecting the most relevant episodes.
- Give a direct, concise final answer."""

TOOLS = [
    {
        "name": "search_memory",
        "description": (
            "Search the memory graph for facts relevant to a query. Returns facts with subject, "
            "predicate, object, validity dates, and source episode ids. Call this before answering, "
            "and call it again with different phrasings for multi-part questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language search query"},
                "as_of": {
                    "type": "string",
                    "description": "Optional ISO date; only return facts valid at this time",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "inspect_episodes",
        "description": (
            "Fetch the raw transcript text of episodes by id. Call this whenever the retrieved "
            "facts are missing a detail the question needs (a date, a count, a duration, a start "
            "point) or are ambiguous — the transcripts often contain details the facts do not. "
            "Do this before concluding that information is not in the history."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "episode_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["episode_ids"],
        },
    },
]


def format_results(results: list[SearchResult]) -> str:
    if not results:
        return "No matching facts in memory."
    lines = []
    for result in results:
        window = f"valid {result.valid_at or '?'} to {result.invalid_at or 'present'}"
        lines.append(
            f"- {result.fact} ({result.subject} -[{result.predicate}]-> {result.object}; "
            f"{window}; episodes: {', '.join(result.episode_ids)})"
        )
    return "\n".join(lines)


class MemoryAgent:
    def __init__(
        self,
        graph: GraphClient,
        search: MemorySearch | None = None,
        client: anthropic.Anthropic | None = None,
        model: str = settings.agent_model,
    ):
        self.graph = graph
        self.search = search or MemorySearch(graph)
        self.client = client or anthropic.Anthropic()
        self.model = model

    def answer(
        self,
        question: str,
        question_date: datetime | None = None,
        max_iterations: int = 8,
    ) -> str:
        prompt = question
        if question_date is not None:
            prompt = f"Question date: {question_date.isoformat()}\n\nQuestion: {question}"
        messages: list[dict] = [{"role": "user", "content": prompt}]

        response = None
        for _ in range(max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )
            if response.stop_reason != "tool_use":
                break
            messages.append({"role": "assistant", "content": response.content})
            tool_results = [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": self._run_tool(block.name, block.input),
                }
                for block in response.content
                if block.type == "tool_use"
            ]
            messages.append({"role": "user", "content": tool_results})

        if response is None:
            return ""
        return "\n".join(block.text for block in response.content if block.type == "text")

    def _run_tool(self, name: str, tool_input: dict) -> str:
        if name == "search_memory":
            as_of = None
            if tool_input.get("as_of"):
                try:
                    as_of = datetime.fromisoformat(tool_input["as_of"])
                except ValueError:
                    pass
            results = self.search.search(tool_input["query"], as_of=as_of)
            return format_results(results)
        if name == "inspect_episodes":
            episodes = self.search.get_episodes(tool_input["episode_ids"])
            if not episodes:
                return "No episodes found for those ids."
            return "\n\n".join(
                f"=== {episode['id']} ({episode['occurred_at']}) ===\n{episode['text']}"
                for episode in episodes
            )
        return f"Unknown tool: {name}"
