"""Recruiter UI: Screen, Review, and Tracking Log on the Phase 5 graph API."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st

from resume_screener.config import get_settings
from resume_screener.persistence.tracking import list_all, list_pending_review
from resume_screener.schemas import MatchLabel, RoleFamily
from resume_screener.ui.demo import DEMO_CASE_IDS, DEMO_LABELS, demo_paths
from resume_screener.ui.display import (
    ScorecardView,
    filter_tracking,
    format_label,
    log_csv,
    log_table_rows,
    resolve_review_action,
    scorecard_view,
)
from resume_screener.ui.runtime import (
    NO_KEY_MESSAGE,
    run_screening,
    submit_review,
    write_upload,
)

st.set_page_config(
    page_title="Resume Screening Agent",
    page_icon="📋",
    layout="wide",
)

PAGES: dict[str, st.Page] = {}


def _settings_caption() -> None:
    settings = get_settings()
    key_note = (
        "OpenAI key set — live parse/score"
        if settings.openai_api_key
        else "No OpenAI key — demo fixtures use recorded parse/score scripts"
    )
    st.caption(
        f"{key_note} · threshold {settings.confidence_threshold} · "
        f"parse {settings.parse_model} · score {settings.score_model}"
    )


def _render_scorecard(view: ScorecardView) -> None:
    if view.error:
        st.error(view.error)
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Skills", f"{view.skills_score}/10")
    c2.metric("Experience", f"{view.experience_score}/10")
    c3.metric("Education", f"{view.education_score}/10")
    c4.metric("Confidence", f"{view.confidence:.0%}")
    st.markdown(f"**Overall label:** {view.label}")
    st.markdown(f"**Recommended action:** {view.recommended_action}")
    if view.jd_title:
        st.caption(f"Job: {view.jd_title}")
    st.subheader("Rationale")
    st.write(view.rationale)
    ev1, ev2, ev3 = st.columns(3)
    with ev1:
        st.markdown("**Skills evidence**")
        for item in view.skills_evidence or ["—"]:
            st.write(f"- {item}")
    with ev2:
        st.markdown("**Experience evidence**")
        for item in view.experience_evidence or ["—"]:
            st.write(f"- {item}")
    with ev3:
        st.markdown("**Education evidence**")
        for item in view.education_evidence or ["—"]:
            st.write(f"- {item}")
    st.subheader("Competency benchmarks")
    if view.benchmark_titles:
        for title in view.benchmark_titles:
            st.write(f"- {title}")
    else:
        st.caption("No benchmark chunks retrieved.")
    if view.recruiter_questions:
        st.subheader("Questions for the recruiter")
        for question in view.recruiter_questions:
            st.write(f"- {question}")
    if view.hitl:
        st.warning(
            "Human review required — Possible Fit or low confidence. "
            "The run is checkpointed; refreshing the app will not drop it."
        )
        if st.button("Go to Review Queue", key="goto_review"):
            st.switch_page(PAGES["review"])


def page_screen() -> None:
    st.header("Screen")
    st.caption(
        "Upload a resume PDF and job description. The scorecard never shows a candidate name."
    )
    _settings_caption()

    st.markdown("**Demo fixtures**")
    demo_cols = st.columns(len(DEMO_CASE_IDS))
    for column, case_id in zip(demo_cols, DEMO_CASE_IDS):
        with column:
            if st.button(DEMO_LABELS[case_id], key=f"demo_{case_id}", use_container_width=True):
                resume_path, jd_text = demo_paths(case_id)
                with st.spinner("Running screening…"):
                    try:
                        st.session_state["last_result"] = run_screening(
                            resume_path, jd_text, resume_filename=resume_path.name
                        )
                        st.session_state["last_error"] = None
                    except Exception as exc:  # noqa: BLE001
                        st.session_state["last_error"] = str(exc)
                        st.session_state["last_result"] = None

    st.divider()
    uploaded = st.file_uploader("Resume PDF", type=["pdf"], key="screen_resume")
    jd_file = st.file_uploader("Job description file (optional)", type=["md", "txt"], key="screen_jd_file")
    jd_text = st.text_area("Job description", height=180, key="screen_jd")
    if jd_file is not None:
        jd_text = jd_file.getvalue().decode("utf-8")

    run_clicked = st.button("Run screening", type="primary")
    if run_clicked:
        if uploaded is None or not (jd_text or "").strip():
            st.warning("Upload a resume PDF and provide a job description.")
        else:
            tmp = write_upload(uploaded.getvalue(), uploaded.name)
            try:
                with st.spinner("Running screening…"):
                    st.session_state["last_result"] = run_screening(
                        tmp, jd_text, resume_filename=uploaded.name
                    )
                    st.session_state["last_error"] = None
            except Exception as exc:  # noqa: BLE001
                st.session_state["last_error"] = str(exc)
                st.session_state["last_result"] = None
            finally:
                tmp.unlink(missing_ok=True)

    if st.session_state.get("last_error"):
        st.error(st.session_state["last_error"])
        if "OPENAI_API_KEY" in st.session_state["last_error"]:
            st.info(NO_KEY_MESSAGE)

    result = st.session_state.get("last_result")
    if result is not None:
        st.divider()
        _render_scorecard(scorecard_view(result))


def page_review() -> None:
    st.header("Review")
    st.caption(
        "Borderline and low-confidence scorecards wait here. Refresh-safe via SQLite checkpoints."
    )
    pending = list_pending_review()
    if not pending:
        st.info("No pending reviews.")
        return

    for record in pending:
        title = f"{record.jd_title or 'Untitled'} · {format_label(record.predicted_label)}"
        with st.expander(title, expanded=True):
            card = record.scorecard_json or {}
            st.write(f"**Predicted:** {format_label(record.predicted_label)}")
            st.write(f"**Confidence:** {record.confidence:.0%}")
            st.write(f"**Resume file:** {record.resume_filename}")
            rationale = card.get("rationale") or ""
            if rationale:
                st.write(rationale)
            questions = card.get("recruiter_questions") or []
            if questions:
                st.markdown("**Agent questions**")
                for question in questions:
                    st.write(f"- {question}")
            if record.predicted_label is None:
                st.warning("This row has no predicted label; skip or inspect the tracking log.")
                continue
            predicted = record.predicted_label
            with st.form(f"review_{record.id}"):
                action = st.radio(
                    "Decision",
                    options=["keep", "upgrade", "downgrade"],
                    format_func=lambda value, current=predicted: (
                        f"{value.title()} → {format_label(resolve_review_action(current, value))}"
                    ),
                    horizontal=True,
                    key=f"action_{record.id}",
                )
                notes = st.text_area("Notes", key=f"notes_{record.id}")
                submitted = st.form_submit_button("Submit review", type="primary")
            if submitted:
                final_label = resolve_review_action(predicted, action)
                try:
                    result = submit_review(record.thread_id, final_label, notes)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    tracking = result.tracking
                    if tracking and tracking.overridden:
                        st.success(
                            f"Override saved: {format_label(tracking.predicted_label)} → "
                            f"{format_label(tracking.final_label)}"
                        )
                    else:
                        st.success(f"Kept {format_label(final_label)}")
                    st.rerun()


def page_log() -> None:
    st.header("Log")
    st.caption("Every screening run writes an audit row. Filename is allowed; no demographic fields.")
    rows = list_all()

    f1, f2, f3 = st.columns(3)
    with f1:
        label_choice = st.selectbox(
            "Label",
            options=["all", *[item.value for item in MatchLabel]],
            format_func=lambda value: "All labels" if value == "all" else format_label(value),
        )
    with f2:
        family_choice = st.selectbox(
            "Role family",
            options=["all", *[item.value for item in RoleFamily]],
            format_func=lambda value: "All families" if value == "all" else value.replace("_", " "),
        )
    with f3:
        overridden_choice = st.selectbox(
            "Overridden",
            options=["all", "yes", "no"],
            format_func=lambda value: {"all": "All", "yes": "Overridden", "no": "Not overridden"}[value],
        )

    label = None if label_choice == "all" else MatchLabel(label_choice)
    family = None if family_choice == "all" else RoleFamily(family_choice)
    overridden = None if overridden_choice == "all" else overridden_choice == "yes"
    filtered = filter_tracking(
        rows, label=label, role_family=family, overridden=overridden
    )
    table = log_table_rows(filtered)
    st.caption(f"{len(filtered)} of {len(rows)} rows")
    if table:
        st.dataframe(table, hide_index=True, use_container_width=True)
    else:
        st.info("No tracking records match these filters.")
    st.download_button(
        "Download CSV",
        data=log_csv(filtered),
        file_name="tracking_log.csv",
        mime="text/csv",
        disabled=not filtered,
    )


PAGES["screen"] = st.Page(page_screen, title="Screen", icon=":material/person_search:")
PAGES["review"] = st.Page(page_review, title="Review", icon=":material/rate_review:")
PAGES["log"] = st.Page(page_log, title="Log", icon=":material/list_alt:")

st.navigation([PAGES["screen"], PAGES["review"], PAGES["log"]]).run()
