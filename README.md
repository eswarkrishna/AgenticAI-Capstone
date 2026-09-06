# Resume Screening Agent

AI-powered resume screening and candidate triage. Phase 1 is the typed shell and PDF extract. Phase 2 adds the labelled eval set and a retrievable competency index. Later phases add parsing, scoring, HITL, and the live recruiter workflow.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

OpenAI is required from Phase 3 onward for live LLM calls. Unit tests mock the model.

```bash
pytest
streamlit run app/streamlit_app.py
```

## Parsing (Phase 3)

`parse_documents(resume_text, jd_text)` wraps untrusted text in `<<<RESUME>>>` / `<<<JOB_DESCRIPTION>>>` delimiters, calls the parse model with structured Pydantic output, drops PII, and retries once on `ValidationError`. Tests inject a fake LLM; a live run needs `OPENAI_API_KEY`.

## Scoring and RAG (Phase 4)

`retrieve_competency_benchmarks(role_family, query)` returns same-family Chroma chunks and is also a LangChain tool. `score_candidate(candidate, role, resume_text)` retrieves benchmarks, scores skills → experience → education with resume-grounded evidence, then applies label rules (never Strong Match when must-haves are absent).

## Graph, HITL, and audit (Phase 5)

`start_screening(resume_path, jd_text, thread_id)` runs the LangGraph loop: ingest → parse → retrieve → score → validate → persist, or `interrupt()` for human review. High-confidence Strong Match / Not Relevant (`confidence >= 0.7`) auto-persists. Possible Fit or low confidence pauses; `resume_review(thread_id, final_label, notes)` resumes via `Command(resume=...)`.

Every run writes a SQLite `tracking` row (`data/tracking.db`). Recruiter decisions append to `data/overrides.jsonl`. Checkpoints live in `data/checkpoints.db` so a Streamlit refresh can resume an in-flight review. Tests inject fake LLMs; a live run needs `OPENAI_API_KEY`.

## Recruiter UI (Phase 6)

`streamlit run app/streamlit_app.py` serves three pages:

- **Screen** — upload a resume PDF and paste/upload a JD, or click a demo fixture. Shows dimension scores, overall label, confidence, rationale, competency benchmark titles, and recommended action. Possible Fit / low confidence shows a banner and a link to Review. Candidate name is never displayed.
- **Review** — pending HITL rows with agent questions. Keep / upgrade / downgrade + notes, then `resume_review`. SQLite checkpoints survive a browser refresh.
- **Log** — audit table with filters (label, role family, overridden) and CSV export. Filename is allowed; no demographic columns.

Without `OPENAI_API_KEY`, the three demo fixtures (`eng-sm-01` Strong Match, `eng-pf-01` Possible Fit, `eng-nr-02` Not Relevant) still run using the same recorded parse/score scripts as the tests. Custom uploads need a key.

```bash
streamlit run app/streamlit_app.py
```

## Regenerating eval PDFs

Resumes are authored as markdown in `data/eval/resumes/*.md` and rendered to PDF with fpdf2 so PyMuPDF stays on the extraction path.

```bash
python -m resume_screener.eval.render_pdfs
```

Job descriptions stay markdown in `data/eval/jds/`. Labels and paths live in `data/eval/labels.json` (30 `EvalCase` rows: 10/10/10 by role family and by label, cross-cut).

To rewrite the markdown sources from the bundled case list:

```bash
python scripts/write_eval_data.py
python -m resume_screener.eval.render_pdfs
```

## Regenerating the competency index

Markdown clusters live in `data/competency_kb/` (30–50 short O*NET-inspired files). Chunk by heading, embed, and persist Chroma collection `competency_benchmarks`:

```bash
python -m resume_screener.rag.ingest
```

This creates `data/chroma/`. With `OPENAI_API_KEY` set, embeddings use `EMBEDDING_MODEL` (default `text-embedding-3-small`). Without a key, or with `RESUME_SCREENER_EMBEDDINGS=local`, ingest uses a deterministic token-hash embedding suitable for smoke tests.

A smoke query for `backend software engineer` should return at least one chunk.
