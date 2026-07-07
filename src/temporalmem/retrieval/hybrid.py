from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field

from ..config import settings
from ..embeddings import Embedder
from ..graph.client import GraphClient
from .fusion import rrf

FACT_FIELDS = """r.key AS key, r.fact AS fact, r.predicate AS predicate,
       s.name AS subject, o.name AS object,
       toString(r.valid_at) AS valid_at, toString(r.invalid_at) AS invalid_at,
       r.episode_ids AS episode_ids"""


class SearchResult(BaseModel):
    key: str
    fact: str
    predicate: str
    subject: str
    object: str
    valid_at: str | None = None
    invalid_at: str | None = None
    episode_ids: list[str] = Field(default_factory=list)
    score: float = 0.0
    via: str = "search"


def lucene_sanitize(query: str) -> str:
    return re.sub(r'[+\-&|!(){}\[\]^"~*?:\\/]', " ", query).strip()


class MemorySearch:
    """Hybrid retrieval: vector + full-text fused with RRF, then graph expansion from entity seeds."""

    def __init__(
        self,
        graph: GraphClient,
        embedder: Embedder | None = None,
        rrf_k: int = settings.rrf_k,
        expansion_decay: float = settings.expansion_decay,
    ):
        self.graph = graph
        self.embedder = embedder or Embedder()
        self.rrf_k = rrf_k
        self.expansion_decay = expansion_decay

    def search(
        self,
        query: str,
        as_of: datetime | None = None,
        limit: int = settings.search_limit,
    ) -> list[SearchResult]:
        embedding = self.embedder.embed_one(query)
        vector_hits = self._vector_facts(embedding, limit * 2)
        text_hits = self._fulltext_facts(query, limit * 2)

        candidates: dict[str, SearchResult] = {}
        for hit in vector_hits + text_hits:
            candidates.setdefault(hit.key, hit)

        scores = rrf(
            [[hit.key for hit in vector_hits], [hit.key for hit in text_hits]],
            k=self.rrf_k,
        )

        for rank, hit in enumerate(self._expand(embedding, limit)):
            if hit.key not in candidates:
                hit.via = "expansion"
                candidates[hit.key] = hit
            scores[hit.key] = scores.get(hit.key, 0.0) + self.expansion_decay / (self.rrf_k + rank + 1)

        results = []
        for key, result in candidates.items():
            if not self._valid_for(result, as_of):
                continue
            result.score = scores.get(key, 0.0)
            results.append(result)
        results.sort(key=lambda result: result.score, reverse=True)
        return results[:limit]

    def get_episodes(self, episode_ids: list[str]) -> list[dict]:
        return self.graph.run(
            """MATCH (e:Episode) WHERE e.id IN $ids
               RETURN e.id AS id, toString(e.occurred_at) AS occurred_at, e.text AS text""",
            ids=episode_ids,
        )

    def _valid_for(self, result: SearchResult, as_of: datetime | None) -> bool:
        if as_of is None:
            return True
        as_of_iso = as_of.isoformat()
        if result.valid_at and result.valid_at > as_of_iso:
            return False
        if result.invalid_at and result.invalid_at <= as_of_iso:
            return False
        return True

    def _vector_facts(self, embedding: list[float], limit: int) -> list[SearchResult]:
        rows = self.graph.run(
            f"""CALL db.index.vector.queryRelationships('fact_embedding', $limit, $embedding)
                YIELD relationship AS r, score
                MATCH (s:Entity)-[r]->(o:Entity)
                RETURN {FACT_FIELDS}""",
            limit=limit,
            embedding=embedding,
        )
        return [SearchResult(**row) for row in rows]

    def _fulltext_facts(self, query: str, limit: int) -> list[SearchResult]:
        sanitized = lucene_sanitize(query)
        if not sanitized:
            return []
        rows = self.graph.run(
            f"""CALL db.index.fulltext.queryRelationships('fact_text', $query)
                YIELD relationship AS r, score
                MATCH (s:Entity)-[r]->(o:Entity)
                RETURN {FACT_FIELDS}
                LIMIT $limit""",
            query=sanitized,
            limit=limit,
        )
        return [SearchResult(**row) for row in rows]

    def _expand(self, embedding: list[float], limit: int) -> list[SearchResult]:
        rows = self.graph.run(
            f"""CALL db.index.vector.queryNodes('entity_embedding', 5, $embedding)
                YIELD node AS seed, score AS seed_score
                MATCH (seed)-[r:RELATES_TO]-()
                MATCH (s:Entity)-[r]->(o:Entity)
                RETURN DISTINCT {FACT_FIELDS}
                LIMIT $limit""",
            embedding=embedding,
            limit=limit,
        )
        return [SearchResult(**row) for row in rows]
