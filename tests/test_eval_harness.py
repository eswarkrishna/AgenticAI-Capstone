"""Phase 7 metric math and a scripted one-case harness run (no live LLM)."""

from __future__ import annotations

from resume_screener.config import Settings
from resume_screener.eval.harness import build_report, format_stdout, score_case
from resume_screener.eval.load import load_eval_cases
from resume_screener.eval.metrics import (
    accuracy,
    audit_completeness,
    confusion_matrix,
    false_positive_rate,
    percentile,
)
from resume_screener.schemas import MatchLabel, RetrievedChunk, RoleFamily
from resume_screener.ui.demo import scripted_llms


def test_accuracy_fpr_and_confusion():
    pairs = [
        ("strong_match", "strong_match"),
        ("not_relevant", "strong_match"),
        ("not_relevant", "not_relevant"),
        ("possible_fit", None),
    ]
    assert accuracy(pairs) == 0.5
    assert false_positive_rate(pairs) == 0.5
    matrix = confusion_matrix(pairs)
    labels = matrix["labels"]
    strong = labels.index("strong_match")
    not_rel = labels.index("not_relevant")
    assert matrix["matrix"][not_rel][strong] == 1
    assert matrix["matrix"][strong][strong] == 1


def test_percentile_and_audit():
    assert percentile([10, 20, 30, 40], 50) == 25
    assert percentile([1.0], 95) == 1.0
    assert audit_completeness([True, True, False]) == 2 / 3


def test_scripted_case_writes_audit_without_using_hitl_label(tmp_path):
    case = next(item for item in load_eval_cases() if item.id == "eng-sm-01")
    parse_llm, score_llm = scripted_llms("eng-sm-01")
    outcome = score_case(
        case,
        settings=Settings(openai_api_key=""),
        sqlite_path=tmp_path / "tracking.db",
        checkpoint_path=tmp_path / "checkpoints.db",
        overrides_path=tmp_path / "overrides.jsonl",
        parse_llm=parse_llm,
        score_llm=score_llm,
        chunks=[
            RetrievedChunk(
                id="python-backend::skills",
                title="Python backend",
                text="Python REST PostgreSQL Docker",
                role_family=RoleFamily.engineering,
                score=0.9,
            )
        ],
    )
    assert outcome.predicted == MatchLabel.strong_match.value
    assert outcome.expected == MatchLabel.strong_match.value
    assert outcome.audited is True
    assert outcome.error is None
    report = build_report([outcome])
    assert report["audit_completeness"] == 1.0
    assert "accuracy=" in format_stdout(report)
    assert report["recruiter_override_rate"]["computed"] is False
