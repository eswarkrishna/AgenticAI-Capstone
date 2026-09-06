from __future__ import annotations

import json

from resume_screener.eval.load import load_eval_cases, resolve_eval_path
from resume_screener.graph.workflow import (
    resume_review,
    should_interrupt,
    start_screening,
    thread_has_pending_interrupt,
)
from resume_screener.persistence.tracking import export_csv, list_all, list_pending_review
from resume_screener.schemas import (
    DimensionScore,
    MatchLabel,
    RetrievedChunk,
    RoleFamily,
    Scorecard,
)

CHUNK = RetrievedChunk(
    id="bench-1",
    title="Backend Software Engineer / Typical skills",
    text="Python REST APIs PostgreSQL Docker",
    role_family=RoleFamily.engineering,
    score=0.9,
)


class ScriptedLLM:
    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.calls: list = []

    def with_structured_output(self, schema):  # noqa: ARG002
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class BoomLLM:
    def with_structured_output(self, schema):  # noqa: ARG002
        return self

    def invoke(self, messages):  # noqa: ARG002
        raise RuntimeError("model down")


def _dim(score: int, *evidence: str) -> dict:
    return {"score": score, "evidence": list(evidence)}


def _backend_role(**overrides) -> dict:
    payload = dict(
        title="Backend Software Engineer",
        role_family="engineering",
        must_have_skills=["Python", "REST APIs", "PostgreSQL", "Docker"],
        nice_to_have_skills=["Kubernetes"],
        min_years=5.0,
        education_req="bachelor in computer science or equivalent",
    )
    payload.update(overrides)
    return payload


def _backend_candidate(**overrides) -> dict:
    payload = dict(
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
        years_experience=7.0,
        education=[
            {"degree": "B.S.", "field": "Computer Science", "level": "bachelor"}
        ],
        role_titles=["Senior Backend Engineer"],
        certifications=[],
        project_keywords=["payment APIs"],
    )
    payload.update(overrides)
    return payload


PARSE = {
    "eng-sm-01": {
        "candidate": _backend_candidate(),
        "role": _backend_role(),
    },
    "eng-pf-01": {
        "candidate": _backend_candidate(
            years_experience=11.0,
            education=[],
            skills=["Python", "PostgreSQL", "Redis", "Kafka"],
            role_titles=["Staff Engineer"],
        ),
        "role": _backend_role(
            title="Staff Backend Engineer",
            min_years=8.0,
            education_req="bachelor in CS required",
        ),
    },
    "eng-nr-02": {
        "candidate": {
            "skills": ["Adobe Illustrator", "InDesign", "Photoshop", "Figma"],
            "years_experience": 6.0,
            "education": [
                {"degree": "B.F.A.", "field": "Graphic Design", "level": "bachelor"}
            ],
            "role_titles": ["Graphic Designer"],
            "certifications": [],
            "project_keywords": ["brand kits"],
        },
        "role": _backend_role(),
    },
}

SCORE = {
    "eng-sm-01": {
        "skills": _dim(9, "Python", "PostgreSQL", "Docker"),
        "experience": _dim(8, "Senior Backend Engineer", "7 years"),
        "education": _dim(8, "B.S. Computer Science", "State University"),
        "rationale": "Must-have skills and years are present on the resume.",
        "recruiter_questions": [],
    },
    "eng-pf-01": {
        "skills": _dim(8, "Python", "PostgreSQL"),
        "experience": _dim(9, "11 years", "Staff Engineer"),
        "education": _dim(4, "No formal degree"),
        "rationale": "Strong experience but education is missing versus the JD.",
        "recruiter_questions": [
            "Is the missing degree offset by 11 years of production work?"
        ],
    },
    "eng-nr-02": {
        "skills": _dim(2, "Graphic Designer", "Adobe Illustrator"),
        "experience": _dim(3, "Studio North"),
        "education": _dim(4, "B.F.A. Graphic Design"),
        "rationale": "Design background with no backend engineering evidence.",
        "recruiter_questions": [],
    },
}


