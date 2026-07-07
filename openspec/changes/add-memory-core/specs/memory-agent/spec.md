# memory-agent — Delta Spec

## ADDED Requirements

### Requirement: Tool-using answering agent

The system SHALL provide an agent (claude-opus-4-8) that answers questions about the stored history using a `search_memory` tool (query, optional `as_of`) and an `inspect_episodes` tool (fetch raw episode text by id). The agent SHALL be able to issue multiple searches per question.

#### Scenario: Multi-hop question
- **WHEN** a question requires combining facts from two different sessions
- **THEN** the agent issues at least one search per sub-question and synthesizes an answer grounded in returned facts

### Requirement: Grounded answers with abstention

The agent SHALL answer only from retrieved memory. When retrieval yields no sufficient evidence, the agent SHALL state that the information is not in memory rather than guessing.

#### Scenario: Abstention question
- **WHEN** a LongMemEval `_abs` question asks about something never discussed
- **THEN** the agent's answer communicates that the history contains no such information

### Requirement: Question-date awareness

The agent SHALL receive the question's date and use it for temporal reasoning (e.g. resolving "last month") and as the default `as_of` for searches.

#### Scenario: Relative time expression
- **WHEN** a question dated 2023-06-01 asks "where did I stay last month?"
- **THEN** the agent searches with temporal bounds covering 2023-05 and answers with the fact valid in that window
