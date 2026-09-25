"""Phase 7 metrics. Predicted label is the scorecard label; HITL is not applied."""

from __future__ import annotations

from resume_screener.schemas import MatchLabel

LABELS: tuple[str, ...] = tuple(label.value for label in MatchLabel)

ACCURACY_GATE = 0.85
FPR_GATE = 0.05
P95_GATE_S = 90.0


def percentile(values: list[float], pct: float) -> float:
    """Linear percentile. `pct` is 0–100."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * weight


def confusion_matrix(
    pairs: list[tuple[str | None, str | None]],
) -> dict[str, list[list[int]]]:
    """Rows are ground truth, columns are predictions. Unscored rows are omitted."""
    index = {label: i for i, label in enumerate(LABELS)}
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    for expected, predicted in pairs:
        if expected not in index or predicted not in index:
            continue
        matrix[index[expected]][index[predicted]] += 1
    return {"labels": list(LABELS), "matrix": matrix}


def accuracy(pairs: list[tuple[str | None, str | None]]) -> float:
    if not pairs:
        return 0.0
    correct = sum(1 for expected, predicted in pairs if predicted == expected)
    return correct / len(pairs)


def false_positive_rate(pairs: list[tuple[str | None, str | None]]) -> float:
    """Not Relevant labelled Strong Match, divided by ground-truth Not Relevant."""
    negatives = [
        predicted
        for expected, predicted in pairs
        if expected == MatchLabel.not_relevant.value
    ]
    if not negatives:
        return 0.0
    false_positives = sum(
        1 for predicted in negatives if predicted == MatchLabel.strong_match.value
    )
    return false_positives / len(negatives)


def audit_completeness(audited_flags: list[bool]) -> float:
    if not audited_flags:
        return 0.0
    return sum(1 for flag in audited_flags if flag) / len(audited_flags)
