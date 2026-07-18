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
- [x] 2.4 Extraction quality pass 1 (from oracle dry-run findings): canonical predicate vocabulary, no date/literal objects, valid_at for acquisition events, functional flag gating invalidation, valid_at shown in --dry-run
- [x] 2.5 Verify ingestion end-to-end against one real LongMemEval haystack (oracle gpt4_2312f94c: idempotent re-ingest skips, entity resolution merges across sessions, all owns facts coexist with purchase dates in valid_at; search + agent answer matches gold). Found and fixed a `query` parameter-name collision in GraphClient.run.
- [ ] 2.6 Batches API path for bulk ingestion (50% cost); keep sync path for --dry-run
- [ ] 2.7 LLM tie-break for entity resolution when embedding similarity is near threshold
- [x] 2.8 Extraction pass 2: dated events (attended / participated_in / started_working_at / started_working_with + valid_at) — participation and employment-start dates were the missing facts in eval run 1
- [x] 2.9 Extraction pass 3 (ablation finding): assistant-side facts under-captured — prompt now extracts assistant recommendations/suggestions (subject "assistant", predicates recommended/suggested). Verified in run3: single-session-assistant 0.4 → 0.8
- [x] 2.10 Entity resolution over-merge: threshold raised 0.85 → 0.90 and vector match gated by `types_compatible` (concrete entity_types must agree; 'other'/missing is a wildcard); checks top-3 candidates. Feeds 2.7

## 3. Milestone 2 — Retrieval & agent

- [x] 3.1 RRF fusion + hybrid search (vector + full-text over facts) with temporal filtering
- [x] 3.2 Graph expansion from entity seeds with attenuated scores
- [x] 3.3 Memory agent (claude-opus-4-8) with search_memory + inspect_episodes tool loop
- [ ] 3.4 Validate retrieval quality on the oracle variant: answer-session recall@k before agent quality
- [ ] 3.5 Tune expansion hops/decay and search limits against a 20-question subset
- [x] 3.6 Agent prompt: explicit inspect_episodes trigger when facts lack a needed detail (all 3 misses in run 1 had the answer in raw episode text, agent never inspected)
- [x] 3.7 Acquisition semantics guidance (run-2 regression): "got/acquired X" means when ownership began (receipt/delivery), not order date — added to agent prompt + extraction note for pre-order vs arrival

## 4. Milestone 3 — Evaluation

- [x] 4.1 Eval harness: resumable runs, per-question records, latency capture
- [x] 4.2 LLM judge + per-question-type accuracy report
- [ ] 4.3 Naive vector-RAG baseline behind the same backend interface (spec: evaluation / Baseline comparison)
- [ ] 4.4 Record token usage per run for cost tracking
- [ ] 4.5 Full A/B report: graph memory vs baseline on a fixed subset, per question type
- [x] 4.6 Stratified --sample flag for eval (implemented under add-invalidation-ablation build: --sample/--seed round-robin across question types)
- [x] 4.7 Re-run the same 20 questions after 2.8 + 3.6 (results/run2.json): **0.90 vs 0.85 baseline** — both targeted misses fixed (Rachel start date extracted; NovaTech career math), charity-count still missed, one regression (got-first interpreted as order date; → 3.7)
- [x] 4.8 Verification run after 2.9 + 2.10 + 3.7 (results/run3.json, 30 stratified, seed 42, functional): **0.867 vs 0.833 baseline** — single-session-assistant 0.4 → 0.8 (the targeted fix, only above-noise move); multi-session 0.6 → 0.4 (one question, within noise; both misses are counting/interpretation with all facts retrieved, not retrieval failures)

## 5. Wrap-up

- [ ] 5.1 Integration test suite (requires Neo4j; separate pytest marker)
- [ ] 5.2 Update README with first real benchmark numbers
- [ ] 5.3 Sync delta specs to main specs and archive this change (/opsx:archive)

Next phases (queued changes, proposals written): `add-invalidation-ablation` (first — none vs functional vs llm-judged, measured), then `add-schema-induction` (gated on the ablation outcome).
