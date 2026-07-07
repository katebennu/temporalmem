from __future__ import annotations

from neo4j import GraphDatabase

from ..config import settings


class GraphClient:
    def __init__(
        self,
        uri: str = settings.neo4j_uri,
        user: str = settings.neo4j_user,
        password: str = settings.neo4j_password,
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def run(self, cypher: str, **params) -> list[dict]:
        with self.driver.session() as session:
            return [record.data() for record in session.run(cypher, params)]

    def close(self) -> None:
        self.driver.close()

    def __enter__(self) -> "GraphClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
