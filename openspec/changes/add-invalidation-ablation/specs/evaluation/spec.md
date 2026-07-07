# evaluation — Delta Spec (invalidation ablation)

## ADDED Requirements

### Requirement: Strategy-tagged comparison runs

Eval runs SHALL record the active invalidation strategy in each result record, and the report SHALL support comparing runs across strategies on identical question sets, broken down by question type. Because facts must be written under the strategy being tested, the harness SHALL support (or document) re-ingesting the subset from a clean graph per arm.

#### Scenario: Three-arm report
- **WHEN** the same 20-question subset has been run under `none`, `functional`, and `llm`
- **THEN** the report presents per-strategy accuracy side by side, overall and per question type
