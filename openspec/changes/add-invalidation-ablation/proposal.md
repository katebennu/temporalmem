# Proposal: add-invalidation-ablation

## Why

Write-time fact invalidation is the core design assumption of the temporal graph — and it's unproven. Three strategies exist on a spectrum (no write-time invalidation with read-time resolution; the current deterministic functional-predicate gate; an LLM supersession judge, Graphiti-style), and eval run 2 already showed both failure directions: an entity over-merge nearly corrupted state, while handing the agent unresolved raw context caused an interpretation regression. Nobody has published a clean comparison of these strategies on LongMemEval's knowledge-update and temporal-reasoning question types; this ablation is both the engineering decision procedure and the project's original contribution.

## What Changes

- `invalidation_strategy` config: `none | functional | llm`.
  - `none`: skip invalidation entirely; retrieval orders conflicting facts by `valid_at` so the agent resolves conflicts at read time.
  - `functional`: current behavior (deterministic gate via the functional-predicate map) — unchanged, becomes the explicit default.
  - `llm`: new arm — candidate conflict pairs found by same subject + predicate-embedding similarity + different object, judged by claude-haiku-4-5 ("does the new fact supersede the old one?"); handles cross-predicate and paraphrase conflicts the deterministic gate cannot.
- Eval harness tags each run with its strategy and supports a three-way report on a fixed question subset, broken down by question type.
- Result formatting groups conflicting facts per subject+predicate into a `valid_at`-ordered timeline so the `none` arm gets a fair shot.

## Capabilities

### New Capabilities

(none — this parameterizes existing behavior)

### Modified Capabilities

- `knowledge-graph`: the bi-temporal invalidation requirement becomes strategy-parameterized (functional gating is one strategy, not the definition)
- `evaluation`: runs record the active invalidation strategy; report supports cross-strategy comparison on identical question sets

## Non-goals

- Not choosing a winner in advance — the harness decides
- No schema/ontology changes (that's `add-schema-induction`)
- `superseded_by` soft-links between facts: noted as a stretch, not in scope

## Impact

- Code: `config.py`, `ingest.py` (strategy dispatch + LLM judge arm), `retrieval/hybrid.py` (timeline grouping), `evaluation/harness.py` (strategy tagging + comparison report)
- Cost: `llm` arm adds ~one Haiku call per candidate conflict pair at ingest; `none` arm adds ~10–30% agent-loop tokens at read time; both trivial at current scale
- Each arm requires re-ingesting the eval subset from a wiped graph (facts must be written under the strategy being tested)
- Output feeds the blog post and gates `add-schema-induction` (induced functionality labels only matter if write-time invalidation survives the ablation)
