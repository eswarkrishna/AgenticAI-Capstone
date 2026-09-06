"""Recruiter-facing view models. Never include candidate name or other PII."""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass
from typing import Any, Literal

from resume_screener.schemas import (
    PII_FIELD_NAMES,
    MatchLabel,
    RecommendedAction,
    RoleFamily,
    ScreeningResult,
    TrackingRecord,
)

ReviewAction = Literal["keep", "upgrade", "downgrade"]

LABEL_ORDER: tuple[MatchLabel, ...] = (
    MatchLabel.not_relevant,
    MatchLabel.possible_fit,
    MatchLabel.strong_match,
)

LABEL_DISPLAY = {
    MatchLabel.strong_match: "Strong Match",
    MatchLabel.possible_fit: "Possible Fit",
    MatchLabel.not_relevant: "Not Relevant",
}

ACTION_DISPLAY = {
    RecommendedAction.advance_to_recruiter: "Advance to recruiter",
    RecommendedAction.hold_for_review: "Hold for review",
    RecommendedAction.reject: "Reject",
}

LOG_COLUMNS = (
    "created_at",
    "resume_filename",
    "jd_title",
    "role_family",
    "predicted_label",
    "final_label",
    "confidence",
    "overridden",
    "needs_human_review",
    "error",
    "thread_id",
)


@dataclass(frozen=True)
class ScorecardView:
    label: str
    confidence: float
    rationale: str
    skills_score: int
    skills_evidence: list[str]
    experience_score: int
    experience_evidence: list[str]
    education_score: int
    education_evidence: list[str]
    benchmark_titles: list[str]
    recommended_action: str
    recruiter_questions: list[str]
    hitl: bool
    jd_title: str
    resume_filename: str
    error: str | None


def format_label(label: MatchLabel | str | None) -> str:
    if label is None or label == "":
        return "—"
    if isinstance(label, str):
        try:
            label = MatchLabel(label)
        except ValueError:
            return label
    return LABEL_DISPLAY[label]


def format_action(action: RecommendedAction | str | None) -> str:
    if action is None:
        return "—"
    if isinstance(action, str):
        try:
            action = RecommendedAction(action)
        except ValueError:
            return action.replace("_", " ").title()
    return ACTION_DISPLAY[action]


def resolve_review_action(predicted: MatchLabel, action: ReviewAction) -> MatchLabel:
    idx = LABEL_ORDER.index(predicted)
    if action == "upgrade":
        return LABEL_ORDER[min(idx + 1, len(LABEL_ORDER) - 1)]
    if action == "downgrade":
        return LABEL_ORDER[max(idx - 1, 0)]
    return predicted


def scorecard_view(result: ScreeningResult) -> ScorecardView:
    card = result.scorecard
    tracking = result.tracking
    filename = tracking.resume_filename if tracking else ""
    jd_title = (result.role.title if result.role else "") or (
        tracking.jd_title if tracking else ""
    )
    payload = result.interrupt_payload or {}
    questions = list(card.recruiter_questions) if card else list(
        payload.get("recruiter_questions") or []
    )
    return ScorecardView(
        label=format_label(card.overall_label if card else payload.get("predicted_label")),
        confidence=(
            card.confidence
            if card is not None
            else float(payload.get("confidence") or 0.0)
        ),
        rationale=(card.rationale if card else str(payload.get("rationale") or "")),
        skills_score=card.skills.score if card else int(payload.get("skills_score") or 0),
        skills_evidence=list(card.skills.evidence) if card else [],
        experience_score=(
            card.experience.score if card else int(payload.get("experience_score") or 0)
        ),
        experience_evidence=list(card.experience.evidence) if card else [],
        education_score=(
            card.education.score if card else int(payload.get("education_score") or 0)
        ),
        education_evidence=list(card.education.evidence) if card else [],
        benchmark_titles=[chunk.title for chunk in result.retrieved_chunks if chunk.title],
        recommended_action=format_action(
            card.recommended_action if card else payload.get("recommended_action")
        ),
        recruiter_questions=questions,
        hitl=bool(result.interrupted or result.needs_human_review),
        jd_title=jd_title,
        resume_filename=filename,
        error=result.error,
    )


def view_as_dict(view: ScorecardView) -> dict[str, Any]:
    return asdict(view)


def assert_no_pii_keys(payload: dict[str, Any]) -> None:
    keys = set(payload)
    overlap = keys & PII_FIELD_NAMES
    if overlap:
        raise ValueError(f"PII keys are not allowed in recruiter views: {sorted(overlap)}")


def role_family_of(record: TrackingRecord) -> str:
    raw = record.role_profile_json or {}
    value = raw.get("role_family") or ""
    return str(value)


def filter_tracking(
    rows: list[TrackingRecord],
    *,
    label: MatchLabel | None = None,
    role_family: RoleFamily | None = None,
    overridden: bool | None = None,
) -> list[TrackingRecord]:
    out: list[TrackingRecord] = []
    family_value = role_family.value if role_family else None
    for row in rows:
        if label is not None and row.predicted_label is not label and row.final_label is not label:
            continue
        if family_value is not None and role_family_of(row) != family_value:
            continue
        if overridden is not None and row.overridden is not overridden:
            continue
        out.append(row)
    return out


def log_table_rows(rows: list[TrackingRecord]) -> list[dict[str, Any]]:
    table: list[dict[str, Any]] = []
    for row in rows:
        item = {
            "created_at": row.created_at.isoformat(),
            "resume_filename": row.resume_filename,
            "jd_title": row.jd_title,
            "role_family": role_family_of(row) or "—",
            "predicted_label": format_label(row.predicted_label),
            "final_label": format_label(row.final_label),
            "confidence": row.confidence,
            "overridden": row.overridden,
            "needs_human_review": row.needs_human_review,
            "error": row.error or "",
            "thread_id": row.thread_id,
        }
        assert_no_pii_keys(item)
        table.append(item)
    return table


def log_csv(rows: list[TrackingRecord]) -> str:
    table = log_table_rows(rows)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(LOG_COLUMNS))
    writer.writeheader()
    writer.writerows(table)
    return buf.getvalue()
