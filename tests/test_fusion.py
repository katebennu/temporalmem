from temporalmem.retrieval.fusion import rrf


def test_rrf_prefers_items_in_both_rankings():
    scores = rrf([["a", "b", "c"], ["b", "d"]], k=60)
    assert scores["b"] > scores["a"]
    assert scores["a"] > scores["c"]
    assert set(scores) == {"a", "b", "c", "d"}


def test_rrf_empty():
    assert rrf([]) == {}
    assert rrf([[]]) == {}
