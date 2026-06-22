"""Phase 8 Critic validator — deterministic, reproducible.

Mirrors the notebook's `_run_validator_tests()` (9 checks): the same synopsis
always yields the same verdict, so these run on CPU with no GPU/LLM.
"""
from greenlight.validator import validate_synopsis

GOOD = ("In the dead of winter, a grieving family moves into a remote house where a "
        "malevolent presence stalks the halls. As the haunting deepens, they uncover a "
        "sinister curse rooted in the home's bloody past. To survive the night, they must "
        "confront the demon before the darkness claims them all.")

ROM = ("A cheerful baker and a clumsy florist keep bumping into each other at the spring market. "
       "Over a few bright weeks their playful banter blossoms into something neither expected. "
       "They must decide whether to risk it all on one leap.")


def test_good_is_valid(constraints):
    r = validate_synopsis(GOOD, "Horror", "Jan, Jul, Jun", constraints)
    assert r["valid"] and r["score"] >= 0.7


def test_good_has_genre_hits(constraints):
    r = validate_synopsis(GOOD, "Horror", "Jan, Jul, Jun", constraints)
    assert len(r["genre_hits"]) > 0


def test_empty_invalid(constraints):
    assert not validate_synopsis("", "Horror", "Jan", constraints)["valid"]


def test_too_short_fails_len(constraints):
    assert "length_ok" in validate_synopsis("A scary house.", "Horror", "Jan", constraints)["failed"]


def test_meta_text_fails(constraints):
    r = validate_synopsis(
        "Here is the synopsis: A family lives here. They are fine today.", "Horror", "Jan", constraints)
    assert "no_placeholder" in r["failed"]


def test_genre_mismatch_fails(constraints):
    assert "genre_signal" in validate_synopsis(ROM, "Horror", "Jan", constraints)["failed"]


def test_genre_mismatch_invalid(constraints):
    assert not validate_synopsis(ROM, "Horror", "Jan", constraints)["valid"]


def test_wrong_window_fails(constraints):
    assert "window_consistent" in validate_synopsis(GOOD, "Horror", "September", constraints)["failed"]


def test_user_override_ok(constraints):
    r = validate_synopsis(GOOD, "Horror", "June", constraints, user_window="June")
    assert "window_consistent" in r["passed"]
