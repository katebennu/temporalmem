# knowledge-graph — Delta Spec (invalidation ablation)

## ADDED Requirements

### Requirement: Invalidation strategy selection

The system SHALL support three write-time invalidation strategies, selected by configuration: `none` (facts are never invalidated at write time), `functional` (deterministic gate via the functional-predicate map — current behavior, the default), and `llm` (candidate conflict pairs, found by same subject plus predicate-embedding similarity with a different object, judged for supersession by an LLM). The active strategy MUST NOT change which facts are stored — only whether and how `invalid_at` is set.

#### Scenario: None arm stores conflicts unmarked
- **WHEN** strategy is `none` and ("user", "lives_in", "Amsterdam") is ingested after ("user", "lives_in", "Berlin")
- **THEN** both facts remain current (no `invalid_at`), and retrieval presents them as a valid_at-ordered timeline

#### Scenario: LLM arm catches a cross-predicate conflict
- **WHEN** strategy is `llm` and ("user", "moved_to", "Amsterdam") is ingested while ("user", "lives_in", "Berlin") is current
- **THEN** the judge is consulted and, on a supersession verdict, the Berlin fact receives `invalid_at`

#### Scenario: Strategy does not alter stored facts
- **WHEN** the same episode set is ingested under each of the three strategies into empty graphs
- **THEN** the three graphs contain the same fact relationships, differing only in `invalid_at` markers
