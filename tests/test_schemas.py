from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from resume_screener.config import Settings
from resume_screener.schemas import (
    PII_FIELD_NAMES,
    CandidateProfile,
    DimensionScore,
    EducationEntry,
    EducationLevel,
    EvalCase,
    MatchLabel,
    RecommendedAction,
    RoleFamily,
    RoleProfile,
    Scorecard,
    TrackingRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _valid_candidate(**overrides) -> dict:
    payload = {
        "skills": ["python", "kubernetes"],
        "years_experience": 5.0,
        "education": [
            {
                "degree": "B.S.",
                "field": "Computer Science",
                "level": EducationLevel.bachelor,
            }
        ],
        "role_titles": ["Software Engineer"],
        "certifications": [],
        "project_keywords": ["distributed systems"],
    }
    payload.update(overrides)
    return payload


def _dimension(score: int = 5, evidence: list[str] | None = None) -> DimensionScore:
    if evidence is None:
        evidence = ["Worked 5 years as a backend engineer"] if score >= 8 else []
    return DimensionScore(score=score, evidence=evidence)


def _valid_scorecard(**overrides) -> Scorecard:
    payload = {
        "skills": _dimension(8, ["Python and Kubernetes on the resume"]),
        "experience": _dimension(7, ["5 years backend"]),
        "education": _dimension(6, ["B.S. Computer Science"]),
        "overall_label": MatchLabel.strong_match,
        "confidence": 0.9,
        "rationale": "Must-have skills and years are present.",
        "recruiter_questions": [],
        "recommended_action": RecommendedAction.advance_to_recruiter,
    }
    payload.update(overrides)
    return Scorecard.model_validate(payload)


def test_candidate_profile_rejects_pii_extra_fields():
    for field in sorted(PII_FIELD_NAMES):
        with pytest.raises(ValidationError):
            CandidateProfile.model_validate({**_valid_candidate(), field: "should fail"})


def test_candidate_profile_accepts_allowed_fields():
    profile = CandidateProfile.model_validate(_valid_candidate())
    dumped = profile.model_dump()
    assert set(dumped).isdisjoint(PII_FIELD_NAMES)
    assert profile.years_experience == 5.0
    assert profile.education[0].level is EducationLevel.bachelor


def test_education_entry_rejects_unknown_level():
    with pytest.raises(ValidationError):
        EducationEntry.model_validate(
            {"degree": "B.S.", "field": "CS", "level": "bootcamp"}
        )


def test_dimension_score_rejects_out_of_range():
    with pytest.raises(ValidationError):
        DimensionScore(score=0, evidence=[])
    with pytest.raises(ValidationError):
        DimensionScore(score=11, evidence=["too high"])


def test_dimension_score_requires_evidence_when_score_at_least_8():
    with pytest.raises(ValidationError):
        DimensionScore(score=8, evidence=[])
    assert DimensionScore(score=8, evidence=["quoted skill"]).score == 8
    assert DimensionScore(score=7, evidence=[]).score == 7


def test_scorecard_requires_questions_for_possible_fit_or_low_confidence():
    with pytest.raises(ValidationError):
        _valid_scorecard(
            overall_label=MatchLabel.possible_fit,
            confidence=0.8,
            recruiter_questions=[],
        )
    with pytest.raises(ValidationError):
        _valid_scorecard(confidence=0.4, recruiter_questions=[])
    card = _valid_scorecard(
        overall_label=MatchLabel.possible_fit,
        recruiter_questions=["Is the Kubernetes experience production or toy?"],
    )
    assert card.overall_label is MatchLabel.possible_fit


def test_role_profile_and_eval_case_round_trip():
    role = RoleProfile(
        title="Backend Engineer",
        role_family=RoleFamily.engineering,
        must_have_skills=["python"],
        nice_to_have_skills=["k8s"],
        min_years=3,
        education_req="bachelor",
    )
    case = EvalCase(
        id="eng-sm-01",
        role_family=RoleFamily.engineering,
        label=MatchLabel.strong_match,
        jd_path="data/eval/jds/eng-sm-01.md",
        resume_pdf="data/eval/resumes/eng-sm-01.pdf",
        notes="must-haves present",
    )
    assert role.role_family is case.role_family


def test_tracking_record_accepts_audit_shape():
    record = TrackingRecord(
        id="run-1",
        created_at=datetime.now(timezone.utc),
        resume_filename="eng-sm-01.pdf",
        jd_title="Backend Engineer",
        candidate_profile_json=_valid_candidate(),
        role_profile_json={"title": "Backend Engineer"},
        retrieved_chunk_ids=["chunk-1"],
        scorecard_json=_valid_scorecard().model_dump(mode="json"),
        predicted_label=MatchLabel.strong_match,
        final_label=MatchLabel.strong_match,
        confidence=0.9,
        needs_human_review=False,
        overridden=False,
        recruiter_notes="",
        thread_id="thread-1",
    )
    assert record.overridden is False


def test_env_example_documents_every_settings_field():
    example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    for name in Settings.model_fields:
        env_name = name.upper()
        assert env_name in example, f"{env_name} missing from .env.example"
