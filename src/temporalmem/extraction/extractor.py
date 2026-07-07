from __future__ import annotations

import anthropic

from ..config import settings
from ..sources.base import Episode
from .schemas import Extraction

SYSTEM_PROMPT = """You extract long-term memory from one chat session between a user and an assistant.

Rules:
- The human speaker is always the entity "user".
- Extract durable information worth remembering: preferences, relationships, possessions,
  life events, plans, opinions the user states about themselves and their world.
- Skip chit-chat, assistant boilerplate, and generic knowledge that isn't about the user's world.
- Resolve relative dates ("last month", "next Friday") against the session date into absolute
  ISO dates, both in the fact sentence and in valid_at.
- Every fact's subject and object should also appear in entities, unless the object is a plain
  literal value (a number, a date, a title).
- Prefer several small atomic facts over one compound fact."""


class Extractor:
    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = settings.extraction_model,
    ):
        self.client = client or anthropic.Anthropic()
        self.model = model

    def extract(self, episode: Episode) -> Extraction:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Session date: {episode.occurred_at.isoformat()}\n\n"
                        f"Session transcript:\n{episode.text()}"
                    ),
                }
            ],
            output_format=Extraction,
        )
        return response.parsed_output
