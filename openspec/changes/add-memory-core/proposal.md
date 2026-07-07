# Proposal: add-memory-core

## Why

Agent memory beyond a context window is an unsolved-in-practice problem: 1M+ tokens of conversational history can't be stuffed into a prompt, and naive vector RAG fails on multi-session, temporal, and knowledge-update questions. This change builds the core of temporalmem — a local-first temporal knowledge-graph memory — with a benchmark harness so every design decision is measurable, not vibes.

## What Changes

- New Python package `temporalmem` with a pluggable ingestion pipeline: episode sources → LLM entity/fact extraction → entity resolution → Neo4j graph writes.
- Bi-temporal fact model: facts carry `valid_at` / `invalid_at`; contradictions invalidate old facts instead of deleting them.
- Hybrid retrieval over one Neo4j instance: vector index + full-text index fused with RRF, then graph expansion from top entity hits.
- An answering agent (claude-opus-4-8) that queries memory iteratively via a `search_memory` tool.
- LongMemEval evaluation harness with an LLM judge, comparing graph memory against a naive vector-RAG baseline.
- Local infra: docker-compose for Neo4j, local sentence-transformers embeddings.

## Capabilities

### New Capabilities
- `episode-ingestion`: pluggable EpisodeSource protocol, LongMemEval adapter, extraction and graph-write pipeline
- `knowledge-graph`: Neo4j schema, bi-temporal fact model, entity resolution, indexes
- `hybrid-retrieval`: vector + full-text + graph-expansion search with rank fusion
- `memory-agent`: tool-using answering agent over the memory store
- `evaluation`: LongMemEval harness, LLM judge, baseline comparison

### Modified Capabilities

(none — greenfield project)

## Non-goals

- No web UI (Neo4j Browser is the visualization for now)
- No MCP server yet (planned follow-up change once core works)
- No memory decay / community summarization (stretch, separate change)
- No support for personal-data sources yet — but the EpisodeSource protocol must make adding them a pure adapter exercise

## Impact

- New codebase under `src/temporalmem/`, tests under `tests/`
- New runtime dependencies: anthropic, neo4j, pydantic, sentence-transformers, huggingface_hub
- Requires Docker (Neo4j) and an `ANTHROPIC_API_KEY`
- Anthropic API cost: ~a few dollars per full LongMemEval_M haystack ingestion via Batches; development should use one haystack + question subset
