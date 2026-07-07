# hybrid-retrieval — Delta Spec

## ADDED Requirements

### Requirement: Hybrid search with rank fusion

Given a natural-language query, the system SHALL run vector similarity search (over fact and entity embeddings) and full-text search in parallel and fuse the ranked lists with reciprocal rank fusion into a single candidate list.

#### Scenario: Lexical-only match
- **WHEN** a query contains a rare proper noun whose embedding neighborhood is empty but which appears verbatim in one fact
- **THEN** that fact appears in the fused results

### Requirement: Graph expansion

The system SHALL expand retrieval from the top-ranked entity hits by traversing 1–2 hops of fact relationships, adding connected facts to the candidate set with attenuated scores, under a configurable hop and result budget.

#### Scenario: Multi-hop connection
- **WHEN** the query matches entity A, and a relevant fact links entity A to entity B
- **THEN** facts about B within the hop budget are included in results even if they matched neither search directly

### Requirement: Temporal filtering

Retrieval SHALL support an optional `as_of` timestamp; when provided, facts with `valid_at` after `as_of` or `invalid_at` at-or-before `as_of` SHALL be excluded. When absent, retrieval SHALL prefer currently-valid facts but MAY include invalidated facts marked as historical.

#### Scenario: Question about the past
- **WHEN** retrieval runs with `as_of` set to a date when a since-invalidated fact was still valid
- **THEN** that fact is returned and its superseding fact is not

### Requirement: Results carry provenance

Each retrieval result SHALL include the fact text, subject and object entity names, temporal fields, a fused relevance score, and source episode ids.

#### Scenario: Agent needs raw context
- **WHEN** a retrieval result is insufficient to answer and the caller requests its sources
- **THEN** the original episode text is retrievable from the returned episode ids
