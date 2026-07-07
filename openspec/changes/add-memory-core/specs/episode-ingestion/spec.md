# episode-ingestion — Delta Spec

## ADDED Requirements

### Requirement: Pluggable episode sources

The system SHALL consume conversational history exclusively through the `EpisodeSource` protocol, which yields `Episode` objects carrying a stable unique `id`, an `occurred_at` timestamp, an ordered list of role/content turns, and source-specific `metadata`. Downstream stages (extraction, graph writes, retrieval) MUST NOT depend on any concrete source type.

#### Scenario: New source requires only an adapter
- **WHEN** a developer adds a new data source (e.g. personal chat transcripts) by implementing `EpisodeSource`
- **THEN** the existing ingestion pipeline processes its episodes without modification to extraction, graph, or retrieval code

### Requirement: LongMemEval adapter

The system SHALL provide a `LongMemEvalSource` that parses a LongMemEval JSON file (`_s`, `_m`, or `_oracle` variant) and yields one `Episode` per haystack session, using the corresponding `haystack_dates` entry as `occurred_at` and recording `question_id` and session id in `metadata`.

#### Scenario: Loading a haystack
- **WHEN** a LongMemEval instance with 40 haystack sessions is loaded for one question id
- **THEN** the source yields 40 episodes, each with a parseable timestamp and a deterministic episode id

### Requirement: LLM fact extraction

The system SHALL extract entities and subject–predicate–object facts from each episode using a schema-constrained LLM call (structured outputs), producing typed pydantic objects. Extraction SHALL use consistent snake_case predicates, SHALL NOT emit dates or adverbs as fact objects, SHALL capture the date a fact became true (`valid_at`) when stated or inferable — for acquisition/state-change events, the date the state began — and SHALL classify each fact as functional or multi-valued.

#### Scenario: Extracting from a session
- **WHEN** an episode containing "I moved to Amsterdam last month" (episode dated 2023-05-20) is extracted
- **THEN** the output contains an entity for the user and for Amsterdam, and a fact ("lives in") with a valid-from date near 2023-04

### Requirement: Idempotent ingestion

The system SHALL make ingestion idempotent: re-ingesting an already-ingested episode MUST NOT create duplicate episode nodes, entity nodes, or fact relationships.

#### Scenario: Re-running ingestion
- **WHEN** the same episode is ingested twice
- **THEN** node and relationship counts in the graph are unchanged after the second run
