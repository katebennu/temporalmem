from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from .config import settings
from .embeddings import Embedder
from .extraction.extractor import Extractor
from .extraction.schemas import Extraction
from .graph.client import GraphClient
from .sources.base import Episode, EpisodeSource


FUNCTIONAL_PREDICATES = {
    "lives_in": True,
    "works_at": True,
    "is_named": True,
    "owns": False,
    "purchased_from": False,
    "visited": False,
    "attended": False,
    "participated_in": False,
    "started_working_at": False,
    "started_working_with": False,
    "plans_trip_to": False,
    "plans_to_visit": False,
    "prefers": False,
    "likes": False,
    "dislikes": False,
    "has_skill": False,
    "has_goal": False,
    "recommended": False,
    "suggested": False,
    "related_to": False,
}


def is_functional(predicate: str, extracted_flag: bool) -> bool:
    """Pinned classification for the canonical vocabulary; the LLM flag decides only
    for unknown predicates (Haiku labels the flag inconsistently across sessions)."""
    return FUNCTIONAL_PREDICATES.get(predicate, extracted_flag)


INVALIDATION_STRATEGIES = {"none", "functional", "llm"}

SUPERSESSION_SYSTEM = """You decide whether a newly learned fact supersedes existing facts about
the same subject. A fact is superseded when it and the new fact cannot both be true at the same
time and the new fact reflects a change of state (moved cities, changed jobs, replaced a primary
device). Facts that can coexist — multiple possessions, repeated events, multiple purchases from
different places — are NOT superseded. When unsure, do not supersede."""


class SupersessionVerdict(BaseModel):
    superseded: list[int] = Field(
        description="Indices of existing facts that the new fact supersedes. Empty list if none."
    )


def normalize(name: str) -> str:
    return " ".join(name.lower().split())


def types_compatible(a: str | None, b: str | None) -> bool:
    """Whether two entity_type labels may refer to the same entity.
    Missing or 'other' is a wildcard; two concrete types must agree —
    prevents cross-type vector merges (a person swallowing a place)."""
    if not a or not b or a == "other" or b == "other":
        return True
    return a == b


