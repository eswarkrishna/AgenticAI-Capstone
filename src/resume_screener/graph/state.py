"""LangGraph state for one screening thread."""

from __future__ import annotations

from typing import Any, TypedDict


class ScreeningState(TypedDict, total=False):
    resume_path: str
    resume_text: str
    jd_text: str
    resume_filename: str
    jd_title: str
    candidate_profile: dict[str, Any] | None
    role_profile: dict[str, Any] | None
    retrieved_chunks: list[dict[str, Any]]
    scorecard: dict[str, Any] | None
    needs_human_review: bool
    recruiter_feedback: dict[str, Any] | None
    tracking_id: str
    thread_id: str
    error: str | None
    sqlite_path: str
    overrides_path: str
