import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "temporalmem-local")

    extraction_model: str = "claude-haiku-4-5"
    agent_model: str = "claude-opus-4-8"
    judge_model: str = "claude-opus-4-8"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dims: int = 384

    invalidation_strategy: str = os.getenv("INVALIDATION_STRATEGY", "functional")
    supersession_similarity_threshold: float = 0.55
    supersession_max_candidates: int = 5

    entity_match_threshold: float = 0.85
    rrf_k: int = 60
    expansion_hops: int = 1
    expansion_decay: float = 0.5
    search_limit: int = 10


settings = Settings()
