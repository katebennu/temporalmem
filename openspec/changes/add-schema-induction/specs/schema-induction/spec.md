# schema-induction — Delta Spec

## ADDED Requirements

### Requirement: Predicate consolidation

The system SHALL provide a batch induction job that clusters observed predicates by embedding similarity (computed over sampled fact sentences), confirms each proposed merge with an LLM check, and rewrites merged edges to the canonical predicate — recomputing fact keys and unioning `episode_ids` when rewrites collide.

#### Scenario: Synonym predicates merge
- **WHEN** the graph contains facts under `plans_trip_to` and `planned_trip_to` and the induction job runs
- **THEN** all such edges carry one canonical predicate, and colliding duplicates are merged with their episode ids unioned

### Requirement: Stored ontology and promotion

The ontology (canonical predicates, usage counts, functionality classification) SHALL be stored as data — `(:Predicate)` nodes in the graph — seeded from the hand-built vocabulary. Tail predicates above a frequency threshold SHALL be promoted into the canonical set, and the extraction prompt SHALL be generated from the stored ontology rather than a hardcoded list.

#### Scenario: Promoted predicate reaches the extractor
- **WHEN** a tail predicate crosses the promotion threshold and the induction job runs
- **THEN** the next extraction prompt lists it as canonical

### Requirement: Observed functionality inference

The induction job SHALL classify each predicate as functional or multi-valued from data — measuring how often subjects hold multiple temporally overlapping objects for it — with an ambiguous middle band deferred to LLM adjudication or the extractor's per-fact flag. Hand-built classifications act as the seed and are overridable by observation.

#### Scenario: Multi-valued inferred from overlap
- **WHEN** most subjects with 2+ facts for predicate P hold temporally overlapping objects
- **THEN** P is classified multi-valued regardless of its seed label

### Requirement: Retroactive reconciliation

After reclassification or consolidation, the job SHALL replay contradiction detection over existing facts under the new ontology, setting or clearing `invalid_at` retroactively, so earlier write-time decisions are repairable.

#### Scenario: Repairing a wrong earlier invalidation
- **WHEN** a predicate previously treated as functional is reclassified multi-valued
- **THEN** facts it wrongly invalidated have `invalid_at` cleared by the reconciliation pass
