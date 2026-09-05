# Resume Screening Agent — Test Plan

Source of truth: [resume_screening_agent_2d4a88b8.plan.md](resume_screening_agent_2d4a88b8.plan.md). Implementation tasks: [TASKS.md](TASKS.md). Later phases must not start until the prior phase gate passes.

## Target metrics (Phase 7)

| Metric | Gate | How measured |
|---|---|---|
| Label accuracy | >= 85% | `eval/run_eval.py` on 30 labelled pairs (`predicted_label` = `scorecard.overall_label`, no HITL) |
| False positive rate | <= 5% | Ground-truth `not_relevant` predicted `strong_match` |
| Time-to-scorecard p95 | < 90s | Same harness, per-case latency |
| Audit completeness | 100% | Every run has a `tracking` row |
| DeepEval faithfulness | Tracked, no hard gate in v1 | Rationale vs resume+JD; skip if DeepEval/API unavailable |
| Recruiter override rate | Manual in v1 | Review Queue, not auto-computed |

## Out of scope

No Greenhouse/Lever/Workday tests, no real candidate PII, no production auth, no interview-replacement claims.

---

## Phase 1 — Foundation

**Files:** `tests/test_schemas.py`, `tests/test_pdf.py`

| ID | Type | Check | Pass |
|---|---|---|---|
| P1-01 | Unit | `pytest` schema validation rejects PII-shaped extra fields (`extra=forbid`) | [x] |
| P1-02 | Unit | Score outside 1–10 is rejected | [x] |
| P1-03 | Unit | PDF extractor returns non-empty text from a fixture PDF | [x] |
| P1-04 | Manual | `streamlit run app/streamlit_app.py` shows Screen / Review / Log pages | [x] |
| P1-05 | Doc | `.env.example` documents every config variable | [x] |

**Command:** `pytest tests/test_schemas.py tests/test_pdf.py`

---

## Phase 2 — Dataset and competency KB

| ID | Type | Check | Pass |
|---|---|---|---|
| P2-01 | Data | 30 labelled pairs exist; `labels.json` validates as `EvalCase` | [x] |
| P2-02 | Data | Balance: 10 engineering / 10 product_design / 10 operations | [x] |
| P2-03 | Data | Balance: 10 strong_match / 10 possible_fit / 10 not_relevant (cross-cut) | [x] |
| P2-04 | Data | At least 6 hard cases: synonym skills, keyword-stuffed weak resume, career-switcher, overqualified mismatch, missing degree + strong experience, uncommon JD tools | [x] |
| P2-05 | Smoke | `python -m resume_screener.rag.ingest` creates `data/chroma/` | [x] |
| P2-06 | Smoke | Query “backend software engineer” returns >= 1 chunk | [x] |
| P2-07 | Doc | README snippet for regenerating PDFs and the index | [x] |

---

## Phase 3 — Parsing Agent

**Tests may use a mocked LLM or a recorded fixture.**

| ID | Type | Check | Pass |
|---|---|---|---|
| P3-01 | Integration | `parse_documents` on 3 fixture pairs (one per `role_family`) returns valid `CandidateProfile` + `RoleProfile` | [x] |
| P3-02 | Unit | `CandidateProfile` JSON has no PII keys (name, email, phone, gender, age, nationality, photo, address) | [x] |
| P3-03 | Unit | Failed schema then successful retry is covered | [x] |
| P3-04 | Unit | Injection string inside resume delimiters does not appear in profile fields as instructions | [x] |

---

## Phase 4 — Scoring Agent and RAG

Phase 4 proves wiring. Label accuracy is **not** gated here; that is Phase 7.

| ID | Type | Check | Pass |
|---|---|---|---|
| P4-01 | Unit | Retriever returns same-`role_family` chunks for a known query | [x] |
| P4-02 | Integration | `score_candidate` returns a valid `Scorecard` for one Strong, one Possible, one Not Relevant fixture | [x] |
| P4-03 | Unit | `Scorecard` validation fails if evidence is empty when a dimension score >= 8 | [x] |

---

## Phase 5 — LangGraph, HITL, and audit

| ID | Type | Check | Pass |
|---|---|---|---|
| P5-01 | Integration | High-confidence `strong_match` or `not_relevant` writes one tracking row and leaves no pending interrupt | [ ] |
| P5-02 | Integration | `possible_fit` or low confidence (`confidence < 0.7`) leaves an interrupt | [ ] |
| P5-03 | Integration | `resume_review` sets `overridden` correctly and writes `final_label` | [ ] |
| P5-04 | Integration | Failed parse/score sets `error` and still writes an audit (or error) row — no silent drops | [ ] |

**APIs under test:** `start_screening`, `resume_review`

---

## Phase 6 — Streamlit UI

| ID | Type | Check | Pass |
|---|---|---|---|
| P6-01 | Manual | Upload fixture PDF + JD → scorecard on Screen in one session | [ ] |
| P6-02 | Manual | Screen shows dimension scores, label, confidence, rationale, benchmark titles, recommended action — never candidate name | [ ] |
| P6-03 | Manual | Possible Fit appears in Review Queue; submit override; Tracking Log shows `overridden=true` and new final label | [ ] |
| P6-04 | Manual | Refresh does not lose in-flight review (Sqlite checkpointer) | [ ] |
| P6-05 | Manual | Tracking Log filters (label, role_family, overridden) and CSV export work; no demographic fields | [ ] |

---

## Phase 7 — Eval harness and demo

**Harness:** `python eval/run_eval.py` over `data/eval/labels.json`

**Outputs:** `eval/results/report.json` and a markdown summary (accuracy, confusion matrix, FPR, latency p50/p95, DeepEval faithfulness).

| ID | Type | Check | Pass |
|---|---|---|---|
| P7-01 | Eval | Harness completes on all 30 pairs and prints accuracy, FPR, p50/p95, audit completeness | [ ] |
| P7-02 | Eval | Accuracy >= 85% and FPR <= 5% (tune prompt/threshold in this phase if missed) | [ ] |
| P7-03 | Eval | Time-to-scorecard p95 < 90s | [ ] |
| P7-04 | Smoke | `docker compose up` serves Streamlit on 8501 | [ ] |
| P7-05 | Doc | README is enough for a third party to run the demo with only an OpenAI key | [ ] |

---

## Suggested test layout

```
tests/
  test_schemas.py          # P1-01, P1-02, P4-03
  test_pdf.py              # P1-03
  test_eval_cases.py       # P2-01–P2-04
  test_ingest.py           # P2-05, P2-06
  test_parsing_agent.py    # P3-01–P3-04
  test_retriever.py        # P4-01
  test_scoring_agent.py    # P4-02
  test_graph.py            # P5-01–P5-04
eval/
  run_eval.py              # P7-01–P7-03
  results/
```

OpenAI is required from Phase 3 onward. Use mocks/fixtures for unit tests; live calls belong in Phase 7 eval and a small set of Phase 3/4 fixture runs.
