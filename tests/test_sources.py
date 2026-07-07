import json
from datetime import datetime

import pytest

from temporalmem.sources.longmemeval import LongMemEvalSource, parse_date

INSTANCE = {
    "question_id": "q1",
    "question_type": "knowledge-update",
    "question": "Where does the user live?",
    "answer": "Amsterdam",
    "question_date": "2023/06/01 (Thu) 10:00",
    "haystack_session_ids": ["s1", "s2"],
    "haystack_dates": ["2023/04/10 (Mon) 09:30", "2023/05/20 (Sat) 14:00"],
    "haystack_sessions": [
        [
            {"role": "user", "content": "I live in Berlin."},
            {"role": "assistant", "content": "Nice!"},
        ],
        [
            {"role": "user", "content": "I moved to Amsterdam last month.", "has_answer": True},
            {"role": "assistant", "content": "Congrats!"},
        ],
    ],
    "answer_session_ids": ["s2"],
}


@pytest.fixture
def dataset(tmp_path):
    path = tmp_path / "longmemeval_test.json"
    path.write_text(json.dumps([INSTANCE]))
    return path


def test_episodes(dataset):
    episodes = list(LongMemEvalSource(dataset).episodes())
    assert len(episodes) == 2
    assert episodes[0].id == "q1:s1"
    assert episodes[0].occurred_at == datetime(2023, 4, 10, 9, 30)
    assert "Berlin" in episodes[0].text()
    assert episodes[1].metadata["has_answer"] is True
    assert episodes[0].metadata["has_answer"] is False


def test_questions(dataset):
    questions = list(LongMemEvalSource(dataset).questions())
    assert len(questions) == 1
    question = questions[0]
    assert question.answer == "Amsterdam"
    assert question.question_date == datetime(2023, 6, 1, 10, 0)
    assert question.answer_session_ids == ["s2"]


def test_question_id_filter(dataset):
    assert list(LongMemEvalSource(dataset, {"other"}).episodes()) == []
    assert len(list(LongMemEvalSource(dataset, {"q1"}).episodes())) == 2


def test_parse_date_variants():
    assert parse_date("2023/05/20 (Sat) 14:00") == datetime(2023, 5, 20, 14, 0)
    assert parse_date("2023-05-20") == datetime(2023, 5, 20)
    with pytest.raises(ValueError):
        parse_date("someday soon")


def test_misaligned_haystack_raises(tmp_path):
    broken = dict(INSTANCE, haystack_dates=INSTANCE["haystack_dates"][:1])
    path = tmp_path / "broken.json"
    path.write_text(json.dumps([broken]))
    with pytest.raises(ValueError, match="misaligned"):
        list(LongMemEvalSource(path).episodes())
