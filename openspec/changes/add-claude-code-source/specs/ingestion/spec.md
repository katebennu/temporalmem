# ingestion — Delta Spec

## ADDED Requirements

### Requirement: CLI source selection

The `ingest` command SHALL accept `--source {longmemeval,claude-code}` defaulting to
`longmemeval`, keeping all existing invocations valid. For `claude-code`, `--data` SHALL
accept a transcript directory or a single `.jsonl` file; `--question-id` applies only to
`longmemeval` and SHALL be rejected with a clear error otherwise.

#### Scenario: Backward compatibility

- **WHEN** `ingest --data <longmemeval.json>` is run without `--source`
- **THEN** behavior is identical to before this change

### Requirement: Development-fact extraction guidance

The extraction prompt SHALL include source-agnostic guidance that decisions and outcomes of
work sessions (project renames, tools/libraries adopted, results and scores obtained) are
durable facts, without referencing any specific benchmark or source.

#### Scenario: Extracting from a coding session

- **WHEN** a session where the user renames a project and records a benchmark score is
  extracted
- **THEN** the extraction includes facts capturing the rename decision and the score as
  dated facts