def _store(tmp_path):
    return {
        "sqlite": tmp_path / "tracking.db",
        "checkpoint": tmp_path / "checkpoints.db",
        "overrides": tmp_path / "overrides.jsonl",
    }


def _case(case_id: str):
    return {item.id: item for item in load_eval_cases()}[case_id]


def _run(case_id: str, store: dict, thread_id: str, parse_llm=None, score_llm=None):
    case = _case(case_id)
    return start_screening(
        resolve_eval_path(case.resume_pdf),
        resolve_eval_path(case.jd_path).read_text(encoding="utf-8"),
        thread_id,
        parse_llm=parse_llm or ScriptedLLM([PARSE[case_id]]),
        score_llm=score_llm or ScriptedLLM([SCORE[case_id]]),
        chunks=[CHUNK],
        sqlite_path=store["sqlite"],
        checkpoint_path=store["checkpoint"],
        overrides_path=store["overrides"],
    )


def test_should_interrupt_only_high_confidence_auto_labels():
    def card(label: MatchLabel, confidence: float) -> Scorecard:
        questions = ["Why?"] if label is MatchLabel.possible_fit or confidence < 0.7 else []
        return Scorecard(
            skills=DimensionScore(score=8, evidence=["Python"]),
            experience=DimensionScore(score=7, evidence=["5 years"]),
            education=DimensionScore(score=6, evidence=["B.S."]),
            overall_label=label,
            confidence=confidence,
            rationale="fixture",
            recruiter_questions=questions,
            recommended_action=(
                "hold_for_review"
                if label is MatchLabel.possible_fit
                else (
                    "advance_to_recruiter"
                    if label is MatchLabel.strong_match
                    else "reject"
                )
            ),
        )

    assert should_interrupt(card(MatchLabel.strong_match, 0.88)) is False
    assert should_interrupt(card(MatchLabel.not_relevant, 0.82)) is False
    assert should_interrupt(card(MatchLabel.possible_fit, 0.9)) is True
    assert should_interrupt(card(MatchLabel.strong_match, 0.4)) is True


def test_high_confidence_strong_and_not_relevant_auto_persist(tmp_path):
    store = _store(tmp_path)
    strong = _run("eng-sm-01", store, "thread-sm")
    assert strong.error is None
    assert strong.interrupted is False
    assert strong.needs_human_review is False
    assert strong.scorecard is not None
    assert strong.scorecard.overall_label is MatchLabel.strong_match
    assert strong.scorecard.confidence >= 0.7
    assert thread_has_pending_interrupt("thread-sm", store["checkpoint"]) is False
    assert list_pending_review(store["sqlite"]) == []

    weak = _run("eng-nr-02", store, "thread-nr")
    assert weak.interrupted is False
    assert weak.scorecard is not None
    assert weak.scorecard.overall_label is MatchLabel.not_relevant
    assert thread_has_pending_interrupt("thread-nr", store["checkpoint"]) is False

    rows = list_all(store["sqlite"])
    assert len(rows) == 2
    by_thread = {row.thread_id: row for row in rows}
    assert by_thread["thread-sm"].final_label is MatchLabel.strong_match
    assert by_thread["thread-sm"].needs_human_review is False
    assert by_thread["thread-nr"].final_label is MatchLabel.not_relevant
    assert not store["overrides"].exists() or store["overrides"].read_text() == ""


def test_possible_fit_leaves_interrupt(tmp_path):
    store = _store(tmp_path)
    result = _run("eng-pf-01", store, "thread-pf")
    assert result.error is None
    assert result.interrupted is True
    assert result.needs_human_review is True
    assert result.scorecard is not None
    assert result.scorecard.overall_label is MatchLabel.possible_fit
    assert result.interrupt_payload is not None
    assert result.interrupt_payload["recruiter_questions"]
    assert thread_has_pending_interrupt("thread-pf", store["checkpoint"]) is True
    pending = list_pending_review(store["sqlite"])
    assert len(pending) == 1
    assert pending[0].thread_id == "thread-pf"
    assert pending[0].final_label is None
    assert pending[0].needs_human_review is True


