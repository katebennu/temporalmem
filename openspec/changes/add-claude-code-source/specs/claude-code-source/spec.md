# claude-code-source — Delta Spec

## ADDED Requirements

### Requirement: Transcript parsing

`ClaudeCodeSource` SHALL implement the `EpisodeSource` protocol over Claude Code session
JSONL files, yielding Episodes containing only conversational text: `user` and `assistant`
records that are not meta, not sidechain, with only their `text` content blocks, excluding
system-injected user messages (command wrappers, caveats, system reminders/notifications).

#### Scenario: Filtering a real session

- **WHEN** a session file contains user text, assistant text, thinking blocks, tool calls,
  tool results, sidechain messages, and `<command-name>` wrapper messages
- **THEN** the yielded Episode contains exactly the user text and assistant text turns,
  in original order, and nothing else

### Requirement: Episode splitting under a character budget

Sessions whose kept text exceeds a configurable `max_chars` SHALL be split into multiple
Episodes at turn boundaries, with ids `<session_id>:p1`, `:p2`, … and each part's
`occurred_at` taken from its own first turn. A single turn longer than the budget is
truncated with a visible marker, never dropped.

#### Scenario: Long session

- **WHEN** a session's kept turns total more than `max_chars`
- **THEN** multiple Episodes are yielded, no Episode text exceeds the budget by more than
  one truncated turn, and every kept turn appears in exactly one Episode

### Requirement: Source discovery and metadata

Given a directory, the source SHALL iterate every `*.jsonl` session file in it (stable
order); given a single file, just that session. Episode metadata SHALL carry the project
directory name, the session title from `ai-title` records when present, and the part number.

#### Scenario: Directory ingestion

- **WHEN** `--source claude-code --data <dir>` is passed to ingest
- **THEN** every session file in the directory is parsed and ingested idempotently
  (already-ingested episode ids are skipped)
