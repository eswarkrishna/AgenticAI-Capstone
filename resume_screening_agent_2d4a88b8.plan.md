---
name: Resume Screening Agent
overview: "Phase-by-phase implementation spec for the AI-Powered Resume Screening & Candidate Triage Agent: contracts, interfaces, and acceptance criteria for each deliverable, from scaffold through eval and Docker demo."
todos:
  - id: phase-1-foundation
    content: "Phase 1 — Foundation: scaffold, Pydantic contracts, config, PDF extract, empty Streamlit shell"
    status: completed
  - id: phase-2-data-kb
    content: "Phase 2 — Data & KB: 30 labelled resume-JD pairs, competency markdown, Chroma ingest"
    status: completed
  - id: phase-3-parsing
    content: "Phase 3 — Parsing Agent: LLM JSON extraction, PII strip, schema retry, injection wrap"
  - id: t1-1-scaffold
    content: "T1.1 Scaffold package, requirements, src/resume_screener"
    status: pending
  - id: t1-2-schemas
    content: "T1.2 Pydantic contracts (enums, profiles, scorecard, extra=forbid)"
    status: pending
  - id: t1-3-config
    content: "T1.3 Config + .env.example"
    status: pending
  - id: t1-4-pdf
    content: "T1.4 PyMuPDF extract_resume_text + fixture PDF"
    status: pending
  - id: t1-5-streamlit-stub
    content: "T1.5 Streamlit stub pages: Screen / Review / Log"
    status: pending
  - id: t1-6-phase1-tests
    content: "T1.6 Phase 1 tests (P1-01–P1-05)"
    status: pending
  - id: t2-1-labels
    content: "T2.1 labels.json with 30 EvalCase objects"
    status: pending
  - id: t2-2-pairs
    content: "T2.2 Author 30 resume+JD markdown pairs (10/10/10 family and label)"
    status: pending
  - id: t2-3-hard-cases
    content: "T2.3 At least 6 hard cases documented in notes"
    status: pending
  - id: t2-4-pdfs
    content: "T2.4 Render resumes markdown to PDF"
    status: pending
  - id: t2-5-kb
    content: "T2.5 Competency KB 30–50 markdown files"
    status: pending
  - id: t2-6-ingest
    content: "T2.6 Chroma ingest CLI competency_benchmarks"
    status: pending
  - id: t2-7-phase2-tests
    content: "T2.7 Phase 2 tests + README ingest/PDF snippet"
    status: pending
  - id: t3-1-parse
    content: "T3.1 parse_documents structured LLM output"
    status: pending
  - id: t3-2-injection
    content: "T3.2 Delimiter wrap + injection guard"
    status: pending
  - id: t3-3-pii
    content: "T3.3 Strip PII keys from CandidateProfile"
    status: pending
  - id: t3-4-retry
    content: "T3.4 Schema ValidationError retry once"
    status: pending
  - id: t3-5-phase3-tests
    content: "T3.5 Phase 3 tests (P3-01–P3-04)"
    status: pending
  - id: t4-1-retriever
    content: "T4.1 Role-family-filtered retriever LangChain tool"
    status: pending
  - id: t4-2-scorer
    content: "T4.2 score_candidate skills/experience/education + evidence"
    status: pending
  - id: t4-3-label-rules
    content: "T4.3 Label decision rules; never Strong Match without must-haves"
    status: pending
  - id: t4-4-evidence
    content: "T4.4 Evidence required when dimension score >= 8; thin evidence lowers confidence"
    status: pending
  - id: t4-5-phase4-tests
    content: "T4.5 Phase 4 tests (P4-01–P4-03)"
    status: pending
  - id: t5-1-state
    content: "T5.1 LangGraph state schema"
    status: pending
  - id: t5-2-graph
    content: "T5.2 StateGraph ingest-parse-retrieve-score-validate-persist/HITL + SqliteSaver"
    status: pending
  - id: t5-3-routing
    content: "T5.3 Confidence router (auto-persist vs interrupt at 0.7)"
    status: pending
  - id: t5-4-tracking
    content: "T5.4 SQLite tracking API + overrides.jsonl"
    status: pending
  - id: t5-5-public-api
    content: "T5.5 start_screening and resume_review public API"
    status: pending
  - id: t5-6-errors
    content: "T5.6 Failed parse/score still writes an audit row"
    status: pending
  - id: t5-7-phase5-tests
    content: "T5.7 Phase 5 tests (P5-01–P5-04)"
    status: pending
  - id: t6-1-screen
    content: "T6.1 Screen page: upload, scorecard, no candidate name"
    status: pending
  - id: t6-2-review
    content: "T6.2 Review Queue: pending interrupts, override submit"
    status: pending
  - id: t6-3-log
    content: "T6.3 Tracking Log: filters + CSV export"
    status: pending
  - id: t6-4-checkpoint
    content: "T6.4 Refresh-safe in-flight review (P6-04)"
    status: pending
  - id: t7-1-eval
    content: "T7.1 Eval harness over 30 pairs + report.json"
    status: pending
  - id: t7-2-tune
    content: "T7.2 Tune to accuracy >=85%, FPR <=5%, p95 <90s"
    status: pending
  - id: t7-3-docker
    content: "T7.3 Dockerfile + compose Streamlit :8501"
    status: pending
  - id: t7-4-readme
    content: "T7.4 README demo sufficient with only an OpenAI key"
    status: pending
