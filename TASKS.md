# Resume Screening Agent — Task Backlog

Source of truth: [resume_screening_agent_2d4a88b8.plan.md](resume_screening_agent_2d4a88b8.plan.md). Gates: [TEST_PLAN.md](TEST_PLAN.md).

Rules: later phases must not start until the prior phase gate passes. Check a task only when its files exist and its linked TEST_PLAN IDs pass.

**Status on `main`:** Phases 1–5 are done. Phase 6 (Streamlit recruiter UI) lands in this change. Next work after the Phase 6 gate is T7.1.

---

## Phase 1 — Foundation and contracts

Goal: runnable empty app with typed contracts and PDF text extraction. No LLM calls.

| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| T1.1 | Scaffold package: `pyproject.toml` or `PYTHONPATH=src`, `requirements.txt`, `src/resume_screener/__init__.py` | `pyproject.toml`, `requirements.txt`, `src/resume_screener/__init__.py` | — | [x] |
| T1.2 | Pydantic contracts: enums (`MatchLabel`, `RoleFamily`, `RecommendedAction`), `CandidateProfile` (`extra=forbid`, no PII), `RoleProfile`, `DimensionScore`, `Scorecard`, `TrackingRecord`, `EvalCase` | `src/resume_screener/schemas.py` | P1-01, P1-02 | [x] |
| T1.3 | Config + env template: dotenv load; OpenAI required; Anthropic/LangSmith optional; defaults for models, `confidence_threshold=0.7`, Chroma, SQLite, `top_k=5` | `src/resume_screener/config.py`, `.env.example` | P1-05 | [x] |
| T1.4 | PDF extractor `extract_resume_text(path) -> str` via PyMuPDF plus a fixture PDF | `src/resume_screener/parsing/pdf.py`, fixture under `tests/` or `data/` | P1-03 | [x] |
| T1.5 | Streamlit stub with three named pages: Screen / Review / Log | `app/streamlit_app.py` | P1-04 | [x] |
| T1.6 | Phase 1 tests | `tests/test_schemas.py`, `tests/test_pdf.py` | P1-01–P1-03 | [x] |

**Phase gate:** `pytest tests/test_schemas.py tests/test_pdf.py`; Streamlit shows three pages; `.env.example` lists every config field. **Passed.**

---

## Phase 2 — Dataset and competency KB

Goal: 30 labelled pairs and a retrievable competency index. Still no agents.

Depends on: Phase 1 gate.

| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| T2.1 | Eval set index: 30 `EvalCase` objects in `labels.json` (id, role_family, label, jd_path, resume_pdf, notes) | `data/eval/labels.json` | P2-01 | [x] |
| T2.2 | Author 30 resume `.md` + 30 JD `.md` with balance 10/10/10 role_family and 10/10/10 labels (cross-cut) | `data/eval/resumes/*.md`, `data/eval/jds/*.md` | P2-02, P2-03 | [x] |
| T2.3 | Include ≥6 hard cases: synonym skills, keyword-stuffed weak resume, career-switcher, overqualified mismatch, missing degree + strong experience, uncommon JD tools | same as T2.2; call out in `notes` | P2-04 | [x] |
| T2.4 | Render resume markdown to PDF (reportlab/fpdf2) so PyMuPDF is on the real path | `data/eval/resumes/*.pdf`, render script if needed | P2-01 | [x] |
| T2.5 | Competency KB: 30–50 short markdown files covering clusters used by the 30 JDs (heading schema: skills, experience band, education, related titles + `role_family` metadata) | `data/competency_kb/*.md` | — | [x] |
| T2.6 | Chroma ingest: chunk by heading, embed, persist collection `competency_benchmarks` with metadata `{role_family, source, title}` | `src/resume_screener/rag/ingest.py` | P2-05, P2-06 | [x] |
| T2.7 | Phase 2 tests + README snippet for regenerating PDFs and the index | `tests/test_eval_cases.py`, `tests/test_ingest.py`, `README.md` | P2-01–P2-07 | [x] |

