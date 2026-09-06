"""Shared Pydantic contracts. Every agent and UI binds to these types."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

LOW_CONFIDENCE = 0.7
HIGH_SCORE_EVIDENCE_FLOOR = 8

PII_FIELD_NAMES = frozenset(
    {
        "name",
        "email",
        "phone",
        "gender",
        "age",
        "nationality",
        "photo",
        "address",
    }
)


class MatchLabel(str, Enum):
    strong_match = "strong_match"
    possible_fit = "possible_fit"
    not_relevant = "not_relevant"


class RoleFamily(str, Enum):
    engineering = "engineering"
    product_design = "product_design"
    operations = "operations"


class RecommendedAction(str, Enum):
    advance_to_recruiter = "advance_to_recruiter"
    hold_for_review = "hold_for_review"
    reject = "reject"


class EducationLevel(str, Enum):
    high_school = "high_school"
    bachelor = "bachelor"
    master = "master"
    phd = "phd"
    other = "other"


class EducationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    degree: str
    field: str
    level: EducationLevel


class CandidateProfile(BaseModel):
    """Scoring input. Demographic and contact fields are forbidden."""

    model_config = ConfigDict(extra="forbid")

    skills: list[str] = Field(default_factory=list)
    years_experience: float = Field(ge=0)
    education: list[EducationEntry] = Field(default_factory=list)
    role_titles: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    project_keywords: list[str] = Field(default_factory=list)


class RoleProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    role_family: RoleFamily
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    min_years: float = Field(ge=0)
    education_req: str = ""


class DimensionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=1, le=10)
    evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_evidence_for_high_scores(self) -> DimensionScore:
        if self.score >= HIGH_SCORE_EVIDENCE_FLOOR and not self.evidence:
            raise ValueError(
                f"evidence is required when score >= {HIGH_SCORE_EVIDENCE_FLOOR}"
            )
        return self


class Scorecard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: DimensionScore
    experience: DimensionScore
    education: DimensionScore
    overall_label: MatchLabel
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    recruiter_questions: list[str] = Field(default_factory=list)
    recommended_action: RecommendedAction

    @model_validator(mode="after")
    def require_questions_when_uncertain(self) -> Scorecard:
        needs_questions = (
            self.overall_label is MatchLabel.possible_fit
            or self.confidence < LOW_CONFIDENCE
        )
        if needs_questions and not self.recruiter_questions:
            raise ValueError(
                "recruiter_questions are required when overall_label is "
                "possible_fit or confidence is below the routing threshold"
            )
        return self


class TrackingRecord(BaseModel):
    """Audit row persisted for every screening run."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime
    resume_filename: str
    jd_title: str
    candidate_profile_json: dict[str, Any]
    role_profile_json: dict[str, Any]
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    scorecard_json: dict[str, Any] = Field(default_factory=dict)
    predicted_label: MatchLabel | None = None
    final_label: MatchLabel | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    needs_human_review: bool
    overridden: bool = False
    recruiter_notes: str = ""
    thread_id: str
    error: str | None = None


class EvalCase(BaseModel):
    """One labelled resume–JD pair in the Phase 2 eval set."""

    model_config = ConfigDict(extra="forbid")

    id: str
    role_family: RoleFamily
    label: MatchLabel
    jd_path: str
    resume_pdf: str
    notes: str = ""


class ParseResult(BaseModel):
    """Output of the parsing agent. Scoring must only see `candidate` (no PII)."""

    model_config = ConfigDict(extra="forbid")

    candidate: CandidateProfile
    role: RoleProfile
    raw_pii_redacted: bool = False


class RetrievedChunk(BaseModel):
    """One competency-benchmark hit from the retriever."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    text: str
    role_family: RoleFamily
    score: float = Field(ge=0.0)


class RecruiterFeedback(BaseModel):
    """HITL resume payload from `resume_review`."""

    model_config = ConfigDict(extra="forbid")

    final_label: MatchLabel
    notes: str = ""


class ScreeningResult(BaseModel):
    """Public result of `start_screening` / `resume_review`."""

    model_config = ConfigDict(extra="forbid")

    thread_id: str
    tracking_id: str
    scorecard: Scorecard | None = None
    candidate: CandidateProfile | None = None
    role: RoleProfile | None = None
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    needs_human_review: bool = False
    interrupted: bool = False
    interrupt_payload: dict[str, Any] | None = None
    tracking: TrackingRecord | None = None
    recruiter_feedback: RecruiterFeedback | None = None
    error: str | None = None
