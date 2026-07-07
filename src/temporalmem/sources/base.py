from __future__ import annotations

from datetime import datetime
from typing import Iterator, Protocol

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: str
    content: str


class Episode(BaseModel):
    """One unit of memory ingestion, e.g. a single chat session."""

    id: str
    occurred_at: datetime
    turns: list[Turn]
    metadata: dict = Field(default_factory=dict)

    def text(self) -> str:
        return "\n".join(f"{turn.role}: {turn.content}" for turn in self.turns)


class EpisodeSource(Protocol):
    """Anything that can yield episodes. Downstream stages depend only on this."""

    def episodes(self) -> Iterator[Episode]: ...
