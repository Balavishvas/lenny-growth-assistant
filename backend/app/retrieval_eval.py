"""Deterministic ranking metrics for retrieval evaluation.

These helpers accept ranked identifiers and curated relevant identifiers. They
do not call the database, embedding provider, or LLM, so unit tests are fast and
reproducible.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence


def precision_at_k(ranked_ids: Sequence[str], relevant_ids: Iterable[str], k: int) -> float:
    """Fraction of the top-k retrieved identifiers that are relevant."""
    _validate_k(k)
    relevant = set(relevant_ids)
    if not ranked_ids[:k]:
        return 0.0
    return sum(identifier in relevant for identifier in ranked_ids[:k]) / k


def recall_at_k(ranked_ids: Sequence[str], relevant_ids: Iterable[str], k: int) -> float:
    """Fraction of all known relevant identifiers found in the top-k."""
    _validate_k(k)
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    return len(set(ranked_ids[:k]) & relevant) / len(relevant)


def reciprocal_rank(ranked_ids: Sequence[str], relevant_ids: Iterable[str]) -> float:
    """Reciprocal rank of the first relevant result, or zero if none is found."""
    relevant = set(relevant_ids)
    for rank, identifier in enumerate(ranked_ids, start=1):
        if identifier in relevant:
            return 1.0 / rank
    return 0.0


def evaluate_rankings(
    cases: Mapping[str, Iterable[str]],
    rankings: Mapping[str, Sequence[str]],
    k: int = 5,
) -> dict[str, float | int]:
    """Compute macro-averaged Precision@K, Recall@K, and MRR.

    Cases map queries to curated relevant identifiers; rankings map the same
    queries to identifiers in retrieval order. Missing rankings count as empty.
    Queries without relevant labels are excluded from the benchmark.
    """
    _validate_k(k)
    scored = [(query, set(relevant)) for query, relevant in cases.items() if set(relevant)]
    if not scored:
        raise ValueError("at least one query must have a relevant identifier")

    precisions, recalls, reciprocal_ranks = [], [], []
    for query, relevant in scored:
        ranked = list(rankings.get(query, ()))
        precisions.append(precision_at_k(ranked, relevant, k))
        recalls.append(recall_at_k(ranked, relevant, k))
        reciprocal_ranks.append(reciprocal_rank(ranked, relevant))

    count = len(scored)
    return {
        "queries": count,
        "precision_at_k": sum(precisions) / count,
        "recall_at_k": sum(recalls) / count,
        "mrr": sum(reciprocal_ranks) / count,
        "k": k,
    }


def _validate_k(k: int) -> None:
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError("k must be a positive integer")
