from __future__ import annotations

from datetime import datetime, timezone

from resume_screener.schemas import (
    PII_FIELD_NAMES,
    MatchLabel,
    RecommendedAction,
    RoleFamily,
    ScreeningResult,
    TrackingRecord,
)
from resume_screener.ui.display import (
    LOG_COLUMNS,
    filter_tracking,
    log_csv,
    log_table_rows,
    resolve_review_action,
    scorecard_view,
    view_as_dict,
)
from resume_screener.ui.runtime import NO_KEY_MESSAGE, run_screening
from resume_screener.ui.demo import demo_paths


def _tracking(**overrides) -> TrackingRecord:
    payload = dict(
        id="run-1",
        created_at=datetime.now(timezone.utc),
        resume_filename="eng-pf-01.pdf",
        jd_title="Staff Backend Engineer",
        candidate_profile_json={"skills": ["Python"]},
        role_profile_json={"title": "Staff Backend Engineer", "role_family": "engineering"},
        retrieved_chunk_ids=["bench-1"],
        scorecard_json={},
        predicted_label=MatchLabel.possible_fit,
        final_label=None,
        confidence=0.55,
        needs_human_review=True,
        overridden=False,
        recruiter_notes="",
        thread_id="thread-1",
        error=None,
    )
    payload.update(overrides)
    return TrackingRecord.model_validate(payload)


def test_resolve_review_action_upgrade_downgrade_keep():
    assert (
        resolve_review_action(MatchLabel.possible_fit, "upgrade")
        is MatchLabel.strong_match
    )
    assert (
        resolve_review_action(MatchLabel.possible_fit, "downgrade")
        is MatchLabel.not_relevant
    )
    assert (
        resolve_review_action(MatchLabel.possible_fit, "keep")
        is MatchLabel.possible_fit
    )
    assert (
        resolve_review_action(MatchLabel.strong_match, "upgrade")
        is MatchLabel.strong_match
    )
    assert (
        resolve_review_action(MatchLabel.not_relevant, "downgrade")
        is MatchLabel.not_relevant
    )


def test_filter_tracking_by_label_family_and_overridden():
    rows = [
        _tracking(id="a", predicted_label=MatchLabel.possible_fit, overridden=False),
        _tracking(
            id="b",
            predicted_label=MatchLabel.strong_match,
            final_label=MatchLabel.strong_match,
            needs_human_review=False,
            overridden=False,
            role_profile_json={"role_family": "operations"},
        ),
        _tracking(
            id="c",
            predicted_label=MatchLabel.possible_fit,
            final_label=MatchLabel.strong_match,
            overridden=True,
            needs_human_review=False,
        ),
    ]
    only_pf = filter_tracking(rows, label=MatchLabel.possible_fit)
    assert {row.id for row in only_pf} == {"a", "c"}
    only_eng = filter_tracking(rows, role_family=RoleFamily.engineering)
    assert {row.id for row in only_eng} == {"a", "c"}
    only_over = filter_tracking(rows, overridden=True)
    assert [row.id for row in only_over] == ["c"]


def test_log_rows_and_csv_have_no_pii_columns():
    rows = log_table_rows([_tracking()])
    assert rows
    assert PII_FIELD_NAMES.isdisjoint(rows[0])
    assert PII_FIELD_NAMES.isdisjoint(LOG_COLUMNS)
    csv_text = log_csv([_tracking()])
    header = csv_text.splitlines()[0]
    for field in PII_FIELD_NAMES:
        assert f",{field}," not in f",{header},"


def test_scorecard_view_omits_pii_and_shows_required_fields():
    from resume_screener.schemas import (
        DimensionScore,
        RetrievedChunk,
        RoleProfile,
        Scorecard,
    )

    result = ScreeningResult(
        thread_id="t",
        tracking_id="id-1",
        scorecard=Scorecard(
            skills=DimensionScore(score=8, evidence=["Python"]),
            experience=DimensionScore(score=7, evidence=["5 years"]),
            education=DimensionScore(score=6, evidence=["B.S."]),
            overall_label=MatchLabel.possible_fit,
            confidence=0.55,
            rationale="Education is thin versus the JD.",
            recruiter_questions=["Is tenure equivalent to the degree?"],
            recommended_action=RecommendedAction.hold_for_review,
        ),
        role=RoleProfile(
            title="Staff Backend Engineer",
            role_family=RoleFamily.engineering,
            must_have_skills=["Python"],
            min_years=5,
        ),
        retrieved_chunks=[
            RetrievedChunk(
                id="b1",
                title="Backend Software Engineer / Typical skills",
                text="Python",
                role_family=RoleFamily.engineering,
                score=0.9,
            )
        ],
        needs_human_review=True,
        interrupted=True,
        tracking=_tracking(),
    )
    view = scorecard_view(result)
    dumped = view_as_dict(view)
    assert PII_FIELD_NAMES.isdisjoint(dumped)
    assert "Jordan" not in str(dumped)
    assert view.skills_score == 8
    assert view.label == "Possible Fit"
    assert view.recommended_action == "Hold for review"
    assert view.benchmark_titles == ["Backend Software Engineer / Typical skills"]
    assert view.hitl is True
    assert view.recruiter_questions


def test_run_screening_demo_fixture_without_openai_key(tmp_path):
    from resume_screener.config import Settings

    resume, jd_text = demo_paths("eng-sm-01")
    result = run_screening(
        resume,
        jd_text,
        resume_filename="eng-sm-01.pdf",
        settings=Settings(openai_api_key=""),
        thread_id="ui-sm",
        sqlite_path=tmp_path / "tracking.db",
        checkpoint_path=tmp_path / "checkpoints.db",
        overrides_path=tmp_path / "overrides.jsonl",
    )
    assert result.error is None
    assert result.scorecard is not None
    assert result.scorecard.overall_label is MatchLabel.strong_match
    dumped = view_as_dict(scorecard_view(result))
    assert PII_FIELD_NAMES.isdisjoint(dumped)
    assert "Jordan" not in str(dumped).lower()
    assert "Hale" not in str(dumped)


def test_demo_possible_fit_override_round_trip(tmp_path):
    from resume_screener.config import Settings
    from resume_screener.ui.runtime import submit_review

    sqlite = tmp_path / "tracking.db"
    checkpoint = tmp_path / "checkpoints.db"
    resume, jd_text = demo_paths("eng-pf-01")
    started = run_screening(
        resume,
        jd_text,
        resume_filename="eng-pf-01.pdf",
        settings=Settings(openai_api_key=""),
        thread_id="ui-pf",
        sqlite_path=sqlite,
        checkpoint_path=checkpoint,
        overrides_path=tmp_path / "overrides.jsonl",
    )
    assert started.interrupted is True
    done = submit_review(
        "ui-pf",
        MatchLabel.strong_match,
        "tenure offsets the missing degree",
        checkpoint_path=checkpoint,
        sqlite_path=sqlite,
    )
    assert done.interrupted is False
    assert done.tracking is not None
    assert done.tracking.overridden is True
    assert done.tracking.final_label is MatchLabel.strong_match


def test_run_screening_requires_key_for_unknown_resume(tmp_path):
    import pytest

    from resume_screener.config import Settings

    fake = tmp_path / "custom.pdf"
    fake.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        run_screening(
            fake,
            "A job",
            resume_filename="custom.pdf",
            settings=Settings(openai_api_key=""),
        )
    assert "demo fixtures" in NO_KEY_MESSAGE.lower()
