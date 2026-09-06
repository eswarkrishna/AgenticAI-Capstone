"""LangGraph screening workflow: ingest → parse → retrieve → score → route → persist/HITL."""

from __future__ import annotations

import sqlite3
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from resume_screener.agents.parsing_agent import parse_documents
from resume_screener.agents.scoring_agent import retrieval_query, score_candidate
from resume_screener.config import Settings
from resume_screener.graph.state import ScreeningState
from resume_screener.parsing.pdf import extract_resume_text
from resume_screener.paths import CHECKPOINT_PATH, OVERRIDES_PATH
from resume_screener.persistence.tracking import (
    append_override,
    finalize_disposition,
    get_run,
    insert_run,
)
from resume_screener.rag.retriever import retrieve_competency_benchmarks
from resume_screener.schemas import (
    CandidateProfile,
    MatchLabel,
    RecruiterFeedback,
    RetrievedChunk,
    RoleProfile,
    Scorecard,
    ScreeningResult,
    TrackingRecord,
)

AUTO_PERSIST_LABELS_SET = frozenset({MatchLabel.strong_match, MatchLabel.not_relevant})


@dataclass
class GraphDeps:
    parse_llm: Any | None = None
    score_llm: Any | None = None
    chunks: list[RetrievedChunk] | None = None
    settings: Settings | None = None


_DEPS: ContextVar[GraphDeps | None] = ContextVar("resume_screener_graph_deps", default=None)


def _deps() -> GraphDeps:
    return _DEPS.get() or GraphDeps()


def _settings() -> Settings:
    return _deps().settings or Settings()


def should_interrupt(scorecard: Scorecard, threshold: float | None = None) -> bool:
    """HITL unless high-confidence Strong Match or Not Relevant."""
    cutoff = 0.7 if threshold is None else threshold
    auto = (
        scorecard.overall_label in AUTO_PERSIST_LABELS_SET
        and scorecard.confidence >= cutoff
    )
    return not auto


def _jd_title_from_text(jd_text: str) -> str:
    for line in jd_text.splitlines():
        title = line.strip().lstrip("#").strip()
        if title:
            return title[:200]
    return "untitled"


def _chunks_from_state(state: ScreeningState) -> list[RetrievedChunk]:
    out: list[RetrievedChunk] = []
    for raw in state.get("retrieved_chunks") or []:
        out.append(RetrievedChunk.model_validate(raw))
    return out


def _optional_profile(raw: dict[str, Any] | None, cls: type):
    if not raw:
        return None
    return cls.model_validate(raw)


def _optional_scorecard(raw: dict[str, Any] | None) -> Scorecard | None:
    if not raw:
        return None
    return Scorecard.model_validate(raw)


def _tracking_record(
    state: ScreeningState,
    *,
    pending: bool,
    error: str | None = None,
) -> TrackingRecord:
    scorecard = _optional_scorecard(state.get("scorecard"))
    predicted = scorecard.overall_label if scorecard else None
    err = error if error is not None else state.get("error")
    notes = f"ERROR: {err}" if err else ""
    final = None if pending or err else predicted
    return TrackingRecord(
        id=state["tracking_id"],
        created_at=datetime.now(timezone.utc),
        resume_filename=state.get("resume_filename")
        or Path(state.get("resume_path") or "unknown").name,
        jd_title=state.get("jd_title") or "untitled",
        candidate_profile_json=state.get("candidate_profile") or {},
        role_profile_json=state.get("role_profile") or {},
        retrieved_chunk_ids=[chunk.id for chunk in _chunks_from_state(state)],
        scorecard_json=state.get("scorecard") or {},
        predicted_label=predicted,
        final_label=final,
        confidence=scorecard.confidence if scorecard else 0.0,
        needs_human_review=pending,
        overridden=False,
        recruiter_notes=notes,
        thread_id=state["thread_id"],
        error=err,
    )


def _sqlite_path(state: ScreeningState) -> Path:
    return Path(state["sqlite_path"])


def ingest_node(state: ScreeningState) -> dict[str, Any]:
    try:
        path = Path(state["resume_path"])
        text = extract_resume_text(path)
        return {
            "resume_text": text,
            "resume_filename": path.name,
            "jd_title": state.get("jd_title") or _jd_title_from_text(state.get("jd_text") or ""),
        }
    except Exception as exc:  # noqa: BLE001 — audit, do not drop the run
        path = Path(state.get("resume_path") or "unknown")
        return {
            "error": f"ingest failed: {exc}",
            "resume_filename": path.name,
            "jd_title": state.get("jd_title") or _jd_title_from_text(state.get("jd_text") or ""),
        }


