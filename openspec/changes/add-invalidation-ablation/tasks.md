# Tasks: add-invalidation-ablation

## 1. Build

- [x] 1.1 `invalidation_strategy` config (`none | functional | llm`) + strategy dispatch in Ingestor with validation
- [x] 1.2 LLM supersession arm: subject-scoped candidates filtered by fact-embedding cosine, one batched Haiku structured-output verdict per new fact
- [x] 1.3 Timeline grouping in agent result formatting (conflicting same subject+predicate facts as valid_at-ordered timeline)
- [x] 1.4 Stratified `--sample` / `--seed` on eval (closes add-memory-core 4.6); `--strategy` flag; strategy recorded per result record
- [x] 1.5 `temporalmem wipe-db` and `temporalmem compare --results ...` CLI commands
- [x] 1.6 Unit tests: stratified sampling, timeline formatting

## 2. Run the ablation

- [ ] 2.1 Pick the fixed subset: `--sample 30 --seed 42` on the oracle variant (verify knowledge-update questions are included)
- [ ] 2.2 Arm 1 `none`: wipe-db → eval → score (results/ablation_none.json)
- [ ] 2.3 Arm 2 `functional`: wipe-db → eval → score (results/ablation_functional.json)
- [ ] 2.4 Arm 3 `llm`: wipe-db → eval → score (results/ablation_llm.json)
- [ ] 2.5 `compare` report; sanity-check llm-arm invalidations by inspecting a few invalid_at markers in the graph
- [ ] 2.6 Write findings into the comparison report / blog draft; decide the default strategy going forward
