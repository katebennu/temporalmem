import pytest

from temporalmem.cli import build_source
from temporalmem.sources.claudecode import ClaudeCodeSource
from temporalmem.sources.longmemeval import LongMemEvalSource


def test_default_source_is_longmemeval(tmp_path):
    source = build_source("longmemeval", str(tmp_path / "data.json"), ["q1"])
    assert isinstance(source, LongMemEvalSource)


def test_claude_code_source_dispatch(tmp_path):
    source = build_source("claude-code", str(tmp_path), None)
    assert isinstance(source, ClaudeCodeSource)


def test_question_id_rejected_for_claude_code(tmp_path):
    with pytest.raises(SystemExit):
        build_source("claude-code", str(tmp_path), ["q1"])
