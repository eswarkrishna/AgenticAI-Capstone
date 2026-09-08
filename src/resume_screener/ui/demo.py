"""Scripted parse/score payloads for the three Screen demo fixtures.

Used when OPENAI_API_KEY is unset so the recruiter UI can still be exercised
on eng-sm-01 / eng-pf-01 / eng-nr-02. Live uploads still require a key.
"""

from __future__ import annotations

from pathlib import Path

from resume_screener.eval.load import load_eval_cases, resolve_eval_path
from resume_screener.schemas import EvalCase

DEMO_CASE_IDS = ("eng-sm-01", "eng-pf-01", "eng-nr-02")


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


DEMO_PARSE = {
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

DEMO_SCORE = {
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

DEMO_LABELS = {
    "eng-sm-01": "Strong Match",
    "eng-pf-01": "Possible Fit (HITL)",
    "eng-nr-02": "Not Relevant",
}


def demo_case_id(filename: str) -> str | None:
    stem = Path(filename).stem
    if stem in DEMO_PARSE:
        return stem
    return None


def load_demo_case(case_id: str) -> EvalCase:
    cases = {item.id: item for item in load_eval_cases()}
    if case_id not in cases:
        raise KeyError(case_id)
    return cases[case_id]


def demo_paths(case_id: str) -> tuple[Path, str]:
    case = load_demo_case(case_id)
    resume = resolve_eval_path(case.resume_pdf)
    jd_text = resolve_eval_path(case.jd_path).read_text(encoding="utf-8")
    return resume, jd_text


def scripted_llms(case_id: str) -> tuple[ScriptedLLM, ScriptedLLM]:
    return ScriptedLLM([DEMO_PARSE[case_id]]), ScriptedLLM([DEMO_SCORE[case_id]])
