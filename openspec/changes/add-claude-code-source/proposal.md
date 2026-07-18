# Proposal: add-claude-code-source

## Why

temporalmem has only ever ingested benchmark data. The `EpisodeSource` protocol was designed
so a real conversation store could plug in without touching the pipeline — this change cashes
that in. Claude Code session transcripts (`~/.claude/projects/<project>/*.jsonl`) are real,
personal, local data that outgrow any context window, and asking a project's own development
history ("when did the engram rename happen and why?", "what did eval run 2 score?") is a
demo a reader can immediately want for themselves. It is also the flagship justification for
local-first: nobody wants their coding sessions in someone else's cloud.

## What Changes

- New `ClaudeCodeSource` implementing `EpisodeSource` over Claude Code transcript JSONL:
  parses `user`/`assistant` records, keeps only human-readable text turns, drops tool
  calls/results, thinking blocks, sidechain (subagent) traffic, meta records, and
  system-injected command/caveat messages.
- Long sessions split into multiple Episodes at turn boundaries under a character budget;
  Episode ids are `<session_id>` or `<session_id>:pN` for parts.
- Session title (from `ai-title` records) and project directory carried in Episode metadata.
- CLI: `ingest`, `eval` untouched; `ingest` gains `--source {longmemeval,claude-code}`
  (default `longmemeval`, backward compatible) with `--data` pointing at a project transcript
  directory or a single `.jsonl` file.
- Extraction prompt gains a light, source-agnostic note that development decisions
  (renames, chosen tools, results) are durable facts — no benchmark-specific wording.
- Demo script material for README/blog: ingest this repo's own sessions, ask history
  questions via `temporalmem ask` and the inspector.

## Capabilities

### New Capabilities

- `claude-code-source`: transcript discovery, record filtering, episode assembly/splitting.

### Modified Capabilities

- `ingestion`: CLI source selection (`--source`), extraction-prompt note for development
  facts. No pipeline behavior changes otherwise.

## Impact

- New module `src/temporalmem/sources/claudecode.py` + unit tests on fixture JSONL.
- `cli.py` ingest subcommand gains one flag; `extractor.py` prompt one added line.
- No graph schema change, no config change, no new dependencies.
- Privacy note: transcripts stay local; the only egress remains the Anthropic extraction call,
  same as every other source.
