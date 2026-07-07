from temporalmem.ingest import fact_key, normalize


def test_normalize():
    assert normalize("  New   York City ") == "new york city"
    assert normalize("NYC") == "nyc"


def test_fact_key_deterministic():
    key = fact_key("s1", "lives_in", "o1")
    assert key == fact_key("s1", "lives_in", "o1")
    assert key != fact_key("s1", "lives_in", "o2")
    assert len(key) == 32
