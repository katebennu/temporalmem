# evaluation — Delta Spec

## ADDED Requirements

### Requirement: Benchmark harness

The system SHALL run a configurable subset of LongMemEval questions end-to-end (ingest the question's haystack, answer via a selected backend, record the hypothesis) and persist per-question results (question id, type, hypothesis, gold answer, latency, token usage) to a JSON results file.

#### Scenario: Subset run
- **WHEN** the harness is invoked with a limit of 20 questions and one backend
- **THEN** it produces a results file with 20 entries, resumable without re-ingesting already-ingested haystacks

### Requirement: LLM judge scoring

The system SHALL score each hypothesis against the gold answer with an LLM judge that returns a binary correct/incorrect verdict, and SHALL report accuracy overall and per question type (including abstention questions).

#### Scenario: Scoring a run
- **WHEN** a results file is scored
- **THEN** the report shows overall accuracy and a per-type breakdown across the six LongMemEval question types

### Requirement: Baseline comparison

The harness SHALL support at least two interchangeable backends behind one interface: the graph memory agent and a naive chunk-based vector RAG baseline, so both can be scored on identical question sets.

#### Scenario: A/B report
- **WHEN** both backends are run on the same 20-question subset
- **THEN** the report presents their accuracy side by side per question type