**Phase gate:** 30 pairs validate; `python -m resume_screener.rag.ingest` creates `data/chroma/`; query “backend software engineer” returns ≥1 chunk. **Passed.**

---

## Phase 3 — Parsing Agent

Goal: resume + JD in, validated `CandidateProfile` + `RoleProfile` out. Scoring must never see PII.

Depends on: Phase 2 gate. OpenAI key required from here on (mocks OK for unit tests).

| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| T3.1 | `parse_documents(resume_text, jd_text) -> ParseResult` with structured LLM output mapped to Pydantic | `src/resume_screener/agents/parsing_agent.py` | P3-01 | [x] |
| T3.2 | Delimiter-wrap untrusted text (`<<<RESUME>>>` / `<<<END_RESUME>>>`); system prompt ignores instructions inside delimiters | same | P3-04 | [x] |
| T3.3 | Drop/ignore PII keys even if the model emits them; `CandidateProfile` has no name/email/phone/gender/age/nationality/photo/address | same | P3-02 | [x] |
| T3.4 | One automatic retry on `ValidationError` | same | P3-03 | [x] |
| T3.5 | Phase 3 tests (mocked LLM or recorded fixture): 3 fixture pairs (one per role family), PII strip, retry, injection | `tests/test_parsing_agent.py` | P3-01–P3-04 | [x] |

**Phase gate:** three fixture pairs parse; no PII keys; retry and injection tests pass. **Passed.**

---

## Phase 4 — Scoring Agent and RAG

Goal: evidence-backed scorecard from profiles + competency retrieval. No graph yet.

Depends on: Phase 3 gate. Label accuracy is **not** gated here (that is Phase 7).

| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| T4.1 | Retriever `retrieve_competency_benchmarks(role_family, query, k=5)` filtered by `role_family`; expose as a LangChain tool | `src/resume_screener/rag/retriever.py` | P4-01 | [x] |
| T4.2 | `score_candidate(candidate, role, resume_text) -> (Scorecard, list[RetrievedChunk])`: retrieve, then score skills → experience → education with resume evidence | `src/resume_screener/agents/scoring_agent.py` | P4-02 | [x] |
| T4.3 | Enforce label decision rules (Strong / Possible / Not Relevant) and never emit Strong Match when must-haves are absent | same | P4-02 | [x] |
| T4.4 | Thin evidence → lower confidence + `recruiter_questions`; custom validator: evidence required when a dimension score ≥ 8 | `src/resume_screener/schemas.py`, scoring agent | P4-03 | [x] |
| T4.5 | Phase 4 tests: family-filtered retrieval; one Strong / Possible / Not Relevant fixture scorecard | `tests/test_retriever.py`, `tests/test_scoring_agent.py` | P4-01–P4-03 | [x] |

**Phase gate:** retriever returns same-family chunks; three fixture scorecards validate; empty evidence on a high score fails validation. **Passed.**

---

## Phase 5 — LangGraph, HITL, and audit

Goal: end-to-end loop with routing, interrupt, and 100% audit writes.

Depends on: Phase 4 gate.

| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| T5.1 | Graph state: texts, filenames, profiles, chunks, scorecard, HITL flags, tracking/thread ids, error | `src/resume_screener/graph/state.py` | — | [x] |
| T5.2 | StateGraph: ingest → parse → retrieve → score → validate → persist **or** `human_review` (`interrupt()`); `SqliteSaver` at `data/checkpoints.db` | `src/resume_screener/graph/workflow.py` | P5-01, P5-02 | [x] |
| T5.3 | Routing: auto-persist iff label in {`strong_match`, `not_relevant`} AND `confidence >= 0.7`; else interrupt | same | P5-01, P5-02 | [x] |
| T5.4 | SQLite tracking table + `insert_run`, `finalize_disposition`, `list_pending_review`, `list_all`, `export_csv`; append-only `data/overrides.jsonl` | `src/resume_screener/persistence/tracking.py` | P5-01, P5-03 | [x] |
| T5.5 | Public API: `start_screening(resume_path, jd_text, thread_id)`, `resume_review(thread_id, final_label, notes)` via `Command(resume=...)` | graph module or `src/resume_screener/api.py` | P5-01–P5-03 | [x] |
| T5.6 | Failed parse/score sets `error` and still writes an audit/error row — no silent drops | persistence + graph | P5-04 | [x] |
| T5.7 | Phase 5 tests | `tests/test_graph.py` | P5-01–P5-04 | [x] |

