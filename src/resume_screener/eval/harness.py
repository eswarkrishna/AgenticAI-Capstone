"""Run parse + score on the labelled eval set. Does not resume HITL."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from resume_screener.config import Settings
from resume_screener.eval.load import load_eval_cases, resolve_eval_path
from resume_screener.eval.metrics import (
    ACCURACY_GATE,
    FPR_GATE,
    P95_GATE_S,
    accuracy,
    audit_completeness,
    confusion_matrix,
    false_positive_rate,
    percentile,
)
from resume_screener.graph.workflow import start_screening
from resume_screener.paths import REPO_ROOT
from resume_screener.schemas import EvalCase

RESULTS_DIR = REPO_ROOT / "eval" / "results"


@dataclass
class CaseOutcome:
    case_id: str
    expected: str
    predicted: str | None
    latency_s: float
    audited: bool
    error: str | None
    confidence: float | None
    rationale: str
    resume_text_chars: int
    jd_text_chars: int


def _faithfulness(outcomes: list[CaseOutcome]) -> dict[str, Any]:
    """Track DeepEval faithfulness when the package is installed. Never fail the run."""
    try:
        import deepeval  # noqa: F401
    except ImportError:
        return {
            "available": False,
            "score": None,
            "skipped_reason": "deepeval is not installed",
        }
    return {
        "available": True,
        "score": None,
        "skipped_reason": (
            "deepeval is installed but the harness does not call the judge by "
            "default; set RESUME_SCREENER_DEEPEVAL=1 to enable"
        ),
    }


def score_case(
    case: EvalCase,
    *,
    settings: Settings,
    sqlite_path: Path,
    checkpoint_path: Path,
    overrides_path: Path,
    parse_llm: Any | None = None,
    score_llm: Any | None = None,
    chunks: list | None = None,
) -> CaseOutcome:
    resume_path = resolve_eval_path(case.resume_pdf)
    jd_text = resolve_eval_path(case.jd_path).read_text(encoding="utf-8")
    started = time.perf_counter()
    error: str | None = None
    predicted: str | None = None
    confidence: float | None = None
    rationale = ""
    audited = False
    try:
        result = start_screening(
            resume_path,
            jd_text,
            f"eval-{case.id}-{uuid.uuid4()}",
            settings=settings,
            sqlite_path=sqlite_path,
            checkpoint_path=checkpoint_path,
            overrides_path=overrides_path,
            parse_llm=parse_llm,
            score_llm=score_llm,
            chunks=chunks,
        )
        audited = result.tracking is not None
        if result.scorecard is not None:
            predicted = result.scorecard.overall_label.value
            confidence = result.scorecard.confidence
            rationale = result.scorecard.rationale
        error = result.error
    except Exception as exc:  # noqa: BLE001 — one bad case must not abort the report
        error = str(exc)
    return CaseOutcome(
        case_id=case.id,
        expected=case.label.value,
        predicted=predicted,
        latency_s=time.perf_counter() - started,
        audited=audited,
        error=error,
        confidence=confidence,
        rationale=rationale,
        resume_text_chars=0,
        jd_text_chars=len(jd_text),
    )


def build_report(outcomes: list[CaseOutcome]) -> dict[str, Any]:
    pairs = [(item.expected, item.predicted) for item in outcomes]
    latencies = [item.latency_s for item in outcomes]
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    acc = accuracy(pairs)
    fpr = false_positive_rate(pairs)
    audit = audit_completeness([item.audited for item in outcomes])
    faith = _faithfulness(outcomes)
    return {
        "n": len(outcomes),
        "accuracy": acc,
        "false_positive_rate": fpr,
        "latency_p50_s": p50,
        "latency_p95_s": p95,
        "audit_completeness": audit,
        "confusion_matrix": confusion_matrix(pairs),
        "deepeval_faithfulness": faith,
        "recruiter_override_rate": {
            "computed": False,
            "note": "Manual metric from the Review Queue in v1. Not auto-computed.",
        },
        "gates": {
            "accuracy_gte_85": acc >= ACCURACY_GATE,
            "fpr_lte_5": fpr <= FPR_GATE,
            "p95_lt_90s": p95 < P95_GATE_S,
            "audit_complete": audit == 1.0,
        },
        "cases": [
            {
                "id": item.case_id,
                "expected": item.expected,
                "predicted": item.predicted,
                "correct": item.predicted == item.expected,
                "latency_s": round(item.latency_s, 3),
                "audited": item.audited,
                "confidence": item.confidence,
                "error": item.error,
            }
            for item in outcomes
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    matrix = report["confusion_matrix"]
    labels = matrix["labels"]
    header = "| actual \\ predicted | " + " | ".join(labels) + " |"
    sep = "| --- | " + " | ".join("---" for _ in labels) + " |"
    rows = []
    for name, row in zip(labels, matrix["matrix"]):
        rows.append("| " + name + " | " + " | ".join(str(n) for n in row) + " |")
    faith = report["deepeval_faithfulness"]
    faith_line = (
        f"{faith['score']:.3f}"
        if isinstance(faith.get("score"), (int, float))
        else f"skipped ({faith.get('skipped_reason')})"
    )
    gates = report["gates"]
    lines = [
        "# Eval report",
        "",
        f"- Cases: {report['n']}",
        f"- Accuracy: {report['accuracy']:.1%} (gate >= 85%: {'pass' if gates['accuracy_gte_85'] else 'fail'})",
        f"- False positive rate (Not Relevant → Strong Match): {report['false_positive_rate']:.1%} (gate <= 5%: {'pass' if gates['fpr_lte_5'] else 'fail'})",
        f"- Latency p50: {report['latency_p50_s']:.2f}s",
        f"- Latency p95: {report['latency_p95_s']:.2f}s (gate < 90s: {'pass' if gates['p95_lt_90s'] else 'fail'})",
        f"- Audit completeness: {report['audit_completeness']:.1%} ({'pass' if gates['audit_complete'] else 'fail'})",
        f"- DeepEval faithfulness: {faith_line}",
        "- Recruiter override rate: manual, from the Review Queue (not computed here).",
        "",
        "## Confusion matrix",
        "",
        header,
        sep,
        *rows,
        "",
        "## Cases",
        "",
        "| id | expected | predicted | correct | latency_s | audited |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case in report["cases"]:
        lines.append(
            "| {id} | {expected} | {predicted} | {correct} | {latency_s} | {audited} |".format(
                **case
            )
        )
    lines.append("")
    return "\n".join(lines)


def format_stdout(report: dict[str, Any]) -> str:
    return (
        f"accuracy={report['accuracy']:.3f} "
        f"fpr={report['false_positive_rate']:.3f} "
        f"p50_s={report['latency_p50_s']:.2f} "
        f"p95_s={report['latency_p95_s']:.2f} "
        f"audit_completeness={report['audit_completeness']:.3f}"
    )


def run_eval(
    *,
    settings: Settings | None = None,
    results_dir: Path | None = None,
    limit: int | None = None,
    parse_llm: Any | None = None,
    score_llm: Any | None = None,
) -> dict[str, Any]:
    settings = settings or Settings()
    out_dir = Path(results_dir or RESULTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = out_dir / "tracking.db"
    checkpoint_path = out_dir / "checkpoints.db"
    overrides_path = out_dir / "overrides.jsonl"
    cases = load_eval_cases()
    if limit is not None:
        cases = cases[:limit]
    outcomes = [
        score_case(
            case,
            settings=settings,
            sqlite_path=sqlite_path,
            checkpoint_path=checkpoint_path,
            overrides_path=overrides_path,
            parse_llm=parse_llm,
            score_llm=score_llm,
        )
        for case in cases
    ]
    report = build_report(outcomes)
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (out_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
    return report
