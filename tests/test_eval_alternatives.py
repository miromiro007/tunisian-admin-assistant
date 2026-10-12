"""Tests for keyword alternatives in the evaluation."""
from app.evaluation import first_hit_rank


def test_alternatives_match_either_form() -> None:
    contents = ["fixé à 6,75 % du salaire", "taux de 6.75% du salaire"]
    assert first_hit_rank(contents, ["6.75|6,75"]) == 1
    assert first_hit_rank(contents[1:], ["6.75|6,75"]) == 1


def test_plain_keyword_still_needs_exact_text() -> None:
    assert first_hit_rank(["fixé à 6,75 %"], ["6.75"]) is None


def test_all_keywords_are_still_required() -> None:
    assert first_hit_rank(["taux 6,75 maladie"], ["6.75|6,75", "retraite"]) is None