def test_resume_review_sets_overridden_and_final_label(tmp_path):
    store = _store(tmp_path)
    kept_start = _run("eng-pf-01", store, "thread-override")
    assert kept_start.interrupted is True
    kept = resume_review(
        "thread-override",
        MatchLabel.possible_fit,
        notes="keep as possible",
        checkpoint_path=store["checkpoint"],
        sqlite_path=store["sqlite"],
    )
    upgraded_start = _run("eng-pf-01", store, "thread-upgrade")
    upgraded = resume_review(
        "thread-upgrade",
        MatchLabel.strong_match,
        notes="degree equivalent via tenure",
        checkpoint_path=store["checkpoint"],
        sqlite_path=store["sqlite"],
    )
    assert kept.interrupted is False
    assert kept.tracking is not None
    assert kept.tracking.final_label is MatchLabel.possible_fit
    assert kept.tracking.overridden is False
    assert kept.tracking.needs_human_review is False

    assert upgraded.interrupted is False
    assert upgraded.tracking is not None
    assert upgraded.tracking.predicted_label is MatchLabel.possible_fit
    assert upgraded.tracking.final_label is MatchLabel.strong_match
    assert upgraded.tracking.overridden is True
    assert upgraded.tracking.recruiter_notes == "degree equivalent via tenure"
    assert thread_has_pending_interrupt("thread-upgrade", store["checkpoint"]) is False
    assert list_pending_review(store["sqlite"]) == []

    lines = [
        json.loads(line)
        for line in store["overrides"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == 2
    by_thread = {line["thread_id"]: line for line in lines}
    assert by_thread["thread-override"]["overridden"] is False
    assert by_thread["thread-upgrade"]["overridden"] is True
    assert by_thread["thread-upgrade"]["final_label"] == "strong_match"
    assert upgraded_start.interrupted is True


def test_failed_parse_and_score_still_write_audit_rows(tmp_path):
    store = _store(tmp_path)
    case = _case("eng-sm-01")
    parse_fail = start_screening(
        resolve_eval_path(case.resume_pdf),
        resolve_eval_path(case.jd_path).read_text(encoding="utf-8"),
        "thread-parse-fail",
        parse_llm=BoomLLM(),
        score_llm=ScriptedLLM([SCORE["eng-sm-01"]]),
        chunks=[CHUNK],
        sqlite_path=store["sqlite"],
        checkpoint_path=store["checkpoint"],
        overrides_path=store["overrides"],
    )
    assert parse_fail.error and "parse failed" in parse_fail.error
    assert parse_fail.interrupted is False
    assert parse_fail.tracking is not None
    assert parse_fail.tracking.error
    assert parse_fail.tracking.predicted_label is None

    score_fail = start_screening(
        resolve_eval_path(case.resume_pdf),
        resolve_eval_path(case.jd_path).read_text(encoding="utf-8"),
        "thread-score-fail",
        parse_llm=ScriptedLLM([PARSE["eng-sm-01"]]),
        score_llm=BoomLLM(),
        chunks=[CHUNK],
        sqlite_path=store["sqlite"],
        checkpoint_path=store["checkpoint"],
        overrides_path=store["overrides"],
    )
    assert score_fail.error and "score failed" in score_fail.error
    assert score_fail.interrupted is False
    assert score_fail.candidate is not None
    assert score_fail.tracking is not None
    assert score_fail.tracking.error
    assert thread_has_pending_interrupt("thread-parse-fail", store["checkpoint"]) is False
    assert thread_has_pending_interrupt("thread-score-fail", store["checkpoint"]) is False

    rows = list_all(store["sqlite"])
    assert len(rows) == 2
    assert all(row.error for row in rows)
    csv_path = export_csv(store["sqlite"].parent / "tracking.csv", sqlite_path=store["sqlite"])
    header = csv_path.read_text(encoding="utf-8").splitlines()[0].lower()
    assert "email" not in header
    assert "gender" not in header
    assert "phone" not in header