def fact_key(subject_id: str, predicate: str, object_id: str) -> str:
    raw = f"{subject_id}|{predicate}|{object_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class Ingestor:
    """Pipeline: episodes -> extraction -> entity resolution -> temporal graph writes."""

    def __init__(
        self,
        graph: GraphClient,
        extractor: Extractor | None = None,
        embedder: Embedder | None = None,
        entity_match_threshold: float = settings.entity_match_threshold,
        strategy: str | None = None,
    ):
        self.graph = graph
        self.extractor = extractor or Extractor()
        self.embedder = embedder or Embedder()
        self.entity_match_threshold = entity_match_threshold
        self.strategy = strategy or settings.invalidation_strategy
        if self.strategy not in INVALIDATION_STRATEGIES:
            raise ValueError(
                f"unknown invalidation strategy {self.strategy!r}; expected one of {sorted(INVALIDATION_STRATEGIES)}"
            )

    def ingest(self, source: EpisodeSource, dry_run: bool = False, log=print) -> int:
        count = 0
        for episode in source.episodes():
            if not dry_run and self._already_ingested(episode.id):
                log(f"skip (already ingested): {episode.id}")
                continue
            extraction = self.extractor.extract(episode)
            if dry_run:
                log(f"--- {episode.id} ({episode.occurred_at:%Y-%m-%d}) ---")
                for fact in extraction.facts:
                    marker = "*" if is_functional(fact.predicate, fact.functional) else ""
                    log(
                        f"  ({fact.subject}) -[{fact.predicate}{marker}]-> ({fact.object})  "
                        f"valid_at={fact.valid_at or '-'}  {fact.fact}"
                    )
            else:
                self._write(episode, extraction)
                log(
                    f"ingested {episode.id}: "
                    f"{len(extraction.entities)} entities, {len(extraction.facts)} facts"
                )
            count += 1
        return count

    def _already_ingested(self, episode_id: str) -> bool:
        rows = self.graph.run("MATCH (e:Episode {id: $id}) RETURN e.id AS id", id=episode_id)
        return bool(rows)

    def _write(self, episode: Episode, extraction: Extraction) -> None:
        self.graph.run(
            """MERGE (e:Episode {id: $id})
               SET e.occurred_at = datetime($occurred_at), e.text = $text""",
            id=episode.id,
            occurred_at=episode.occurred_at.isoformat(),
            text=episode.text(),
        )

        entity_ids: dict[str, str] = {}
        names = {entity.name for entity in extraction.entities}
        names |= {fact.subject for fact in extraction.facts}
        names |= {fact.object for fact in extraction.facts}
        summaries = {entity.name: entity.summary for entity in extraction.entities}
        types = {entity.name: entity.entity_type for entity in extraction.entities}

        for name in names:
            embedding = self.embedder.embed_one(name)
            entity_id = self._resolve_entity(name, embedding, types.get(name, "other"))
            entity_ids[name] = entity_id
            self.graph.run(
                """MERGE (n:Entity {id: $id})
                   ON CREATE SET n.name = $name, n.normalized = $normalized,
                                 n.embedding = $embedding, n.entity_type = $entity_type
                   SET n.summary = coalesce($summary, n.summary)""",
                id=entity_id,
                name=name,
                normalized=normalize(name),
                embedding=embedding,
                entity_type=types.get(name, "other"),
                summary=summaries.get(name),
            )
            self.graph.run(
                """MATCH (e:Episode {id: $episode_id}), (n:Entity {id: $entity_id})
                   MERGE (e)-[:MENTIONS]->(n)""",
                episode_id=episode.id,
                entity_id=entity_id,
            )

        for fact in extraction.facts:
            subject_id = entity_ids[fact.subject]
            object_id = entity_ids[fact.object]
            valid_at = self._fact_valid_at(fact.valid_at, episode.occurred_at)
            key = fact_key(subject_id, fact.predicate, object_id)
            fact_embedding = self.embedder.embed_one(fact.fact)
            if self.strategy == "functional":
                if is_functional(fact.predicate, fact.functional):
                    self._invalidate_contradictions(subject_id, fact.predicate, object_id, valid_at)
            elif self.strategy == "llm":
                self._invalidate_llm(subject_id, object_id, fact.fact, fact_embedding, valid_at)
            self.graph.run(
                """MATCH (s:Entity {id: $subject_id}), (o:Entity {id: $object_id})
                   MERGE (s)-[r:RELATES_TO {key: $key}]->(o)
                   ON CREATE SET r.predicate = $predicate, r.fact = $fact,
                                 r.embedding = $embedding,
                                 r.valid_at = datetime($valid_at), r.invalid_at = null,
                                 r.episode_ids = [$episode_id]
                   ON MATCH SET r.episode_ids = CASE
                       WHEN $episode_id IN r.episode_ids THEN r.episode_ids
                       ELSE r.episode_ids + $episode_id END""",
                subject_id=subject_id,
                object_id=object_id,
                key=key,
                predicate=fact.predicate,
                fact=fact.fact,
                embedding=fact_embedding,
                valid_at=valid_at.isoformat(),
                episode_id=episode.id,
            )

    def _fact_valid_at(self, stated: str | None, fallback: datetime) -> datetime:
        if stated:
            try:
                return datetime.fromisoformat(stated)
            except ValueError:
                pass
        return fallback

    def _resolve_entity(self, name: str, embedding: list[float], entity_type: str = "other") -> str:
        rows = self.graph.run(
            "MATCH (n:Entity {normalized: $normalized}) RETURN n.id AS id LIMIT 1",
            normalized=normalize(name),
        )
        if rows:
            return rows[0]["id"]
        rows = self.graph.run(
            """CALL db.index.vector.queryNodes('entity_embedding', 3, $embedding)
               YIELD node, score
               WHERE score >= $threshold
               RETURN node.id AS id, node.entity_type AS entity_type
               ORDER BY score DESC""",
            embedding=embedding,
            threshold=self.entity_match_threshold,
        )
        for row in rows:
            if types_compatible(entity_type, row["entity_type"]):
                return row["id"]
        return uuid.uuid4().hex

    def _invalidate_llm(
        self,
        subject_id: str,
        object_id: str,
        new_fact: str,
        new_embedding: list[float],
        valid_at: datetime,
    ) -> None:
        rows = self.graph.run(
            """MATCH (s:Entity {id: $subject_id})-[r:RELATES_TO]->(o:Entity)
               WHERE o.id <> $object_id AND r.invalid_at IS NULL
                     AND r.valid_at <= datetime($valid_at)
               RETURN r.key AS key, r.fact AS fact, r.embedding AS embedding""",
            subject_id=subject_id,
            object_id=object_id,
            valid_at=valid_at.isoformat(),
        )
        scored = []
        for row in rows:
            similarity = sum(a * b for a, b in zip(new_embedding, row["embedding"]))
            if similarity >= settings.supersession_similarity_threshold:
                scored.append((similarity, row))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        candidates = [row for _, row in scored[: settings.supersession_max_candidates]]
        if not candidates:
            return
        listing = "\n".join(f"{index}. {row['fact']}" for index, row in enumerate(candidates))
        response = self.extractor.client.messages.parse(
            model=settings.extraction_model,
            max_tokens=1024,
            system=SUPERSESSION_SYSTEM,
            messages=[{"role": "user", "content": f"New fact: {new_fact}\n\nExisting facts:\n{listing}"}],
            output_format=SupersessionVerdict,
        )
        superseded_keys = [
            candidates[index]["key"]
            for index in response.parsed_output.superseded
            if 0 <= index < len(candidates)
        ]
        if superseded_keys:
            self.graph.run(
                """MATCH ()-[r:RELATES_TO]->()
                   WHERE r.key IN $keys AND r.invalid_at IS NULL
                   SET r.invalid_at = datetime($valid_at)""",
                keys=superseded_keys,
                valid_at=valid_at.isoformat(),
            )

    def _invalidate_contradictions(
        self, subject_id: str, predicate: str, object_id: str, valid_at: datetime
    ) -> None:
        self.graph.run(
            """MATCH (s:Entity {id: $subject_id})-[r:RELATES_TO {predicate: $predicate}]->(o:Entity)
               WHERE o.id <> $object_id AND r.invalid_at IS NULL
                     AND r.valid_at <= datetime($valid_at)
               SET r.invalid_at = datetime($valid_at)""",
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            valid_at=valid_at.isoformat(),
        )
