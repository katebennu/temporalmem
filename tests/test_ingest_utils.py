from temporalmem.ingest import fact_key, is_functional, normalize


def test_normalize():
    assert normalize("  New   York City ") == "new york city"
    assert normalize("NYC") == "nyc"


def test_is_functional_overrides_llm_flag():
    assert is_functional("owns", True) is False
    assert is_functional("lives_in", False) is True
    assert is_functional("unknown_predicate", True) is True
    assert is_functional("unknown_predicate", False) is False


def test_fact_key_deterministic():
    key = fact_key("s1", "lives_in", "o1")
    assert key == fact_key("s1", "lives_in", "o1")
    assert key != fact_key("s1", "lives_in", "o2")
    assert len(key) == 32
