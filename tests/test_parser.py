"""Natural-prompt parser guardrails — deterministic, tested.

Mirrors the notebook's `_run_parser_tests()` (15 checks). The LLM extraction is
fuzzy; these exercise the exact safety net (`_normalize`, `_match_genre`,
`_parse_budget`) that clamps genre, maps seasons->months, and trusts numbers in
text — so "250 words" and "$50M" are never confused.
"""
from greenlight.parser import _match_genre, _normalize


def test_genre_from_text():
    assert _match_genre("a thriller film") == "Thriller"


def test_scifi_alias():
    assert _match_genre("a sci-fi movie") == "Science Fiction"


def test_bad_genre_fallback():
    assert _normalize({"genre": "Xyz"}, "a thriller film")["genre"] == "Thriller"


def test_unknown_default():
    assert _normalize({"genre": None}, "make me a film")["genre"] == "Drama"


def test_best_window_none():
    assert _normalize({"window": "best"}, "best release window")["window"] is None


def test_summer_maps_june():
    assert _normalize({"window": "summer"}, "summer release")["window"] == "June"


def test_month_passthrough():
    assert _normalize({"window": "October"}, "october")["window"] == "October"


def test_length_from_text():
    assert _normalize({"length": None}, "a 250 word synopsis")["length"] == 250


def test_length_default():
    assert _normalize({"length": None}, "a synopsis")["length"] == 80


def test_length_clamped():
    assert _normalize({"length": 99999}, "x")["length"] == 80


def test_budget_50m_dollar():
    assert _normalize({}, "horror under 50M$")["budget"] == 50_000_000


def test_budget_million_words():
    assert _normalize({}, "budget of 50 million dollars")["budget"] == 50_000_000


def test_budget_full_number():
    assert _normalize({}, "a $50,000,000 thriller")["budget"] == 50_000_000


def test_budget_none():
    assert _normalize({}, "a 250 word comedy")["budget"] is None


def test_budget_500k():
    assert _normalize({}, "a 500k indie")["budget"] == 500_000
