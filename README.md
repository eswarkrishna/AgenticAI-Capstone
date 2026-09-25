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

## Importing the open resume set (optional)

The LiveCareer "Resume Dataset" (2,484 PDFs in 24 job categories) can be imported as a second, larger eval set. It is only partially anonymized upstream, so the importer redacts before anything is written under the repo:

- Drops name headers, emails, phone numbers, URLs, street and city/state/zip addresses, `Personal Information` / `Personal Details` blocks (also when collapsed onto one line), demographic fields (date of birth, gender, marital status, nationality, religion, age, passport/visa), self-introductions ("I, Jane Doe, …"), and `References` sections.
- Copies PDFs that needed no redaction byte-for-byte so the real-world layout survives; re-renders redacted ones with fpdf2. Every output PDF is re-extracted and re-scanned; anything with a residual hit is excluded and listed in the manifest.
- Skips blank PDFs and exact duplicates.

Mapping to `RoleFamily`: `INFORMATION-TECHNOLOGY` plus software-titled `ENGINEERING` resumes are engineering candidates, paired with the engineering JD whose must-haves overlap most (label from overlap ratio: ≥ 75% Strong Match, > 0 Possible Fit, 0 Not Relevant). Every other category is a `not_relevant` pool against a random engineering JD. All labels are weak and say so in `notes`; review them before quoting accuracy on this set.

```bash
python -m resume_screener.eval.open_data --source /path/to/archive/data/data
python eval/run_eval.py --labels data/eval/labels_open.json --results-dir eval/results_open
```

Outputs: redacted PDFs and `manifest.json` under `data/external/livecareer/` (gitignored), and a stratified `data/eval/labels_open.json` (`--sample 150` by default; `--sample 0` writes every kept resume). Each harness case costs one parse and one score call. The 30-case `labels.json` and its tests are untouched.

## Regenerating the competency index

Markdown clusters live in `data/competency_kb/` (30–50 short O*NET-inspired files). Chunk by heading, embed, and persist Chroma collection `competency_benchmarks`:

```bash
python -m resume_screener.rag.ingest
```

This creates `data/chroma/`. With `OPENAI_API_KEY` set, embeddings use `EMBEDDING_MODEL` (default `text-embedding-3-small`). Without a key, or with `RESUME_SCREENER_EMBEDDINGS=local`, ingest uses a deterministic token-hash embedding suitable for smoke tests.

A smoke query for `backend software engineer` should return at least one chunk.

Rebuild the index after changing `OPENAI_API_KEY` or `EMBEDDING_MODEL`. Chroma stores one vector size per collection. A local ingest is 64 dimensions; `text-embedding-3-small` is 1536. Mixing them fails retrieval with a dimension error.

## Evaluation (Phase 7)

`python eval/run_eval.py` scores every pair in `data/eval/labels.json`. Each case runs parse and score only. The predicted label is `scorecard.overall_label`. The harness does not resume human review, so recruiter overrides are not applied.

It prints accuracy, false-positive rate (ground-truth Not Relevant predicted Strong Match), latency p50/p95, and audit completeness, and writes `eval/results/report.json` plus `eval/results/report.md`.

Targets: accuracy ≥ 85%, FPR ≤ 5%, p95 < 90s, and a tracking row for every case. DeepEval faithfulness is recorded when the package is installed; otherwise the report skips it. Recruiter override rate stays a manual Review Queue metric.

## Demo script

With or without `OPENAI_API_KEY`, open the Screen page and run these three fixtures:

1. `eng-sm-01` — Strong Match (auto-persist when confidence is high).
2. `eng-pf-01` — Possible Fit. Open Review, keep or change the label, add notes, and submit.
3. `eng-nr-02` — Not Relevant.

Then open Log, filter by label or role family, and export CSV. Candidate name is never shown.

Custom PDF uploads need `OPENAI_API_KEY`.

## Docker

```bash
docker compose up --build
```

Streamlit listens on port 8501. `./data` is mounted so tracking, checkpoints, and Chroma persist. If `data/chroma` is empty, the container ingests the competency KB on startup.

## Limitations

- Labels come from a 30-pair synthetic set, not live applicants.
- Dimension scores use the model; the Strong Match / Possible Fit / Not Relevant label is then applied by fixed rules.
- Embeddings and the index must be built with the same model.
- DeepEval faithfulness is optional and is not a release gate.
- No applicant-tracking-system integration, login, or interview decision.

## Responsible use

The parser drops name, email, phone, gender, age, nationality, photo, and address before scoring. Possible Fit and low-confidence Strong Match or Not Relevant stop for a recruiter. Every run writes a SQLite tracking row, and Review decisions append to `data/overrides.jsonl`. The scorecard is a triage aid. A person decides who moves forward.
