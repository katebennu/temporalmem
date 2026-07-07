from __future__ import annotations

from ..config import settings
from .client import GraphClient

DDL = [
    "CREATE CONSTRAINT episode_id IF NOT EXISTS FOR (e:Episode) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX entity_normalized IF NOT EXISTS FOR (n:Entity) ON (n.normalized)",
    """CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
       FOR (n:Entity) ON (n.embedding)
       OPTIONS {{indexConfig: {{`vector.dimensions`: {dims}, `vector.similarity_function`: 'cosine'}}}}""",
    """CREATE VECTOR INDEX fact_embedding IF NOT EXISTS
       FOR ()-[r:RELATES_TO]-() ON (r.embedding)
       OPTIONS {{indexConfig: {{`vector.dimensions`: {dims}, `vector.similarity_function`: 'cosine'}}}}""",
    "CREATE FULLTEXT INDEX fact_text IF NOT EXISTS FOR ()-[r:RELATES_TO]-() ON EACH [r.fact]",
    "CREATE FULLTEXT INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON EACH [n.name]",
    "CREATE FULLTEXT INDEX episode_text IF NOT EXISTS FOR (e:Episode) ON EACH [e.text]",
]


def setup_schema(graph: GraphClient, dims: int = settings.embedding_dims) -> None:
    """Idempotent: safe to run repeatedly against the same database."""
    for statement in DDL:
        graph.run(statement.format(dims=dims))
