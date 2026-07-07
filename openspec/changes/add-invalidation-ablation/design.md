# Design: add-invalidation-ablation

## Context

Write-time invalidation is the temporal graph's central design bet, currently implemented one way (deterministic functional-predicate gate). Run 2 showed both failure directions are real: silent state corruption (entity over-merge) vs agent over-interpretation of unresolved context. Graphiti ships a single strategy and no published comparison exists — the measured answer is the project's original-contribution candidate.

## Goals / Non-Goals

**Goals:**
- Three invalidation strategies runnable against identical question subsets with one config/CLI switch
- A per-question-type comparison report
- A fair `none` arm (the agent must see conflicts as an ordered timeline, not scattered noise)

**Non-Goals:**
- Declaring a winner in the design doc — the harness decides
- `superseded_by` soft links; ontology changes (add-schema-induction)

## Decisions

1. **Strategy as config + CLI flag** (`INVALIDATION_STRATEGY` env / `--strategy` on eval), dispatched in `Ingestor._write`; `functional` stays the default. Strategy recorded on every result record so results files are self-describing.

2. **LLM arm: candidates by subject + fact-embedding cosine, one batched Haiku judge call per new fact.** Candidates = subject's current facts with a different object, `valid_at <=` the new fact's, cosine ≥ 0.55, top 5. A single structured-output call returns superseded indices. Rationale: per-pair calls would multiply cost ~5x; subject-scoped candidates keep the pool small since most facts share the "user" subject. Judge instruction biases against superseding when unsure (a wrong invalidation is silent corruption; a missed one is recoverable at read time).

3. **`none` arm fairness via timeline grouping in result formatting** (all arms get it): conflicting facts for the same subject+predicate render as a valid_at-ordered timeline. Without this, the `none` arm would measure formatting noise, not the strategy.

4. **Per-arm re-ingestion from a wiped graph** (`temporalmem wipe-db`), since facts must be written under the strategy being tested. Same `--sample N --seed S` across arms guarantees identical question sets.

5. **Comparison over scored results files** (`temporalmem compare --results a.json b.json c.json`) rather than a stateful experiment runner — files are the unit of comparison, resumable and inspectable.

## Risks / Trade-offs

- [Judge nondeterminism makes arms noisy] → fixed seed/subset, judge-once caching in results files; report per-type so noise is visible
- [Subject-scoped candidates miss cross-subject conflicts] → accepted; rare in this data model where "user" is the subject of most facts
- [Cosine 0.55 threshold untuned] → config constant; tune only if the llm arm shows obvious misses
- [Small subsets (~30) give wide confidence intervals] → report counts alongside accuracy; treat differences < ~2 questions as noise

## Migration Plan

No migration — strategies only affect `invalid_at` markers. Any arm's graph is rebuilt with wipe-db + re-ingest.
