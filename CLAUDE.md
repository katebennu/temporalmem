# temporalmem — agent instructions

Local-first agentic memory on a temporal knowledge graph (Neo4j), evaluated on LongMemEval.
Read `README.md` for architecture; `openspec/` for specs and active changes.

## Spec-driven workflow (OpenSpec)

This project uses OpenSpec. Requirements live in `openspec/specs/`, in-flight work in
`openspec/changes/<change-id>/`.

- New feature or behavior change → start with `/opsx:propose` (or `openspec new change`),
  don't implement first.
- Implementing an existing change → follow its `tasks.md`, check items off as you complete them.
- Behavior changed in code → keep the corresponding spec delta in sync (`/opsx:sync`).
- Finished and verified → `/opsx:archive`.

## Commands

- `uv sync` — install; `uv run pytest` — tests (no external services needed)
- `docker compose up -d` — Neo4j; `uv run temporalmem setup-db` — create indexes
- CLI: `uv run temporalmem {setup-db,ingest,search,ask,eval,score}`

## Conventions

- Python 3.12, src layout. Standard readable style: descriptive names, type hints,
  docstrings only where behavior isn't obvious.
- Models: `claude-haiku-4-5` for extraction, `claude-opus-4-8` for agent/judge — configured
  in `src/temporalmem/config.py`, never hardcoded elsewhere.
- Embedding model/dimensions are coupled to the Neo4j vector index DDL; change both together
  (requires reindex).
- Unit tests must not require Neo4j or an API key; anything needing either belongs in a
  separate integration suite.
- Neo4j is disposable during development: `docker compose down -v` wipes it.