def parse_node(state: ScreeningState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    try:
        parsed = parse_documents(
            state["resume_text"],
            state["jd_text"],
            llm=_deps().parse_llm,
            settings=_settings(),
        )
        return {
            "candidate_profile": parsed.candidate.model_dump(mode="json"),
            "role_profile": parsed.role.model_dump(mode="json"),
            "jd_title": parsed.role.title,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"parse failed: {exc}"}


def retrieve_node(state: ScreeningState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    try:
        deps = _deps()
        if deps.chunks is not None:
            chunks = deps.chunks
        else:
            role = RoleProfile.model_validate(state["role_profile"])
            settings = _settings()
            chunks = retrieve_competency_benchmarks(
                role.role_family,
                retrieval_query(role),
                k=settings.top_k,
                settings=settings,
            )
        return {"retrieved_chunks": [chunk.model_dump(mode="json") for chunk in chunks]}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"retrieve failed: {exc}"}


def score_node(state: ScreeningState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    try:
        candidate = CandidateProfile.model_validate(state["candidate_profile"])
        role = RoleProfile.model_validate(state["role_profile"])
        chunks = _chunks_from_state(state)
        card, used = score_candidate(
            candidate,
            role,
            state["resume_text"],
            llm=_deps().score_llm,
            chunks=chunks,
            settings=_settings(),
        )
        return {
            "scorecard": card.model_dump(mode="json"),
            "retrieved_chunks": [chunk.model_dump(mode="json") for chunk in used],
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"score failed: {exc}"}


def validate_node(state: ScreeningState) -> dict[str, Any]:
    if state.get("error"):
        return {"needs_human_review": False}
    try:
        card = Scorecard.model_validate(state.get("scorecard"))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"validate failed: {exc}", "needs_human_review": False}
    threshold = _settings().confidence_threshold
    return {"needs_human_review": should_interrupt(card, threshold)}


def route_after_validate(
    state: ScreeningState,
) -> Literal["persist_auto", "persist_pending", "persist_error"]:
    if state.get("error"):
        return "persist_error"
    if state.get("needs_human_review"):
        return "persist_pending"
    return "persist_auto"


def persist_auto_node(state: ScreeningState) -> dict[str, Any]:
    insert_run(_tracking_record(state, pending=False), sqlite_path=_sqlite_path(state))
    return {"needs_human_review": False}


def persist_pending_node(state: ScreeningState) -> dict[str, Any]:
    insert_run(_tracking_record(state, pending=True), sqlite_path=_sqlite_path(state))
    return {"needs_human_review": True}


def persist_error_node(state: ScreeningState) -> dict[str, Any]:
    insert_run(
        _tracking_record(state, pending=False, error=state.get("error") or "unknown error"),
        sqlite_path=_sqlite_path(state),
    )
    return {"needs_human_review": False}


def human_review_node(state: ScreeningState) -> dict[str, Any]:
    # Side effects live in persist_pending (previous node). This node restarts
    # from the top on resume, so keep it limited to interrupt() + feedback.
    card = state.get("scorecard") or {}
    skills = card.get("skills") or {}
    experience = card.get("experience") or {}
    education = card.get("education") or {}
    payload = {
        "tracking_id": state.get("tracking_id"),
        "thread_id": state.get("thread_id"),
        "resume_filename": state.get("resume_filename") or "",
        "jd_title": state.get("jd_title") or "",
        "predicted_label": card.get("overall_label"),
        "confidence": card.get("confidence"),
        "rationale": card.get("rationale"),
        "recommended_action": card.get("recommended_action"),
        "recruiter_questions": card.get("recruiter_questions") or [],
        "skills_score": skills.get("score"),
        "experience_score": experience.get("score"),
        "education_score": education.get("score"),
    }
    raw = interrupt(payload)
    feedback = RecruiterFeedback.model_validate(raw)
    return {"recruiter_feedback": feedback.model_dump(mode="json")}


def persist_final_node(state: ScreeningState) -> dict[str, Any]:
    feedback = RecruiterFeedback.model_validate(state.get("recruiter_feedback") or {})
    record = finalize_disposition(
        state["tracking_id"],
        feedback.final_label,
        notes=feedback.notes,
        sqlite_path=_sqlite_path(state),
    )
    append_override(
        record,
        notes=feedback.notes,
        overrides_path=Path(state["overrides_path"]),
    )
    return {"needs_human_review": False}


def _build_graph() -> StateGraph:
    builder = StateGraph(ScreeningState)
    builder.add_node("ingest", ingest_node)
    builder.add_node("parse", parse_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("score", score_node)
    builder.add_node("validate", validate_node)
    builder.add_node("persist_auto", persist_auto_node)
    builder.add_node("persist_pending", persist_pending_node)
    builder.add_node("persist_error", persist_error_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("persist_final", persist_final_node)

    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "parse")
    builder.add_edge("parse", "retrieve")
    builder.add_edge("retrieve", "score")
    builder.add_edge("score", "validate")
    builder.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "persist_auto": "persist_auto",
            "persist_pending": "persist_pending",
            "persist_error": "persist_error",
        },
    )
    builder.add_edge("persist_auto", END)
    builder.add_edge("persist_error", END)
    builder.add_edge("persist_pending", "human_review")
    builder.add_edge("human_review", "persist_final")
    builder.add_edge("persist_final", END)
    return builder


