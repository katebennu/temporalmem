# Tasks: add-claude-code-source

## 1. Source implementation

- [x] 1.1 `sources/claudecode.py`: record filtering (user/assistant text only; drop meta,
  sidechain, thinking, tool blocks, system-injected user messages)
- [x] 1.2 Episode assembly with `max_chars` splitting at turn boundaries, per-part
  `occurred_at`, oversized-turn truncation marker
- [x] 1.3 Directory/file discovery, `ai-title` metadata, project name from path
- [x] 1.4 Unit tests on a fixture JSONL exercising the filter, split, and metadata rules
  (no Neo4j, no API key)

## 2. CLI + extraction

- [x] 2.1 `ingest --source {longmemeval,claude-code}` with backward-compatible default;
  reject `--question-id` for claude-code
- [x] 2.2 Extraction prompt: one source-agnostic line on development decisions/outcomes as
  durable dated facts
- [x] 2.3 Unit test: CLI arg wiring (source dispatch, error on --question-id misuse)

## 3. Demo (the actual showcase)

- [x] 3.1 Ingest this repo's own Claude Code sessions into a fresh graph: 7 sessions →
  18 episodes, 207 entities, 226 facts
- [x] 3.2 Curated 7 questions (rename, run-2 fixes, ablation outcome, stack, over-merge bug,
  Graphiti diff, inspector UI) — all answered correctly via `temporalmem ask`; the over-merge
  answer correctly reported the fix as "not yet applied" as of the ingested sessions
  (bi-temporal correctness, quoted in the README)
- [ ] 3.3 Inspect entity timelines in the Streamlit inspector; capture screenshots (Kate —
  needs a browser)
- [x] 3.4 README section: "Point it at your own Claude Code sessions" with commands,
  verified Q&A, and the privacy note
