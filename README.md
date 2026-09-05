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
pytest tests/test_schemas.py tests/test_pdf.py tests/test_eval_cases.py tests/test_ingest.py tests/test_parsing_agent.py
streamlit run app/streamlit_app.py
```

## Parsing (Phase 3)

`parse_documents(resume_text, jd_text)` wraps untrusted text in `<<<RESUME>>>` / `<<<JOB_DESCRIPTION>>>` delimiters, calls the parse model with structured Pydantic output, drops PII, and retries once on `ValidationError`. Tests inject a fake LLM; a live run needs `OPENAI_API_KEY`.

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