@lru_cache(maxsize=16)
def compile_graph(checkpoint_path: str):
    path = Path(checkpoint_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return _build_graph().compile(checkpointer=saver)


def thread_has_pending_interrupt(
    thread_id: str,
    checkpoint_path: Path | str | None = None,
) -> bool:
    graph = compile_graph(str(Path(checkpoint_path or CHECKPOINT_PATH)))
    snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
    return bool(snapshot.next)


def _interrupt_payload(result: dict[str, Any], graph, config: dict[str, Any]) -> Any | None:
    items = result.get("__interrupt__") or []
    if items:
        first = items[0]
        return getattr(first, "value", first)
    snapshot = graph.get_state(config)
    for task in snapshot.tasks or ():
        for item in getattr(task, "interrupts", ()) or ():
            return getattr(item, "value", item)
    return None


def _result_from_graph(
    graph,
    config: dict[str, Any],
    invoke_result: dict[str, Any],
    sqlite_path: Path,
) -> ScreeningResult:
    snapshot = graph.get_state(config)
    values: dict[str, Any] = dict(snapshot.values or {})
    for key, value in invoke_result.items():
        if key != "__interrupt__":
            values[key] = value
    payload = _interrupt_payload(invoke_result, graph, config)
    interrupted = payload is not None or bool(snapshot.next)
    tracking_id = values.get("tracking_id") or ""
    tracking = get_run(tracking_id, sqlite_path=sqlite_path) if tracking_id else None
    feedback_raw = values.get("recruiter_feedback")
    return ScreeningResult(
        thread_id=values.get("thread_id") or config["configurable"]["thread_id"],
        tracking_id=tracking_id,
        scorecard=_optional_scorecard(values.get("scorecard")),
        candidate=_optional_profile(values.get("candidate_profile"), CandidateProfile),
        role=_optional_profile(values.get("role_profile"), RoleProfile),
        retrieved_chunks=_chunks_from_state(values),  # type: ignore[arg-type]
        needs_human_review=bool(values.get("needs_human_review")) or interrupted,
        interrupted=interrupted,
        interrupt_payload=payload if isinstance(payload, dict) else None,
        tracking=tracking,
        recruiter_feedback=(
            RecruiterFeedback.model_validate(feedback_raw) if feedback_raw else None
        ),
        error=values.get("error"),
    )


def start_screening(
    resume_path: Path,
    jd_text: str,
    thread_id: str,
    *,
    parse_llm: Any | None = None,
    score_llm: Any | None = None,
    chunks: list[RetrievedChunk] | None = None,
    sqlite_path: Path | None = None,
    checkpoint_path: Path | None = None,
    overrides_path: Path | None = None,
    settings: Settings | None = None,
    tracking_id: str | None = None,
) -> ScreeningResult:
    """Run ingest → parse → retrieve → score → persist or HITL interrupt."""
    settings = settings or Settings()
    sqlite = Path(sqlite_path or settings.sqlite_path)
    checkpoints = Path(checkpoint_path or CHECKPOINT_PATH)
    overrides = Path(overrides_path or OVERRIDES_PATH)
    sqlite.parent.mkdir(parents=True, exist_ok=True)
    overrides.parent.mkdir(parents=True, exist_ok=True)

    graph = compile_graph(str(checkpoints))
    config = {"configurable": {"thread_id": thread_id}}
    initial: ScreeningState = {
        "resume_path": str(Path(resume_path)),
        "jd_text": jd_text,
        "thread_id": thread_id,
        "tracking_id": tracking_id or str(uuid.uuid4()),
        "sqlite_path": str(sqlite),
        "overrides_path": str(overrides),
        "error": None,
        "retrieved_chunks": [],
        "needs_human_review": False,
    }
    token = _DEPS.set(
        GraphDeps(
            parse_llm=parse_llm,
            score_llm=score_llm,
            chunks=chunks,
            settings=settings,
        )
    )
    try:
        invoked = graph.invoke(initial, config)
    finally:
        _DEPS.reset(token)
    return _result_from_graph(graph, config, invoked, sqlite)


def resume_review(
    thread_id: str,
    final_label: MatchLabel,
    notes: str = "",
    *,
    checkpoint_path: Path | None = None,
    sqlite_path: Path | None = None,
) -> ScreeningResult:
    """Resume a paused HITL thread with the recruiter's final label."""
    checkpoints = Path(checkpoint_path or CHECKPOINT_PATH)
    graph = compile_graph(str(checkpoints))
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if not snapshot.next:
        raise RuntimeError(f"thread {thread_id} has no pending interrupt")
    sqlite = Path(sqlite_path or snapshot.values.get("sqlite_path") or Settings().sqlite_path)
    feedback = RecruiterFeedback(final_label=final_label, notes=notes)
    invoked = graph.invoke(Command(resume=feedback.model_dump(mode="json")), config)
    return _result_from_graph(graph, config, invoked, sqlite)
