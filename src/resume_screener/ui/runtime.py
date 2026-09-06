"""Streamlit adapter around start_screening / resume_review."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from resume_screener.config import Settings
from resume_screener.graph.workflow import resume_review, start_screening
from resume_screener.schemas import MatchLabel, ScreeningResult
from resume_screener.ui.demo import demo_case_id, scripted_llms

NO_KEY_MESSAGE = (
    "OPENAI_API_KEY is required for custom resumes. Without a key you can still "
    "run the three demo fixtures on this page (Strong Match, Possible Fit, Not Relevant)."
)


def run_screening(
    resume_path: Path,
    jd_text: str,
    *,
    resume_filename: str | None = None,
    settings: Settings | None = None,
    thread_id: str | None = None,
    sqlite_path: Path | None = None,
    checkpoint_path: Path | None = None,
    overrides_path: Path | None = None,
) -> ScreeningResult:
    settings = settings or Settings()
    filename = resume_filename or Path(resume_path).name
    kwargs: dict = {}
    case_id = demo_case_id(filename)
    if not settings.openai_api_key:
        if case_id is None:
            raise RuntimeError(NO_KEY_MESSAGE)
        parse_llm, score_llm = scripted_llms(case_id)
        kwargs["parse_llm"] = parse_llm
        kwargs["score_llm"] = score_llm
    return start_screening(
        Path(resume_path),
        jd_text,
        thread_id or str(uuid.uuid4()),
        settings=settings,
        sqlite_path=sqlite_path,
        checkpoint_path=checkpoint_path,
        overrides_path=overrides_path,
        **kwargs,
    )


def write_upload(data: bytes, filename: str) -> Path:
    suffix = Path(filename).suffix or ".pdf"
    handle = tempfile.NamedTemporaryFile(prefix="resume-", suffix=suffix, delete=False)
    handle.write(data)
    handle.close()
    return Path(handle.name)


def submit_review(
    thread_id: str,
    final_label: MatchLabel,
    notes: str = "",
    *,
    checkpoint_path: Path | None = None,
    sqlite_path: Path | None = None,
) -> ScreeningResult:
    return resume_review(
        thread_id,
        final_label,
        notes,
        checkpoint_path=checkpoint_path,
        sqlite_path=sqlite_path,
    )
