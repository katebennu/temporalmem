# Design: add-claude-code-source

## Context

Claude Code writes one JSONL file per session under `~/.claude/projects/<munged-cwd>/`.
Inspection of real files (1.3k records) shows a record zoo: `user`/`assistant` message
records plus `ai-title`, `file-history-snapshot`, `attachment`, `system`, `mode`,
`queue-operation`, and others. Message `content` is either a plain string or a block list
(`text`, `thinking`, `tool_use`, `tool_result`); in the sampled session only 85 of ~730
content blocks were actual text. Records carry `timestamp` (ISO, Z), `sessionId`, `isMeta`,
`isSidechain`, and user records may be system-injected (`<command-name>`,
`<local-command-caveat>`, `<system-reminder>` payloads).

## Goals / Non-Goals

**Goals**
- Turn one session file into clean conversational Episodes: only what a human said and what
  the assistant answered.
- Keep extraction cost bounded on megabyte-scale sessions.
- Zero changes to Ingestor, retrieval, or the agent.

**Non-Goals**
- No extraction of facts from tool outputs, diffs, or file contents (huge, low-density,
  and often verbatim code the graph shouldn't store).
- No incremental tailing of live sessions (re-ingest is idempotent; re-running covers it).
- No cross-project discovery UI — the CLI takes an explicit path.

## Decisions

1. **Filter set** — keep records with `type in {user, assistant}` where `isMeta` and
   `isSidechain` are falsy; keep only `text` blocks (or plain-string content); drop user
   messages starting with system-injected markers (`<command-name>`, `<local-command-caveat>`,
   `<system-reminder>`, `[SYSTEM NOTIFICATION`). Rationale: sidechains are subagent traffic
   that duplicates the main thread; thinking/tool blocks are noise at extraction time.
2. **Splitting** — assemble turns in order and split at turn boundaries when accumulated text
   exceeds `max_chars` (default 20_000 ≈ 5k tokens). Ids: `<session_id>` unsplit, else
   `<session_id>:p1`, `:p2`, …. Rationale: one Haiku call per episode with predictable cost;
   turn-boundary splits never cut a sentence. Each part keeps its own `occurred_at` (first
   turn's timestamp) so bi-temporal dating stays meaningful within long sessions.
3. **Oversized single turns** are truncated to `max_chars` with a `… [truncated]` marker
   rather than dropped — a truncated question still anchors its answer.
4. **Metadata** — `{"project": <dir name>, "title": <ai-title>, "part": N}`; title comes from
   the last `ai-title` record (titles get refined mid-session).
5. **CLI shape** — `ingest --source claude-code --data <dir-or-file>`; a directory ingests
   every `*.jsonl` inside (sorted by mtime so re-runs are stable), a file just that session.
   `--source` defaults to `longmemeval` so every documented command keeps working.
6. **Extractor stays generic** — one added prompt line covering development/work facts
   (decisions, renames, tools adopted, results measured). The canonical predicate list is
   already "prefer when it fits"; Haiku may mint snake_case predicates for dev concepts, and
   the schema-induction phase is the planned home for consolidating them.

## Risks / Trade-offs

- **Transcripts of temporalmem sessions mention temporalmem itself** — self-referential
  entities ("temporalmem", "Neo4j") will accumulate many facts; acceptable for a demo, and
  a good stress test for entity resolution.
- **Privacy**: transcript text goes to the Anthropic API for extraction — same trust boundary
  as the sessions themselves, but worth one README sentence.
- **Cost**: a large project directory can hold hundreds of sessions. Mitigated by episode
  char budget, idempotent skip of already-ingested episode ids, and explicit per-path CLI.

## Migration Plan

Purely additive; no schema or data migration. Existing graphs are unaffected.

## Open Questions

- Should `compactMetadata`/summary records be ingested as their own high-density episodes?
  Deferred: they duplicate what extraction already distills.
