import pytest

from app.evaluation import build_report, first_hit_rank, hit_rate, mean_reciprocal_rank, normalize


def test_normalize_ignores_case_and_extra_spaces():
    assert normalize("  55   ANS\npour les Mineurs ") == "55 ans pour les mineurs"


def test_normalize_turns_arabic_presentation_forms_into_normal_letters():
    assert normalize("\ufe8d\ufedf") == "\u0627\u0644"


def test_first_hit_rank_is_one_based_and_needs_all_keywords():
    contents = ["rien ici", "le quinzième jour du mois", "quinzième jour et précomptée d'office"]
    assert first_hit_rank(contents, ["quinzième jour"]) == 2
    assert first_hit_rank(contents, ["quinzième jour", "précomptée d'office"]) == 3


def test_first_hit_rank_is_none_when_nothing_matches():
    assert first_hit_rank(["abc", "def"], ["xyz"]) is None
    assert first_hit_rank([], ["xyz"]) is None


def test_first_hit_rank_works_with_arabic_text():
    contents = ["نص آخر", "أجر   شهرين عن كل سنة"]
    assert first_hit_rank(contents, ["أجر شهرين"]) == 2


def test_hit_rate_counts_questions_found_within_k():
    ranks = [1, 3, None, 5]
    assert hit_rate(ranks, 1) == 0.25
    assert hit_rate(ranks, 3) == 0.5
    assert hit_rate(ranks, 5) == 0.75
    assert hit_rate([], 3) == 0.0


def test_mean_reciprocal_rank():
    assert mean_reciprocal_rank([1, 2, None, 4]) == pytest.approx((1 + 0.5 + 0 + 0.25) / 4)
    assert mean_reciprocal_rank([]) == 0.0


def test_report_lists_every_config_language_and_question():
    questions = [{"id": "fr-1", "language": "fr"}, {"id": "ar-1", "language": "ar"}]
    ranks = {"article_1500": [1, None], "fixed_500": [2, 3]}
    report = build_report(questions, ranks)
    assert "| article_1500 | fr | 1 | 100% |" in report
    assert "| article_1500 | ar | 1 | 0% |" in report
    assert "| fixed_500 | all | 2 |" in report
    assert "| fr-1 | fr | 1 | 2 |" in report
    assert "| ar-1 | ar | - | 3 |" in report