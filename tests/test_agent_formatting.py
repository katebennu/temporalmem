from temporalmem.agent.memory_agent import format_results
from temporalmem.retrieval.hybrid import SearchResult


def make_result(fact: str, obj: str, valid_at: str, score: float) -> SearchResult:
    return SearchResult(
        key=obj,
        fact=fact,
        predicate="lives_in",
        subject="user",
        object=obj,
        valid_at=valid_at,
        episode_ids=["e1"],
        score=score,
    )


def test_conflicting_facts_render_as_ordered_timeline():
    results = [
        make_result("User lives in Amsterdam.", "Amsterdam", "2025-01-01", 0.9),
        make_result("User lives in Berlin.", "Berlin", "2019-06-01", 0.8),
    ]
    text = format_results(results)
    assert "Timeline for user -[lives_in]->" in text
    assert text.index("Berlin") < text.index("Amsterdam")


def test_single_fact_renders_plainly():
    text = format_results([make_result("User lives in Berlin.", "Berlin", "2019-06-01", 0.8)])
    assert "Timeline" not in text
    assert text.startswith("- User lives in Berlin.")


def test_empty_results():
    assert format_results([]) == "No matching facts in memory."
