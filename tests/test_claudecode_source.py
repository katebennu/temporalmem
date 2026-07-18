import json

from temporalmem.sources.claudecode import ClaudeCodeSource, TRUNCATION_MARKER


def _msg(role, content, ts="2026-07-06T21:43:47.706Z", **extra):
    return {
        "type": role,
        "timestamp": ts,
        "message": {"role": role, "content": content},
        **extra,
    }


def _write_session(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records))


SESSION = [
    {"type": "ai-title", "aiTitle": "First title"},
    {"type": "mode", "mode": "normal"},
    _msg("user", "let's build a memory system", ts="2026-07-06T10:00:00Z"),
    _msg(
        "assistant",
        [
            {"type": "thinking", "thinking": "hmm"},
            {"type": "text", "text": "Sounds good, starting with Neo4j."},
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}},
        ],
        ts="2026-07-06T10:01:00Z",
    ),
    _msg("user", [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]),
    _msg("user", "<command-name>/model</command-name>"),
    _msg("user", "<system-reminder>noise</system-reminder>"),
    _msg("user", "ignored sidechain", isSidechain=True),
    _msg("user", "ignored meta", isMeta=True),
    {"type": "ai-title", "aiTitle": "Refined title"},
    _msg("user", "rename it to temporalmem", ts="2026-07-06T11:00:00Z"),
]


def test_filters_to_conversational_text(tmp_path):
    _write_session(tmp_path / "abc123.jsonl", SESSION)
    episodes = list(ClaudeCodeSource(tmp_path / "abc123.jsonl").episodes())

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.id == "abc123"
    assert [(t.role, t.content) for t in episode.turns] == [
        ("user", "let's build a memory system"),
        ("assistant", "Sounds good, starting with Neo4j."),
        ("user", "rename it to temporalmem"),
    ]
    assert episode.occurred_at.isoformat() == "2026-07-06T10:00:00+00:00"
    assert episode.metadata["title"] == "Refined title"
    assert episode.metadata["project"] == tmp_path.name


def test_splits_long_sessions_at_turn_boundaries(tmp_path):
    records = [
        _msg("user", "a" * 60, ts="2026-07-06T10:00:00Z"),
        _msg("assistant", "b" * 60, ts="2026-07-06T10:01:00Z"),
        _msg("user", "c" * 60, ts="2026-07-06T10:02:00Z"),
    ]
    _write_session(tmp_path / "s1.jsonl", records)
    episodes = list(ClaudeCodeSource(tmp_path / "s1.jsonl", max_chars=100).episodes())

    assert [e.id for e in episodes] == ["s1:p1", "s1:p2", "s1:p3"]
    assert [len(e.turns) for e in episodes] == [1, 1, 1]
    # each part dated by its own first turn
    assert episodes[1].occurred_at.isoformat() == "2026-07-06T10:01:00+00:00"
    assert [e.metadata["part"] for e in episodes] == [1, 2, 3]


def test_truncates_oversized_single_turn(tmp_path):
    _write_session(tmp_path / "s2.jsonl", [_msg("user", "x" * 500)])
    episodes = list(ClaudeCodeSource(tmp_path / "s2.jsonl", max_chars=100).episodes())

    assert len(episodes) == 1
    content = episodes[0].turns[0].content
    assert content.endswith(TRUNCATION_MARKER)
    assert len(content) == 100 + len(TRUNCATION_MARKER)


def test_directory_discovery(tmp_path):
    _write_session(tmp_path / "s1.jsonl", [_msg("user", "hello from one")])
    _write_session(tmp_path / "s2.jsonl", [_msg("user", "hello from two")])
    (tmp_path / "notes.txt").write_text("not a session")

    episodes = list(ClaudeCodeSource(tmp_path).episodes())
    assert {e.id for e in episodes} == {"s1", "s2"}


def test_empty_session_yields_nothing(tmp_path):
    _write_session(tmp_path / "s3.jsonl", [{"type": "mode", "mode": "normal"}])
    assert list(ClaudeCodeSource(tmp_path / "s3.jsonl").episodes()) == []
