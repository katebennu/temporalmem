from collections import Counter
from datetime import datetime

from temporalmem.evaluation.harness import stratified_sample
from temporalmem.sources.longmemeval import Question


def make_question(index: int, question_type: str) -> Question:
    return Question(
        question_id=f"q{question_type}{index}",
        question_type=question_type,
        question="?",
        answer="a",
        question_date=datetime(2023, 1, 1),
    )


def make_pool() -> list[Question]:
    return [
        make_question(i, qtype)
        for qtype in ("temporal-reasoning", "knowledge-update", "multi-session")
        for i in range(10)
    ]


def test_stratified_sample_is_even_across_types():
    sampled = stratified_sample(make_pool(), 6, seed=1)
    counts = Counter(question.question_type for question in sampled)
    assert len(sampled) == 6
    assert set(counts.values()) == {2}


def test_stratified_sample_deterministic_per_seed():
    ids_a = [question.question_id for question in stratified_sample(make_pool(), 9, seed=7)]
    ids_b = [question.question_id for question in stratified_sample(make_pool(), 9, seed=7)]
    assert ids_a == ids_b


def test_stratified_sample_caps_at_pool_size():
    pool = make_pool()
    sampled = stratified_sample(pool, 100, seed=1)
    assert len(sampled) == len(pool)
    assert len({question.question_id for question in sampled}) == len(pool)
