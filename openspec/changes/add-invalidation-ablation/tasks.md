# Tasks: add-invalidation-ablation

## 1. Build

- [x] 1.1 `invalidation_strategy` config (`none | functional | llm`) + strategy dispatch in Ingestor with validation
- [x] 1.2 LLM supersession arm: subject-scoped candidates filtered by fact-embedding cosine, one batched Haiku structured-output verdict per new fact
- [x] 1.3 Timeline grouping in agent result formatting (conflicting same subject+predicate facts as valid_at-ordered timeline)
- [x] 1.4 Stratified `--sample` / `--seed` on eval (closes add-memory-core 4.6); `--strategy` flag; strategy recorded per result record
- [x] 1.5 `temporalmem wipe-db` and `temporalmem compare --results ...` CLI commands
- [x] 1.6 Unit tests: stratified sampling, timeline formatting

## 2. Run the ablation

- [x] 2.1 Pick the fixed subset: `--sample 30 --seed 42` on the oracle variant (all 6 question types included, 5 each)
- [x] 2.2 Arm 1 `none`: wipe-db → eval → score (results/ablation_none.json) — 0.867
- [x] 2.3 Arm 2 `functional`: wipe-db → eval → score (results/ablation_functional.json) — 0.833
- [x] 2.4 Arm 3 `llm`: wipe-db → eval → score (results/ablation_llm.json) — 0.867
- [x] 2.5 `compare` report + llm-arm graph inspection. Findings: (a) no measurable overall difference — every per-type divergence is a single question (n=5/type, within pre-committed noise threshold); (b) knowledge-update saturated at 1.0 in all arms — the oracle variant lacks the retrieval pressure to differentiate strategies; (c) dose-response on counting questions: "how many instruments do I own" answered 4/3/2 under none/functional/llm — write-time invalidation destroys information counting needs; (d) llm arm over-invalidated (30 invalidations incl. `owns 4K TV`, instrument ownership) — the exact failure the functional gate prevents; its two `lives_in` invalidations were legitimate; (e) confounder: each arm re-extracted independently, so single-question diffs mix strategy effect with extraction noise; (f) strategy-independent finding: single-session-assistant 0.4 in every arm — extraction under-captures assistant-side facts
- [ ] 2.6 Write findings into the comparison report / blog draft; decide the default strategy going forward (current lean: keep `functional` default; `none` is competitive and simplest)
- [ ] 2.7 Cleaner protocol for a follow-up run: ingest once under `none`, snapshot, replay invalidation passes offline per arm (valid because strategies only touch invalid_at — removes the extraction-noise confounder); rerun on the _s variant where distractors create real retrieval pressure
