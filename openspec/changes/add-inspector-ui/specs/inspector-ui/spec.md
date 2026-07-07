# inspector-ui — Delta Spec

## ADDED Requirements

### Requirement: Read-only inspection surface

The system SHALL provide a local web inspector with Ask, Search, Timeline, and Runs views. The inspector MUST NOT write to the graph — ingestion and wipes remain CLI-only.

#### Scenario: Diagnosing a wrong answer
- **WHEN** a question is asked in the Ask view
- **THEN** the answer is shown together with the full tool trace — each search/inspect call's inputs and the exact text the agent saw back

### Requirement: Fact-validity timeline

The Timeline view SHALL render an entity's facts as bars from `valid_at` to `invalid_at` (or now), grouped by predicate, with superseded facts visually distinguishable and listed.

#### Scenario: Viewing a knowledge update
- **WHEN** an entity has a superseded lives_in fact and its successor
- **THEN** the old fact's bar ends where the new fact's bar begins, and the old fact appears in the superseded list

### Requirement: Runs comparison view

The Runs view SHALL chart per-question-type accuracy across selected scored results files (e.g. ablation arms side by side) and provide a failure browser showing question, gold answer, and hypothesis for incorrect records.

#### Scenario: Comparing ablation arms
- **WHEN** the three ablation results files are selected
- **THEN** grouped bars show per-type accuracy per arm with visible value labels, and an overall accuracy table with counts is displayed

### Requirement: Agent tool trace

`MemoryAgent` SHALL expose an `answer_traced` method returning the answer text and an ordered trace of tool calls (tool name, input, output text), without changing the behavior of `answer`.

#### Scenario: Trace availability
- **WHEN** the agent answers a question that required two searches and one episode inspection
- **THEN** the returned trace contains three entries in call order
