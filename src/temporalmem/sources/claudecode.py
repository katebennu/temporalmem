"""EpisodeSource over Claude Code session transcripts (~/.claude/projects/<project>/*.jsonl).

Keeps only the conversation a human could read back: user and assistant text turns.
Tool calls/results, thinking blocks, sidechain (subagent) traffic, meta records, and
system-injected user messages are all dropped.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .base import Episode, Turn

# User messages injected by the harness rather than typed by the human.
SYSTEM_INJECTED_PREFIXES = (
    "<command-name>",
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<system-reminder>",
    "[SYSTEM NOTIFICATION",
    "Caveat: The messages below",
)

DEFAULT_MAX_CHARS = 20_000
TRUNCATION_MARKER = "\n… [truncated]"


def _text_of(record: dict) -> str | None:
    """Human-readable text of a user/assistant record, or None if it has none."""
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return content.strip() or None
    if not isinstance(content, list):
        return None
    parts = [
        block["text"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
    ]
    text = "\n".join(parts).strip()
    return text or None


def _is_conversational(record: dict) -> bool:
    if record.get("type") not in ("user", "assistant"):
        return False
    if record.get("isMeta") or record.get("isSidechain"):
        return False
    return True


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class ClaudeCodeSource:
    """Yields Episodes from one session file or every ``*.jsonl`` in a directory.

    Sessions longer than ``max_chars`` of kept text split into parts at turn
    boundaries (ids ``<session_id>:p1``, ``:p2``, …), each part dated by its own
    first turn so facts inside long sessions keep meaningful valid_at fallbacks.
    """

    def __init__(self, path: str | Path, max_chars: int = DEFAULT_MAX_CHARS):
        self.path = Path(path).expanduser()
        self.max_chars = max_chars

    def episodes(self) -> Iterator[Episode]:
        for session_file in self._session_files():
            yield from self._session_episodes(session_file)

    def _session_files(self) -> list[Path]:
        if self.path.is_file():
            return [self.path]
        return sorted(self.path.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)

    def _session_episodes(self, session_file: Path) -> Iterator[Episode]:
        session_id = session_file.stem
        project = session_file.parent.name
        title: str | None = None
        turns: list[tuple[Turn, datetime | None]] = []

        with session_file.open() as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("type") == "ai-title" and record.get("aiTitle"):
                    title = record["aiTitle"]  # last one wins: titles refine mid-session
                    continue
                if not _is_conversational(record):
                    continue
                text = _text_of(record)
                if text is None:
                    continue
                role = record["type"]
                if role == "user" and text.startswith(SYSTEM_INJECTED_PREFIXES):
                    continue
                if len(text) > self.max_chars:
                    text = text[: self.max_chars] + TRUNCATION_MARKER
                turns.append((Turn(role=role, content=text), _parse_timestamp(record.get("timestamp"))))

        if not turns:
            return

        parts = self._split(turns)
        multipart = len(parts) > 1
        for index, part in enumerate(parts, start=1):
            occurred_at = next(
                (ts for _, ts in part if ts is not None),
                datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc),
            )
            yield Episode(
                id=f"{session_id}:p{index}" if multipart else session_id,
                occurred_at=occurred_at,
                turns=[turn for turn, _ in part],
                metadata={"project": project, "title": title, "part": index},
            )

    def _split(
        self, turns: list[tuple[Turn, datetime | None]]
    ) -> list[list[tuple[Turn, datetime | None]]]:
        parts: list[list[tuple[Turn, datetime | None]]] = [[]]
        size = 0
        for item in turns:
            length = len(item[0].content)
            if parts[-1] and size + length > self.max_chars:
                parts.append([])
                size = 0
            parts[-1].append(item)
            size += length
        return parts
