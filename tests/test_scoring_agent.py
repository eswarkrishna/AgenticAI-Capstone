from __future__ import annotations

from resume_screener.agents.scoring_agent import (
    apply_decision,
    decide_label,
    derive_confidence,
    must_have_coverage,
    redact_resume_for_scoring,
    score_candidate,
)
from resume_screener.eval.load import load_eval_cases, resolve_eval_path
from resume_screener.parsing.pdf import extract_resume_text
from resume_screener.schemas import (
    CandidateProfile,
    DimensionScore,
    EducationEntry,
    EducationLevel,
    MatchLabel,
    RetrievedChunk,
    RoleFamily,
    RoleProfile,
)


class ScriptedLLM:
    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.calls: list = []

    def with_structured_output(self, schema):  # noqa: ARG002
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        return self.script.pop(0)


def _dim(score: int, *evidence: str) -> dict:
    return {"score": score, "evidence": list(evidence)}


def _backend_role(**overrides) -> RoleProfile:
    payload = dict(
        title="Backend Software Engineer",
        role_family=RoleFamily.engineering,
        must_have_skills=["Python", "REST APIs", "PostgreSQL", "Docker"],
        nice_to_have_skills=["Kubernetes"],
        min_years=5,
        education_req="bachelor in computer science or equivalent",
    )
    payload.update(overrides)
    return RoleProfile.model_validate(payload)


def _backend_candidate(**overrides) -> CandidateProfile:
    payload = dict(
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
        years_experience=7.0,
        education=[
            EducationEntry(
                degree="B.S.", field="Computer Science", level=EducationLevel.bachelor
            )
        ],
        role_titles=["Senior Backend Engineer"],
        certifications=[],
        project_keywords=["payment APIs"],
    )
    payload.update(overrides)
    return CandidateProfile.model_validate(payload)


def test_never_strong_match_when_must_haves_absent():
    candidate = _backend_candidate(
        skills=["Adobe Illustrator", "InDesign"], project_keywords=[]
    )
    role = _backend_role()
    assert must_have_coverage(candidate, role, []) == 0
    label = decide_label(
        skills_score=9,
        experience_score=8,
        education_ok=True,
        coverage=0.0,
        years=7,
        min_years=5,
    )
    assert label is not MatchLabel.strong_match


def test_k8s_alias_counts_as_kubernetes():
    candidate = _backend_candidate(skills=["k8s", "Docker", "GCP"])
    role = _backend_role(must_have_skills=["Kubernetes", "Docker"])
    assert must_have_coverage(candidate, role, []) == 1.0


def test_short_skill_names_do_not_match_as_substrings():
    candidate = _backend_candidate(skills=["MongoDB", "Django", "Redis", "JavaScript"])
    role = _backend_role(must_have_skills=["Go", "R", "Java"])
    assert must_have_coverage(candidate, role, []) == 0.0


def test_half_coverage_is_not_most_must_haves():
    label = decide_label(
        skills_score=9,
        experience_score=9,
        education_ok=True,
        coverage=0.5,
        years=7,
        min_years=5,
    )
    assert label is not MatchLabel.strong_match


def test_apache_spark_matches_spark():
    candidate = _backend_candidate(skills=["Spark", "Python", "SQL", "Snowflake"])
    role = _backend_role(must_have_skills=["Apache Spark", "Python"])
    assert must_have_coverage(candidate, role, []) == 1.0


def test_retrieved_kb_file_supplies_synonyms():
    candidate = _backend_candidate(skills=["Docker", "Prometheus"])
    role = _backend_role(must_have_skills=["containers", "observability"])
    assert must_have_coverage(candidate, role, []) == 0.0
    chunk = RetrievedChunk(
        id="devops-sre::education",
        title="DevOps / Education",
        text="Bachelor in CS or engineering common.",
        role_family=RoleFamily.engineering,
        score=0.4,
    )
    assert must_have_coverage(candidate, role, [chunk]) == 1.0


def test_rag_synonym_line_counts_toward_coverage():
    candidate = _backend_candidate(skills=["tf"])
    role = _backend_role(must_have_skills=["Terraform"])
    assert must_have_coverage(candidate, role, []) == 0.0
    chunk = RetrievedChunk(
        id="devops-sre::experience",
        title="DevOps / Experience band",
        text="Synonyms: tf for Terraform.",
        role_family=RoleFamily.engineering,
        score=0.8,
    )
    assert must_have_coverage(candidate, role, [chunk]) == 1.0


def test_confidence_rises_with_margin_and_threshold_is_real():
    clear = derive_confidence(
        label=MatchLabel.strong_match,
        skills_score=10,
        experience_score=10,
        education_ok=True,
        coverage=1.0,
        years=8,
        min_years=5,
        thin=False,
        evidence_count=6,
    )
    borderline = derive_confidence(
        label=MatchLabel.strong_match,
        skills_score=8,
        experience_score=7,
        education_ok=True,
        coverage=2 / 3,
        years=5,
        min_years=5,
        thin=True,
        evidence_count=3,
    )
    weak_negative = derive_confidence(
        label=MatchLabel.not_relevant,
        skills_score=3,
        experience_score=4,
        education_ok=True,
        coverage=0.0,
        years=1,
        min_years=6,
        thin=False,
        evidence_count=2,
    )
    assert clear > borderline
    assert clear >= 0.7
    assert borderline < 0.7
    assert weak_negative < 0.7