**Phase gate:** high-confidence Strong/Not Relevant auto-persists with no pending interrupt; Possible Fit / low confidence interrupts; override logged; failures still audited. **Passed.**

---

## Phase 6 — Streamlit recruiter UI

Goal: demoable recruiter workflow on the graph API. Never display candidate name.

Depends on: Phase 5 gate.

| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| T6.1 | Screen page: upload PDF, paste/upload JD, run `start_screening`, show dimension scores, label, confidence, rationale, benchmark titles, recommended action; HITL banner + link to Review Queue | `app/streamlit_app.py` (or `app/pages/`) | P6-01, P6-02 | [x] |
| T6.2 | Review Queue: list pending interrupts, pre-filled summary + agent questions, upgrade/downgrade/keep + notes, Submit → `resume_review` | same | P6-03 | [x] |
| T6.3 | Tracking Log: table (time, JD title, predicted/final label, confidence, overridden, HITL); filters (label, role_family, overridden); CSV export; filename OK, no demographics | same | P6-05 | [x] |
| T6.4 | Checkpoint survival: refresh does not lose in-flight review | Sqlite checkpointer | P6-04 | [x] |

**Phase gate:** fixture PDF+JD → scorecard in one session; HITL override appears in log; refresh-safe; no names on Screen. **Passed.**

---

## Phase 7 — Evaluation, packaging, docs

Goal: measure proposal metrics and make the demo reproducible.

Depends on: Phase 6 gate.

| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| T7.1 | Eval harness over `labels.json` (parse + score, no HITL); write `eval/results/report.json` + markdown summary (accuracy, confusion matrix, FPR, latency p50/p95, DeepEval faithfulness if available) | `eval/run_eval.py` | P7-01 | [ ] |
| T7.2 | Tune prompt/threshold until accuracy ≥ 85% and FPR ≤ 5%; confirm p95 < 90s | prompts, `confidence_threshold` | P7-02, P7-03 | [ ] |
| T7.3 | Docker: Streamlit on 8501, volume `./data`, optional first-run ingest if Chroma empty | `Dockerfile`, `docker-compose.yml` | P7-04 | [ ] |
| T7.4 | README: setup, `.env`, ingest, `streamlit run`, `python eval/run_eval.py`, 3-fixture demo script, limitations, responsible-AI notes | `README.md` | P7-05 | [ ] |

**Phase gate:** harness completes on all 30 pairs and prints the automatic metrics; `docker compose up` serves the app; a third party can run the demo with only an OpenAI key.

---

## Out of scope (do not file tasks)

Greenhouse/Lever/Workday integration, real candidate PII, production auth, interview replacement, AWS AgentCore/Bedrock.

---

## Suggested execution order

```
T1.1 → T1.2 → T1.3 → T1.4 → T1.5 → T1.6
                         ↓
T2.1 → T2.2 → T2.3 → T2.4 → T2.5 → T2.6 → T2.7
                                          ↓
T3.1 → T3.2 → T3.3 → T3.4 → T3.5
                            ↓
T4.1 → T4.2 → T4.3 → T4.4 → T4.5
                            ↓
T5.1 → T5.2 → T5.3 → T5.4 → T5.5 → T5.6 → T5.7
                                          ↓
T6.1 → T6.2 → T6.3 → T6.4
                    ↓
T7.1 → T7.2 → T7.3 → T7.4
```
