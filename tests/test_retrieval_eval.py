from __future__ import annotations

import pytest

from app.retrieval_eval import evaluate_rankings, precision_at_k, recall_at_k, reciprocal_rank


def test_precision_recall_and_reciprocal_rank() -> None:
    ranked = ["irrelevant", "relevant-a", "relevant-b", "other"]
    relevant = {"relevant-a", "relevant-b"}
    assert precision_at_k(ranked, relevant, 3) == pytest.approx(2 / 3)
    assert recall_at_k(ranked, relevant, 3) == pytest.approx(1.0)
    assert reciprocal_rank(ranked, relevant) == pytest.approx(0.5)


def test_missing_relevant_results_score_zero() -> None:
    assert precision_at_k(["x", "y"], {"z"}, 2) == 0.0
    assert recall_at_k(["x", "y"], {"z"}, 2) == 0.0
    assert reciprocal_rank(["x", "y"], {"z"}) == 0.0


def test_empty_rankings_and_no_relevant_labels() -> None:
    assert precision_at_k([], {"x"}, 5) == 0.0
    assert recall_at_k(["x"], set(), 5) == 0.0
    with pytest.raises(ValueError, match="at least one query"):
        evaluate_rankings({"unlabeled": []}, {"unlabeled": ["x"]})


def test_macro_averaged_evaluation() -> None:
    scores = evaluate_rankings(
        {"query-a": {"a", "b"}, "query-b": {"d"}},
        {"query-a": ["a", "noise", "b"], "query-b": ["noise", "d"]},
        k=2,
    )
    assert scores["queries"] == 2
    assert scores["k"] == 2
    assert scores["precision_at_k"] == pytest.approx(0.5)
    assert scores["recall_at_k"] == pytest.approx(0.5)
    assert scores["mrr"] == pytest.approx(0.75)


@pytest.mark.parametrize("k", [0, -1, True])
def test_invalid_k_is_rejected(k: int) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        precision_at_k(["a"], {"a"}, k)