def test_score_prompt_drops_name_email_and_phone():
    resume = "\n".join(
        [
            "# Jordan Hale",
            "jordan.hale@example.com",
            "555-010-1234",
            "https://linkedin.com/in/jordan",
            "Senior Backend Engineer. Python, PostgreSQL, Docker.",
        ]
    )
    redacted = redact_resume_for_scoring(resume)
    assert "Jordan Hale" not in redacted
    assert "jordan.hale@example.com" not in redacted
    assert "555-010-1234" not in redacted
    assert "linkedin.com" not in redacted
    assert "Python" in redacted

    llm = ScriptedLLM(
        [
            {
                "skills": _dim(9, "Python", "PostgreSQL", "Docker"),
                "experience": _dim(8, "Senior Backend Engineer"),
                "education": _dim(5, "not stated"),
                "rationale": "Backend skills are on the resume.",
                "recruiter_questions": [],
            }
        ]
    )
    score_candidate(
        _backend_candidate(),
        _backend_role(),
        resume,
        llm=llm,
        chunks=[
            RetrievedChunk(
                id="bench-1",
                title="Backend",
                text="Python PostgreSQL Docker",
                role_family=RoleFamily.engineering,
                score=0.9,
            )
        ],
    )
    blob = str(llm.calls[0])
    assert "Jordan Hale" not in blob
    assert "jordan.hale@example.com" not in blob
    assert "555-010-1234" not in blob
    assert "linkedin.com" not in blob
    assert "Python" in blob


def test_score_candidate_strong_possible_and_not_relevant_fixtures():
    cases = {case.id: case for case in load_eval_cases()}
    scenarios = [
        (
            "eng-sm-01",
            MatchLabel.strong_match,
            {
                "skills": _dim(9, "Python", "PostgreSQL", "Docker"),
                "experience": _dim(8, "Senior Backend Engineer", "7 years"),
                "education": _dim(8, "B.S. Computer Science"),
                "rationale": "Must-have skills and years are present on the resume.",
                "recruiter_questions": [],
            },
        ),
        (
            "eng-pf-01",
            MatchLabel.possible_fit,
            {
                "skills": _dim(8, "Python", "PostgreSQL"),
                "experience": _dim(9, "11 years", "Staff Engineer"),
                "education": _dim(4, "No formal degree"),
                "rationale": "Strong experience but education is missing versus the JD.",
                "recruiter_questions": [
                    "Is the missing degree offset by 11 years of production work?"
                ],
            },
        ),
        (
            "eng-nr-02",
            MatchLabel.not_relevant,
            {
                "skills": _dim(2, "Graphic Designer", "Adobe Illustrator"),
                "experience": _dim(3, "Studio North"),
                "education": _dim(4, "B.F.A. Graphic Design"),
                "rationale": "Design background with no backend engineering evidence.",
                "recruiter_questions": [],
            },
        ),
    ]

    empty_chunk = RetrievedChunk(
        id="bench-1",
        title="Backend Software Engineer / Typical skills",
        text="Python REST APIs PostgreSQL Docker",
        role_family=RoleFamily.engineering,
        score=0.9,
    )

    for case_id, expected_label, llm_out in scenarios:
        case = cases[case_id]
        resume_text = extract_resume_text(resolve_eval_path(case.resume_pdf))
        if expected_label is MatchLabel.strong_match:
            candidate = _backend_candidate()
            role = _backend_role()
        elif expected_label is MatchLabel.possible_fit:
            candidate = _backend_candidate(
                years_experience=11.0,
                education=[],
                skills=["Python", "PostgreSQL", "Redis", "Kafka"],
                role_titles=["Staff Engineer"],
            )
            role = _backend_role(
                title="Staff Backend Engineer",
                min_years=8,
                education_req="bachelor in CS required",
            )
        else:
            candidate = CandidateProfile(
                skills=["Adobe Illustrator", "InDesign", "Photoshop", "Figma"],
                years_experience=6.0,
                education=[
                    EducationEntry(
                        degree="B.F.A.",
                        field="Graphic Design",
                        level=EducationLevel.bachelor,
                    )
                ],
                role_titles=["Graphic Designer"],
                certifications=[],
                project_keywords=["brand kits"],
            )
            role = _backend_role()

        llm = ScriptedLLM([llm_out])
        card, chunks = score_candidate(
            candidate,
            role,
            resume_text,
            llm=llm,
            chunks=[empty_chunk],
        )
        assert card.overall_label is expected_label, case_id
        assert chunks
        type(card).model_validate(card.model_dump())
        if expected_label is MatchLabel.possible_fit:
            assert card.recruiter_questions
        if card.skills.score >= 8:
            assert card.skills.evidence


def test_apply_decision_adds_questions_when_possible_fit():
    skills = DimensionScore(score=6, evidence=["Python on resume"])
    experience = DimensionScore(score=6, evidence=["5 years backend"])
    education = DimensionScore(score=5, evidence=["B.S."])
    card = apply_decision(
        skills,
        experience,
        education,
        _backend_candidate(skills=["Python"]),
        _backend_role(),
        [],
        "Mixed signals.",
        [],
    )
    assert card.overall_label is MatchLabel.possible_fit
    assert card.recruiter_questions
    assert card.confidence < 0.7
