"""Tests for Reciprocal Rank Fusion (pure function, no database)."""
from app.search import reciprocal_rank_fusion


def test_item_in_both_lists_beats_item_first_in_only_one() -> None:
    # 2 is 2nd in both lists, 1 is 1st in one list only, 3 is 1st in the other only.
    fused = reciprocal_rank_fusion([[1, 2], [3, 2]])
    assert fused[0][0] == 2


def test_scores_follow_the_formula() -> None:
    fused = dict(reciprocal_rank_fusion([[10, 20]], k=60))
    assert fused[10] == 1 / 61
    assert fused[20] == 1 / 62


def test_empty_lists_give_empty_result() -> None:
    assert reciprocal_rank_fusion([[], []]) == []


def test_ties_are_broken_by_id() -> None:
    fused = reciprocal_rank_fusion([[5], [3]])
    assert [item_id for item_id, _ in fused] == [3, 5]