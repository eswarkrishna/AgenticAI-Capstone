"""Recruiter UI shell. Phase 1: named pages only — no scoring yet."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st

from resume_screener.config import get_settings

st.set_page_config(
    page_title="Resume Screening Agent",
    page_icon="📋",
    layout="wide",
)


def page_screen() -> None:
    st.header("Screen")
    st.caption("Screen candidate — upload a resume PDF and job description.")
    st.file_uploader("Resume PDF", type=["pdf"], key="screen_resume")
    st.text_area("Job description", height=180, key="screen_jd")
    st.button("Run screening", disabled=True, help="Wiring arrives in Phase 6.")
    settings = get_settings()
    st.caption(
        f"Confidence threshold {settings.confidence_threshold} · "
        f"parse model {settings.parse_model} · score model {settings.score_model}"
    )


def page_review() -> None:
    st.header("Review")
    st.caption("Review queue — borderline and low-confidence scorecards land here.")
    st.info("No pending reviews. Review Queue wiring arrives in Phase 6.")


def page_log() -> None:
    st.header("Log")
    st.caption("Tracking log — every run writes an audit row.")
    st.info("No tracking records yet. Log wiring arrives in Phase 6.")


screen = st.Page(page_screen, title="Screen", icon=":material/person_search:")
review = st.Page(page_review, title="Review", icon=":material/rate_review:")
log = st.Page(page_log, title="Log", icon=":material/list_alt:")

st.navigation([screen, review, log]).run()
