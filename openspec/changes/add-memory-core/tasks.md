# Tasks: add-memory-core

## 1. Milestone 1 — Infrastructure & scaffold

- [x] 1.1 Project scaffold: pyproject (uv), docker-compose for Neo4j 5.26, .env.example, README, CLAUDE.md
- [x] 1.2 EpisodeSource protocol + Episode/Turn models (`sources/base.py`)
- [x] 1.3 LongMemEval adapter with date parsing, question iterator, id filtering (`sources/longmemeval.py`)
- [x] 1.4 Neo4j client wrapper + idempotent schema setup (constraints, vector + full-text indexes)
- [x] 1.5 Local embedder (sentence-transformers, lazy model load)
- [x] 1.6 Dataset download script (HuggingFace `xiaowu0162/longmemeval-cleaned`)
- [x] 1.7 Unit tests for sources, RRF, ingest utilities (no external services)

## 2. Milestone 1 — Ingestion pipeline

- [x] 2.1 Extraction schemas + claude-haiku-4-5 extractor via structured outputs
- [x] 2.2 Ingestor: episode → extraction → entity resolution → graph writes, idempotent, --dry-run
- [x] 2.3 Contradiction invalidation (same subject+predicate, different object → set invalid_at)
- [ ] 2.4 Verify ingestion end-to-end against one real LongMemEval haystack; eyeball graph in Neo4j Browser; iterate on extraction prompt using the oracle variant
- [ ] 2.5 Batches API path for bulk ingestion (50% cost); keep sync path for --dry-run
- [ ] 2.6 LLM tie-break for entity resolution when embedding similarity is near threshold

## 3. Milestone 2 — Retrieval & agent

- [x] 3.1 RRF fusion + hybrid search (vector + full-text over facts) with temporal filtering
- [x] 3.2 Graph expansion from entity seeds with attenuated scores
- [x] 3.3 Memory agent (claude-opus-4-8) with search_memory + inspect_episodes tool loop
- [ ] 3.4 Validate retrieval quality on the oracle variant: answer-session recall@k before agent quality
- [ ] 3.5 Tune expansion hops/decay and search limits against a 20-question subset

## 4. Milestone 3 — Evaluation

- [x] 4.1 Eval harness: resumable runs, per-question records, latency capture
- [x] 4.2 LLM judge + per-question-type accuracy report
- [ ] 4.3 Naive vector-RAG baseline behind the same backend interface (spec: evaluation / Baseline comparison)
- [ ] 4.4 Record token usage per run for cost tracking
- [ ] 4.5 Full A/B report: graph memory vs baseline on a fixed subset, per question type

## 5. Wrap-up

- [ ] 5.1 Integration test suite (requires Neo4j; separate pytest marker)
- [ ] 5.2 Update README with first real benchmark numbers
- [ ] 5.3 Sync delta specs to main specs and archive this change (/opsx:archive)
