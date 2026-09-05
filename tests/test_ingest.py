from __future__ import annotations

from pathlib import Path

from resume_screener.config import Settings
from resume_screener.paths import KB_DIR, REPO_ROOT
from resume_screener.rag.ingest import (
    chunk_kb_dir,
    ingest_competency_kb,
    main as ingest_main,
    query_competency,
)


def test_kb_has_thirty_to_fifty_markdown_files():
    files = list(KB_DIR.glob("*.md"))
    assert 30 <= len(files) <= 50


def test_chunk_kb_includes_role_family_source_title():
    chunks = chunk_kb_dir(KB_DIR)
    assert chunks
    backend = [c for c in chunks if "backend" in c["text"].lower()]
    assert backend
    sample = backend[0]
    assert sample["role_family"]
    assert sample["source"]
    assert sample["title"]


def test_ingest_creates_store_and_backend_query_hits(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RESUME_SCREENER_EMBEDDINGS", "local")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    chroma_dir = tmp_path / "chroma"
    settings = Settings(openai_api_key="", chroma_dir=chroma_dir)
    count = ingest_competency_kb(kb_dir=KB_DIR, chroma_dir=chroma_dir, settings=settings)
    assert count >= 1
    assert chroma_dir.exists()
    hits = query_competency(
        "backend software engineer", k=5, chroma_dir=chroma_dir, settings=settings
    )
    assert len(hits) >= 1
    assert hits[0]["id"]
    assert hits[0]["text"]


def test_ingest_cli_creates_data_chroma(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RESUME_SCREENER_EMBEDDINGS", "local")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.chdir(REPO_ROOT)
    chroma_dir = tmp_path / "cli-chroma"
    assert ingest_main(["--chroma-dir", str(chroma_dir), "--query", "backend software engineer"]) == 0
    assert chroma_dir.exists()
    assert any(chroma_dir.iterdir())
