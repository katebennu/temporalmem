# Proposal: add-schema-induction

## Why

The canonical predicate vocabulary and functional-predicate map are hand-built and tuned to LongMemEval's domains — they will not survive contact with real-world sources (personal transcripts, notes), where relations are open-ended and nobody hand-labels which are single-valued. The ontology should grow from the data itself, with the hand-built schema as nothing more than a seed.

## What Changes

A periodic `temporalmem induce-schema` job (batch, manual or every N episodes) with three stages plus a repair pass:

- **Consolidate**: cluster tail predicates by embedding (over sampled fact sentences, not just names), confirm merges with one cheap LLM call per cluster, rewrite losing edges to the canonical form — recomputing fact keys and unioning `episode_ids` where edges collide.
- **Promote**: tail predicates above a frequency threshold join the canonical set. The ontology moves out of the hardcoded prompt into `(:Predicate)` nodes in the graph (counts, scores, functionality); the extraction prompt is built dynamically from it, closing the loop — promoted predicates get used consistently, sharpening the next round's statistics.
- **Infer functionality from observation**: for each predicate, measure how often subjects hold multiple temporally overlapping objects; high overlap → multi-valued, near-zero → functional, ambiguous middle band → LLM adjudication or the extractor's per-fact flag. The hand-built map becomes just the seed.
- **Reconcile**: replay contradiction detection over existing facts under the new classifications, setting or clearing `invalid_at` retroactively — write-time mistakes are repairable, resolving the bootstrap chicken-and-egg.

Adoption is gated on measurement: induced schema vs the hand-built map on the harness.

## Capabilities

### New Capabilities

- `schema-induction`: the consolidation/promotion/inference/reconciliation job and the stored-ontology model

### Modified Capabilities

- `episode-ingestion`: extraction prompt is generated from the stored ontology instead of a hardcoded vocabulary
- `knowledge-graph`: `(:Predicate)` ontology nodes; functionality classification sourced from induction output (seeded by the hand-built map)

## Non-goals

- Entity-type ontology induction (predicates only, for now)
- Online induction during ingest — this is a batch job by design
- Replacing the invalidation strategy — that question belongs to `add-invalidation-ablation`, which SHOULD land first (induced functionality labels only matter if write-time invalidation survives it)

## Impact

- Code: new `schema/` module + CLI subcommand; `extraction/` builds its prompt from the graph; graph schema gains `(:Predicate)` nodes
- Risk: this is the one design with a feedback loop (a bad merge propagates into the extraction prompt) — merge confirmations and the harness gate are the guardrails
- Depends on: `add-invalidation-ablation` outcome; a second real-world `EpisodeSource` adapter is the intended stress test
