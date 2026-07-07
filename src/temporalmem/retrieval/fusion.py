from __future__ import annotations


def rrf(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal rank fusion: fuse ranked key lists into a single score map."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    return scores
