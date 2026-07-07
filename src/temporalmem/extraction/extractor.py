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
- Predicates: snake_case, present tense, and consistent — reuse the same predicate for the
  same kind of relation every time. Prefer this canonical set when it fits: owns, lives_in,
  works_at, purchased_from, plans_trip_to, plans_to_visit, visited, attended,
  participated_in, started_working_at, started_working_with, prefers, likes, dislikes,
  has_skill, has_goal, related_to.
- Extract dated life events as individual facts — one per event, with valid_at set to the
  event's date: attended/participated_in for events and activities, visited for places,
  started_working_at / started_working_with for jobs, projects, and collaborations.
  Capture start dates and first occurrences explicitly whenever mentioned; questions like
  "how long", "how many before X", and "which came first" depend on them.
- Objects must be entity names (people, places, organizations, products, events) — never
  dates, amounts, or adverbs. Put WHEN into valid_at and the details into the fact sentence.
  For acquisition or state-change events (purchases, moves, job changes), valid_at is the
  date the state began, e.g. owns + valid_at = purchase date.
- Set functional=true only when a new object would replace the old one (a person has one
  home, one employer); functional=false when multiple objects can hold at once (owns,
  visited, purchased_from).
- Every fact's subject and object should also appear in entities, unless the object is a plain
  literal value (a number or a title).
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
