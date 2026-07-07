# knowledge-graph — Delta Spec

## ADDED Requirements

### Requirement: Graph schema

The system SHALL store memory in Neo4j using `(:Entity)` nodes (name, normalized name, embedding), `(:Episode)` nodes (id, occurred_at, text), fact relationships `(:Entity)-[:RELATES_TO]->(:Entity)` (predicate, fact text, embedding, temporal fields, source episode ids), and provenance relationships `(:Episode)-[:MENTIONS]->(:Entity)`.

#### Scenario: Provenance is traversable
- **WHEN** any fact is retrieved
- **THEN** the episodes that produced it are reachable via its source episode ids, so raw source text can be fetched

### Requirement: Bi-temporal fact validity

Fact relationships SHALL carry `valid_at` (when the fact became true, if known) and `invalid_at` (when it stopped being true; null while current). Facts SHALL be classified at extraction time as functional (only one object can hold at a time for the subject and predicate, e.g. lives_in) or multi-valued (e.g. owns, purchased_from). When a newly ingested **functional** fact contradicts an existing fact (same subject and predicate, different object), the system SHALL set `invalid_at` on the old fact rather than deleting it. Multi-valued facts MUST NOT invalidate each other.

#### Scenario: Knowledge update
- **WHEN** the graph holds ("user", "lives in", "Berlin") and a later episode yields ("user", "lives in", "Amsterdam")
- **THEN** the Berlin fact receives `invalid_at` equal to the new fact's `valid_at`, and both facts remain queryable

#### Scenario: Point-in-time query
- **WHEN** memory is queried "as of" a date between the Berlin fact's valid_at and invalid_at
- **THEN** the Berlin fact is returned as current and the Amsterdam fact is not

#### Scenario: Multi-valued facts coexist
- **WHEN** the graph holds ("user", "purchased_from", "Best Buy") and a later episode yields ("user", "purchased_from", "Amazon")
- **THEN** both facts remain current (neither receives `invalid_at`)

### Requirement: Entity resolution

Before creating an entity node, the system SHALL attempt to resolve the mention against existing entities using normalized-name match and embedding similarity above a configurable threshold; on a match it SHALL reuse the existing node.

#### Scenario: Same entity, different surface form
- **WHEN** episodes mention "NYC" and "New York City"
- **THEN** both resolve to a single entity node

### Requirement: Indexes and constraints

The system SHALL create, via an idempotent setup routine: uniqueness constraints on entity and episode ids, vector indexes on entity and fact embeddings (384 dims, cosine), and full-text indexes over entity names, fact text, and episode text.

#### Scenario: Fresh database setup
- **WHEN** the schema setup routine runs against an empty Neo4j instance (and again a second time)
- **THEN** all constraints and indexes exist and the second run raises no errors
