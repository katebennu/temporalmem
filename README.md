# temporalmem

Local-first agentic memory on a temporal knowledge graph, evaluated on
[LongMemEval](https://github.com/xiaowu0162/LongMemEval).

An agent's conversational history quickly exceeds any context window, and naive vector RAG
fails on multi-session, temporal, and knowledge-update questions. temporalmem ingests chat
history into a Neo4j knowledge graph where facts carry validity windows (`valid_at` /
`invalid_at`), retrieves with hybrid search (vector + full-text + graph expansion), and
answers questions through a tool-using agent — with a benchmark harness so every design
decision is measured, not vibed.

```
EpisodeSource ──> extraction ──> entity resolution ──> Neo4j temporal graph
 (pluggable)      (claude-haiku-4-5,                    (:Entity)-[:RELATES_TO
                   structured outputs)                    {fact, valid_at, invalid_at}]->(:Entity)
                                                                 │
        answer <── memory agent <── hybrid retrieval ────────────┘
                   (claude-opus-4-8,  (vector + BM25 + RRF
                    search_memory)     + graph expansion)
```

Everything runs locally except Anthropic API calls: Neo4j in Docker, embeddings via
sentence-transformers on your machine.

## Quickstart

```bash
# 1. Infrastructure
cp .env.example .env          # add your ANTHROPIC_API_KEY
docker compose up -d          # Neo4j at bolt://localhost:7687, browser at http://localhost:7474

# 2. Install
uv sync

# 3. Data + schema
uv run python scripts/download_data.py
uv run temporalmem setup-db

# 4. Ingest one question's haystack and look around
uv run temporalmem ingest --data data/longmemeval/longmemeval_s_cleaned.json \
    --question-id <some_question_id>
# open http://localhost:7474 and run: MATCH p=(:Entity)-[:RELATES_TO]->(:Entity) RETURN p LIMIT 100

# 5. Query it
uv run temporalmem search --query "where does the user live" --as-of 2023-05-01
uv run temporalmem ask --question "Where did I live before I moved?" --date 2023-06-01

# 6. Evaluate
uv run temporalmem eval --data data/longmemeval/longmemeval_s_cleaned.json --limit 20
uv run temporalmem score --data data/longmemeval/longmemeval_s_cleaned.json
```

Cost note: ingestion uses claude-haiku-4-5; a full LongMemEval_M haystack is roughly a couple
of dollars. Develop against single haystacks and small `--limit` values.

## Key design points

- **Pluggable sources.** Everything downstream consumes the `EpisodeSource` protocol
  (`src/temporalmem/sources/base.py`). Adding your own data (chat exports, notes) is a new
  adapter, not a rewrite.
- **Bi-temporal facts.** Contradicting facts invalidate their predecessors instead of
  overwriting them, so "where does she live?" and "where did she live in 2024?" are both
  answerable.
- **One database.** Neo4j provides the graph, the vector indexes, and the full-text (Lucene)
  indexes — no cross-store sync.
- **Measured, not vibed.** The eval harness scores answers with an LLM judge per LongMemEval
  question type, so retrieval changes are A/B-testable.

## Development

Specs and change proposals live in `openspec/` (managed with
[OpenSpec](https://github.com/Fission-AI/OpenSpec)). Current state and roadmap:
`openspec/changes/add-memory-core/`. Use `/opsx:propose` in Claude Code to spec new work
before implementing.

```bash
uv run pytest          # unit tests (no Neo4j or API key needed)
uv run ruff check .    # lint
```
