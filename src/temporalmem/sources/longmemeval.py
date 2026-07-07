from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, Field

from .base import Episode, Turn

DATE_FORMATS = [
    "%Y/%m/%d (%a) %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
]


class Question(BaseModel):
    question_id: str
    question_type: str
    question: str
    answer: str
    question_date: datetime
    answer_session_ids: list[str] = Field(default_factory=list)


def parse_date(raw: str) -> datetime:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognized LongMemEval date: {raw!r}")


class LongMemEvalSource:
    """Adapts a LongMemEval JSON file (s / m / oracle variant) to the EpisodeSource protocol.

    Each haystack session becomes one Episode; episode ids are deterministic
    ("<question_id>:<session_id>") so re-ingestion is idempotent.
    """

    def __init__(self, path: str | Path, question_ids: set[str] | None = None):
        self.path = Path(path)
        self.question_ids = question_ids
        self._instances: list[dict] | None = None

    @property
    def instances(self) -> list[dict]:
        if self._instances is None:
            with open(self.path) as f:
                self._instances = json.load(f)
        return self._instances

    def _selected(self) -> Iterator[dict]:
        for instance in self.instances:
            if self.question_ids is not None and instance["question_id"] not in self.question_ids:
                continue
            yield instance

    def episodes(self) -> Iterator[Episode]:
        for instance in self._selected():
            question_id = instance["question_id"]
            session_ids = instance["haystack_session_ids"]
            dates = instance["haystack_dates"]
            sessions = instance["haystack_sessions"]
            if not (len(session_ids) == len(dates) == len(sessions)):
                raise ValueError(f"misaligned haystack arrays for question {question_id}")
            for session_id, date, session in zip(session_ids, dates, sessions):
                yield Episode(
                    id=f"{question_id}:{session_id}",
                    occurred_at=parse_date(date),
                    turns=[Turn(role=turn["role"], content=turn["content"]) for turn in session],
                    metadata={
                        "question_id": question_id,
                        "session_id": session_id,
                        "has_answer": any(turn.get("has_answer") for turn in session),
                    },
                )

    def questions(self) -> Iterator[Question]:
        for instance in self._selected():
            yield Question(
                question_id=instance["question_id"],
                question_type=instance["question_type"],
                question=instance["question"],
                answer=str(instance["answer"]),
                question_date=parse_date(instance["question_date"]),
                answer_session_ids=[str(sid) for sid in instance.get("answer_session_ids", [])],
            )