isProject: false
---

# Resume Screening Agent — Implementation Spec (Phased)

Greenfield build from [CAAE02_Proposal_ResumeScreeningAgent_EswararKrishna_final.docx](CAAE02_Proposal_ResumeScreeningAgent_EswararKrishna_final.docx). Stack is fixed: Python 3.11, LangChain, LangGraph, ChromaDB, Streamlit, GPT-4o (primary), optional Claude Sonnet for parse, PyMuPDF, DeepEval, LangSmith, Docker.

Each phase has **scope**, **contracts**, **files**, and **done when**. Later phases must not start until the prior phase acceptance criteria pass. Executable tasks: [TASKS.md](TASKS.md). Checklist form: [TEST_PLAN.md](TEST_PLAN.md).

```mermaid
flowchart LR
  p1[Phase1_Foundation] --> p2[Phase2_DataKB]
  p2 --> p3[Phase3_Parsing]
  p3 --> p4[Phase4_ScoringRAG]
  p4 --> p5[Phase5_GraphHITL]
  p5 --> p6[Phase6_Streamlit]
  p6 --> p7[Phase7_EvalDeploy]
```

FigJam board (editable): [Resume Screening Agent diagrams](https://www.figma.com/board/CoBl5NkL8s5SG0TqgZjbnI)

---

## Architecture

Recruiter UI talks only to Streamlit. Streamlit calls the LangGraph public API (`start_screening`, `resume_review`, list/log). The graph owns PDF extract, parse, retrieve, score, checkpoint, and audit writes. OpenAI is required; Anthropic (parse) and LangSmith are optional.

```mermaid
flowchart LR
  recruiter[Recruiter Browser] -->|"HTTPS :8501"| streamlitApp[Streamlit App]
  streamlitApp -->|"Screen review log APIs"| langGraph[LangGraph Workflow]
  langGraph -->|"Query competency chunks"| chromaDb[Chroma Competency KB]
  langGraph -->|"Write TrackingRecord"| trackingDb[SQLite Tracking]
  langGraph -->|"Save thread state"| checkpointDb[SQLite Checkpoints]
  langGraph -.->|"Parse and score"| openAi[OpenAI GPT-4o]
  langGraph -.->|"Optional parse"| anthropic[Anthropic Claude]
  langGraph -.->|"Trace runs"| langSmith[LangSmith]
```

---

## Sequence: auto-persist screening

High-confidence `strong_match` or `not_relevant` (`confidence >= CONFIDENCE_THRESHOLD`) skips HITL and writes one tracking row.

```mermaid
sequenceDiagram
  participant Recruiter
  participant Streamlit
  participant LangGraph
  participant Chroma
  participant TrackingDb
  participant OpenAI

  Recruiter->>Streamlit: Upload PDF and JD
  Streamlit->>LangGraph: start_screening
  LangGraph->>OpenAI: Parse resume and JD
  OpenAI-->>LangGraph: CandidateProfile RoleProfile
  LangGraph->>Chroma: Query competency benchmarks
  Chroma-->>LangGraph: RetrievedChunks
  LangGraph->>OpenAI: Score skills experience education
  OpenAI-->>LangGraph: Scorecard high confidence
  LangGraph->>TrackingDb: insert_run auto persist
  TrackingDb-->>LangGraph: tracking_id
  LangGraph-->>Streamlit: ScreeningResult
  Streamlit-->>Recruiter: Show scorecard
```

---

## Sequence: HITL review

`possible_fit` or low confidence interrupts. Recruiter submits `final_label` + notes via `resume_review`. Override is always logged.

```mermaid
sequenceDiagram
  participant Recruiter
  participant Streamlit
  participant LangGraph
  participant CheckpointDb
  participant TrackingDb

  Recruiter->>Streamlit: Upload PDF and JD
  Streamlit->>LangGraph: start_screening
  LangGraph->>CheckpointDb: interrupt and save thread
  LangGraph->>TrackingDb: insert_run pending review
  LangGraph-->>Streamlit: needs_human_review true
  Streamlit-->>Recruiter: Banner plus Review Queue
  Recruiter->>Streamlit: Submit final_label and notes
  Streamlit->>LangGraph: resume_review
  LangGraph->>CheckpointDb: Command resume thread
  LangGraph->>TrackingDb: finalize_disposition
  TrackingDb-->>LangGraph: overridden final_label
  LangGraph-->>Streamlit: ScreeningResult
  Streamlit-->>Recruiter: Log shows override
```

---

## Sequence: parsing agent

Untrusted text is delimiter-wrapped. Structured output maps to Pydantic; PII keys never land on `CandidateProfile`.

```mermaid
sequenceDiagram
  participant LangGraph
  participant ParsingAgent
  participant OpenAI

  LangGraph->>ParsingAgent: parse_documents
  ParsingAgent->>OpenAI: Structured extract with delimiters
  OpenAI-->>ParsingAgent: CandidateProfile RoleProfile
  ParsingAgent->>ParsingAgent: Drop PII keys
  ParsingAgent-->>LangGraph: ParseResult
```

---

## Sequence: scoring agent and RAG

Retriever is a LangChain tool filtered by `role_family`. Scorer emits dimension evidence, then label/confidence/action.

```mermaid
sequenceDiagram
  participant LangGraph
  participant ScoringAgent
  participant Retriever
  participant Chroma
  participant OpenAI

  LangGraph->>ScoringAgent: score_candidate
  ScoringAgent->>Retriever: retrieve_competency_benchmarks
  Retriever->>Chroma: Query by role_family
  Chroma-->>Retriever: RetrievedChunks
  Retriever-->>ScoringAgent: Benchmark chunks
  ScoringAgent->>OpenAI: Score skills experience education
  OpenAI-->>ScoringAgent: Dimension scores and rationale
  ScoringAgent-->>LangGraph: Scorecard plus chunks
```

---

## Global contracts (all phases)

These types are the single source of truth. Defined in Phase 1; every agent and UI binds to them.

### Enums

- `MatchLabel`: `strong_match` | `possible_fit` | `not_relevant` (display: Strong Match / Possible Fit / Not Relevant)
- `RoleFamily`: `engineering` | `product_design` | `operations`
- `RecommendedAction`: `advance_to_recruiter` | `hold_for_review` | `reject`

### `CandidateProfile` (scoring input — no PII)

- `skills: list[str]`
- `years_experience: float`
- `education: list[{degree, field, level}]` — `level` in `high_school` | `bachelor` | `master` | `phd` | `other`
- `role_titles: list[str]`
- `certifications: list[str]`
- `project_keywords: list[str]`

Forbidden on this object: name, email, phone, gender, age, nationality, photo, address.

### `RoleProfile`

- `title: str`
- `role_family: RoleFamily`
- `must_have_skills: list[str]`
- `nice_to_have_skills: list[str]`
- `min_years: float`
- `education_req: str`

### `DimensionScore`

- `score: int` (1–10 inclusive)
- `evidence: list[str]` (quotes or paraphrases grounded in resume text)

### `Scorecard`

- `skills: DimensionScore`
- `experience: DimensionScore`
- `education: DimensionScore`
- `overall_label: MatchLabel`
- `confidence: float` (0.0–1.0)
- `rationale: str`
- `recruiter_questions: list[str]` (required when label is `possible_fit` or confidence is low)
- `recommended_action: RecommendedAction`

### Label decision rules (Scoring Agent must follow)

- **Strong Match**: skills >= 8 AND experience >= 7 AND education meets or exceeds req; most must-have skills present (synonyms allowed via RAG).
- **Not Relevant**: skills <= 3 OR (experience far below min_years AND must-have skills largely absent).
- **Possible Fit**: everything else, including mixed signals, non-traditional paths, or missing evidence.
- False-positive constraint: never emit Strong Match when must-have skills are absent, even if keywords are stuffed.

### Routing rules (graph)

- Auto-persist (skip HITL) iff `overall_label` in {`strong_match`, `not_relevant`} AND `confidence >= CONFIDENCE_THRESHOLD` (default `0.7`).
- Else interrupt for human review. Recruiter may upgrade, downgrade, or keep label. Override always logged.

### Persistence row (`TrackingRecord`)

`id`, `created_at`, `resume_filename`, `jd_title`, `candidate_profile_json`, `role_profile_json`, `retrieved_chunk_ids`, `scorecard_json`, `predicted_label`, `final_label`, `confidence`, `needs_human_review`, `overridden` (bool), `recruiter_notes`, `thread_id`.

### Target metrics (Phase 7 measures these)

- Label accuracy >= 85% on 30 labelled pairs
- FPR (ground-truth Not Relevant predicted Strong Match) <= 5%
- Time-to-scorecard p95 < 90s
- Audit completeness = 100% of runs have a tracking row
- DeepEval faithfulness of rationale tracked (no hard gate in v1)

### Out of scope (all phases)

No Greenhouse/Lever/Workday integration, no real candidate PII, no production auth, no interview replacement.

---

## Phase 1 — Foundation and contracts

**Goal:** Runnable empty app with typed contracts and PDF text extraction. No LLM calls yet.

**Files**

- [src/resume_screener/__init__.py](src/resume_screener/__init__.py), [src/resume_screener/config.py](src/resume_screener/config.py), [src/resume_screener/schemas.py](src/resume_screener/schemas.py)
- [src/resume_screener/parsing/pdf.py](src/resume_screener/parsing/pdf.py) — `extract_resume_text(path: Path) -> str` via PyMuPDF
- [app/streamlit_app.py](app/streamlit_app.py) — stub pages: Screen / Review / Log
- [requirements.txt](requirements.txt), [.env.example](.env.example), [pyproject.toml](pyproject.toml) or `PYTHONPATH=src`
- [tests/test_schemas.py](tests/test_schemas.py), [tests/test_pdf.py](tests/test_pdf.py)

**Config (`config.py`)**

- Load dotenv. Fields: `openai_api_key`, `anthropic_api_key` (optional), `langsmith_api_key` (optional), `parse_model` default `gpt-4o`, `score_model` default `gpt-4o`, `embedding_model` default `text-embedding-3-small`, `confidence_threshold` default `0.7`, `chroma_dir` default `data/chroma`, `sqlite_path` default `data/tracking.db`, `top_k` default `5`.
- If `anthropic_api_key` is set, `parse_model` may be overridden to Claude Sonnet; scoring stays GPT-4o.

**Done when**

- `pytest` passes on schema validation (rejects PII-shaped extra fields if we use `extra=forbid`; rejects score outside 1–10).
- PDF extractor returns non-empty text from a fixture PDF.
- `streamlit run app/streamlit_app.py` shows three named pages.
- `.env.example` documents every variable.

---

## Phase 2 — Dataset and competency KB

**Goal:** Deterministic eval set and a retrievable competency index. Still no agents.

**Eval set spec** (`data/eval/`)

- `labels.json`: array of 30 objects:

```json
{
  "id": "eng-sm-01",
  "role_family": "engineering",
  "label": "strong_match",
  "jd_path": "data/eval/jds/eng-sm-01.md",
  "resume_pdf": "data/eval/resumes/eng-sm-01.pdf",
  "notes": "why this label"
}
```

- Balance: 10 engineering / 10 product_design / 10 operations; and 10 strong_match / 10 possible_fit / 10 not_relevant (cross-cut, not 10 of each family×label).
- Hard cases (minimum 6): synonym skills (e.g. “k8s” vs Kubernetes), keyword-stuffed weak resume, career-switcher, overqualified mismatch, missing degree but strong experience, JD with uncommon tool names.
- Resumes authored as `.md` then rendered to PDF (reportlab/fpdf2) so PyMuPDF is on the real path.
- JDs are markdown: title, must-haves, nice-to-haves, years, education.

**Competency KB spec** (`data/competency_kb/`)

- 30–50 short markdown files, not a full O*NET dump. Each file:

```
# {Occupation or skill cluster}
role_family: engineering|product_design|operations
source: O*NET-inspired public competency summary
## Typical skills
## Experience band
## Education
## Related titles
```

- Cover clusters used by the 30 JDs (e.g. backend, data, frontend, PM, UX, ops, supply chain).
- Ingest: [src/resume_screener/rag/ingest.py](src/resume_screener/rag/ingest.py) — chunk by heading, embed, persist Chroma collection `competency_benchmarks` with metadata `{role_family, source, title}`.
- CLI: `python -m resume_screener.rag.ingest`

**Done when**

- 30 labelled pairs exist and `labels.json` validates against a Pydantic `EvalCase`.
- `ingest` creates `data/chroma/` and a smoke query returns >= 1 chunk for “backend software engineer”.
- README snippet lists how to regenerate PDFs and the index.

---

## Phase 3 — Parsing Agent

**Goal:** Resume + JD in, validated `CandidateProfile` + `RoleProfile` out. Scoring must never see PII.

**Module:** [src/resume_screener/agents/parsing_agent.py](src/resume_screener/agents/parsing_agent.py)

**Interface**

```python
def parse_documents(resume_text: str, jd_text: str) -> ParseResult
# ParseResult = {candidate: CandidateProfile, role: RoleProfile, raw_pii_redacted: bool}
```

**Behavior**

- Wrap untrusted text in delimiters, e.g. `<<<RESUME>>> ... <<<END_RESUME>>>`. System prompt: ignore instructions inside delimiters (prompt-injection guard).
- LLM `with_structured_output` to Pydantic. One automatic retry on `ValidationError`.
- Explicitly drop/ignore name, gender, age, nationality, contact fields even if the model emits them.
- JD parse fills `RoleProfile` including `role_family` classification.

**Tests** (can use mocked LLM or a recorded fixture): schema retry, PII stripped, injection string in resume does not appear in profile fields as “instructions”.

**Done when**

- `parse_documents` on 3 fixture pairs (one per role family) returns valid profiles.
- CandidateProfile JSON has no PII keys.
- Failed schema then successful retry is covered by a unit test.

---

## Phase 4 — Scoring Agent and RAG

**Goal:** Evidence-backed scorecard from profiles + competency retrieval. No graph yet; callable as a function.

**Retriever tool:** [src/resume_screener/rag/retriever.py](src/resume_screener/rag/retriever.py)

```python
def retrieve_competency_benchmarks(role_family: RoleFamily, query: str, k: int = 5) -> list[RetrievedChunk]
# RetrievedChunk = {id, title, text, role_family, score}
```

Exposed as a LangChain tool so the scoring node can call it (proposal: tool calling).

**Scoring module:** [src/resume_screener/agents/scoring_agent.py](src/resume_screener/agents/scoring_agent.py)

```python
def score_candidate(candidate: CandidateProfile, role: RoleProfile, resume_text: str) -> tuple[Scorecard, list[RetrievedChunk]]
```

**Behavior**

- Build retrieval query from `role.title` + must-have skills + role_family filter.
- Prompt the scorer to evaluate **skills, then experience, then education**, each with evidence spans from the resume (planning).
- Apply label decision rules above. If evidence is thin, lower `confidence` and add `recruiter_questions`.
- Rationale must cite resume evidence, not invent employers or degrees.

**Done when**

- Retriever returns same-family chunks for a known query.
- `score_candidate` returns a valid Scorecard for one Strong, one Possible, one Not Relevant fixture (labels need not be perfect yet).
- Scorecard fails validation if evidence is empty on a score >= 8 (enforce `min_length` on evidence when score is high, or a custom validator).

---

## Phase 5 — LangGraph, HITL, and audit log

**Goal:** End-to-end agentic loop with routing, interrupt, and 100% audit writes.

```mermaid
flowchart TD
  ingest[ingest] --> parse[parse]
  parse --> retrieve[retrieve]
  retrieve --> score[score]
  score --> validate[validate]
  validate -->|auto| persist[persist]
  validate -->|hitl| humanReview[human_review]
  humanReview --> persist
```

**State** ([src/resume_screener/graph/state.py](src/resume_screener/graph/state.py))

- `resume_text`, `jd_text`, `resume_filename`, `jd_title`
- `candidate_profile`, `role_profile`
- `retrieved_chunks`
- `scorecard`
- `needs_human_review: bool`
- `recruiter_feedback: {final_label, notes} | None`
- `tracking_id`, `thread_id`
- `error: str | None`

**Graph** ([src/resume_screener/graph/workflow.py](src/resume_screener/graph/workflow.py))

- Checkpointer: `SqliteSaver` at `data/checkpoints.db` (survives Streamlit reruns).
- `human_review` uses LangGraph `interrupt()` with payload: scorecard summary + `recruiter_questions`.
- Resume via `Command(resume=recruiter_feedback)`.
- Memory: thread state + append-only override log (`data/overrides.jsonl`) for later prompt refinement.

**SQLite** ([src/resume_screener/persistence/tracking.py](src/resume_screener/persistence/tracking.py))

- Table `tracking` matching `TrackingRecord`.
- API: `insert_run(...)`, `finalize_disposition(...)`, `list_pending_review()`, `list_all()`, `export_csv()`.

**Public API**

```python
def start_screening(resume_path: Path, jd_text: str, thread_id: str) -> ScreeningResult
def resume_review(thread_id: str, final_label: MatchLabel, notes: str) -> ScreeningResult
```

**Done when**

- High-confidence Strong/Not Relevant run writes one tracking row and does not leave a pending interrupt.
- Possible Fit or low confidence leaves an interrupt; `resume_review` sets `overridden` correctly and writes `final_label`.
- Failed parse/score sets `error` and still writes an audit row (or a dedicated error row) — no silent drops.

---

## Phase 6 — Streamlit recruiter UI

**Goal:** Demoable recruiter workflow on top of the graph API. No scoring of names.

**App:** [app/streamlit_app.py](app/streamlit_app.py) (or `app/pages/` if split)

**Page: Screen candidate**

- Upload PDF, paste or upload JD.
- Run `start_screening`.
- Show dimension scores (1–10), overall label, confidence, rationale, retrieved benchmark titles, recommended action.
- If HITL required, show banner and link to Review Queue.
- Do not display candidate name.

**Page: Review queue**

- List pending interrupts (`list_pending_review`).
- Show pre-filled summary + agent questions.
- Actions: upgrade / downgrade / keep; notes textarea; Submit calls `resume_review`.

**Page: Tracking log**

- Table: time, JD title, predicted label, final label, confidence, overridden, HITL flag.
- Filters: label, role_family, overridden.
- CSV export.
- Filename may appear here; still no demographic fields.

**Done when**

- Happy path: upload fixture PDF + JD -> scorecard on screen in one session.
- HITL path: Possible Fit appears in queue; submit override; log shows `overridden=true` and new final label.
- Refresh does not lose in-flight review (Sqlite checkpointer).

---

## Phase 7 — Evaluation, packaging, docs

**Goal:** Measure proposal metrics and make the demo reproducible.

**Eval harness** ([eval/run_eval.py](eval/run_eval.py))

- Iterate `labels.json`. For each case: parse + score **without HITL** (predicted label = scorecard.overall_label).
- Write `eval/results/report.json` and a markdown summary:

  - accuracy
  - confusion matrix
  - FPR (Not Relevant -> Strong Match)
  - latency p50/p95
  - DeepEval faithfulness (rationale vs resume+JD; skip gracefully if DeepEval/API unavailable)
- Recruiter override rate is documented as a manual metric from the Review Queue, not auto-computed in v1.

**Packaging**

- [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml): Streamlit on 8501, volume `./data`.
- Optional first-run ingest if Chroma dir empty.
- [README.md](README.md): setup, `.env`, ingest, `streamlit run`, `python eval/run_eval.py`, demo script (3 fixture IDs), limitations, responsible-AI notes (PII strip, HITL, audit).

**Done when**

- `eval/run_eval.py` completes on all 30 pairs and prints the four automatic metrics.
- Prompt/threshold tuned if accuracy or FPR miss targets (iterate in this phase, not by expanding scope).
- `docker compose up` serves the app.
- README is sufficient for a third party to run the demo with only an OpenAI key.

---

## Dependency and risk notes

- **API keys:** OpenAI required from Phase 3 onward. Anthropic and LangSmith optional.
- **Cost/latency:** 30-pair eval is two LLM calls per pair (parse + score) plus embeddings at ingest. Keep prompts tight to stay under 90s p95.
- **Label quality:** Phase 4 fixtures only prove wiring; Phase 7 is when accuracy is tuned.
- **No AWS AgentCore** — proposal stack is LangGraph + Streamlit, not Bedrock/AgentCore.
