# Design: add-memory-core

## Context

Greenfield project. Goal: a local-first agentic memory system over 1M+ tokens of conversational history, with measurable quality (LongMemEval). Reference architectures: Graphiti/Zep (temporal knowledge graph), Letta/MemGPT (agent-driven memory), Mem0. Constraints: everything local except Anthropic API calls; hobby-project budget; the code doubles as a portfolio piece, so clarity beats cleverness.

## Goals / Non-Goals

**Goals:**
- End-to-end pipeline: LongMemEval JSON → temporal knowledge graph → hybrid retrieval → agent answers → scored report
- Pluggable `EpisodeSource` so personal-data adapters are additive
- Every retrieval design decision A/B-testable against a naive RAG baseline

**Non-Goals:**
- Web UI, MCP server, memory decay, community summarization (follow-up changes)
- Multi-tenant namespacing (design for it loosely; don't build it)

## Decisions

1. **Neo4j does triple duty (graph + vector + full-text)** over Kùzu / SQLite / separate vector DB. Neo4j 5.26 LTS has native vector indexes (node and relationship properties) and Lucene full-text; one store means no cross-store consistency problems, and Cypher + Neo4j Browser are the strongest demo/portfolio assets. Kùzu rejected: archived/unmaintained since 2025. SQLite rejected: no Cypher, weaker demo value.

2. **Facts as relationships, not reified fact nodes.** `(:Entity)-[:RELATES_TO {predicate, fact, embedding, valid_at, invalid_at, episode_ids}]->(:Entity)` keeps traversal one hop per fact. Requires Neo4j ≥ 5.18 for relationship vector indexes — satisfied by 5.26. If relationship-index limits bite later, migrate to `(:Fact)` nodes in a new change.

3. **Bi-temporal via invalidation, not deletion.** Contradiction detection runs at ingest time: new fact → fetch existing facts with same subject entity + predicate → Haiku judges compatibility → incompatible facts get `invalid_at`. Judged per-predicate, not globally, to bound cost.

4. **Extraction: claude-haiku-4-5 + structured outputs (`messages.parse` with pydantic schemas); Batches API for bulk ingestion** (50% cost). claude-opus-4-8 reserved for the answering agent and (optionally) judge. Rationale: extraction is high-volume schema-filling; the agent loop is where intelligence pays.

5. **Embeddings: local sentence-transformers `BAAI/bge-small-en-v1.5` (384 dims, cosine).** Anthropic has no embeddings API; local keeps it free and offline. Dimension is fixed in the index DDL — changing models means reindexing, so the model name lives in one config constant.

6. **Rank fusion: RRF (k=60)** over learned rerankers — no training data, robust, trivially explainable. Graph expansion adds facts at attenuated score (score × decay^hops).

7. **Entity resolution: normalized-name exact match → embedding cosine ≥ threshold (default 0.85) → else create.** LLM tie-break deferred to a follow-up change; the threshold pass is cheap and covers most LongMemEval cases. Known weakness documented in Risks.

## Risks / Trade-offs

- [Extraction quality caps everything downstream] → Keep per-episode extraction inspectable (`temporalmem ingest --dry-run` prints extractions); iterate on the prompt against the oracle variant first.
- [Entity dedup drift (over- or under-merging)] → Threshold configurable; resolution decisions logged; oracle runs make dedup errors visible early.
- [Haiku contradiction judging misses paraphrase conflicts] → Scope: only same-subject+predicate pairs are compared; accept misses in v1, measure via knowledge-update question type.
- [Relationship vector index maturity] → Pin Neo4j 5.26 LTS; fallback documented (Fact nodes).
- [API cost surprises] → Batches by default for ingestion; harness defaults to 20-question subsets; token usage recorded per run.
- [LongMemEval format drift between variants] → Adapter validates required fields and fails loudly with the offending question id.

## Migration Plan

Greenfield — no migration. Rollback = drop the Neo4j volume (`docker compose down -v`).
