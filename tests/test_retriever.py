from __future__ import annotations

from pathlib import Path

import pytest

from resume_screener.config import Settings
from resume_screener.paths import KB_DIR
from resume_screener.rag.ingest import ingest_competency_kb
from resume_screener.rag.retriever import (
    retrieve_competency_benchmarks,
    retrieve_competency_benchmarks_tool,
)
from resume_screener.schemas import RoleFamily


@pytest.fixture
def local_chroma(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("RESUME_SCREENER_EMBEDDINGS", "local")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    chroma_dir = tmp_path / "chroma"
    settings = Settings(openai_api_key="", chroma_dir=chroma_dir)
    ingest_competency_kb(kb_dir=KB_DIR, chroma_dir=chroma_dir, settings=settings)
    return chroma_dir


def test_retriever_returns_same_role_family(local_chroma: Path):
    settings = Settings(openai_api_key="", chroma_dir=local_chroma)
    chunks = retrieve_competency_benchmarks(
        RoleFamily.engineering,
        "backend software engineer python APIs",
        k=5,
        chroma_dir=local_chroma,
        settings=settings,
    )
    assert chunks
    assert all(chunk.role_family is RoleFamily.engineering for chunk in chunks)
    assert all(chunk.id and chunk.text for chunk in chunks)


def test_retriever_product_design_does_not_return_ops(local_chroma: Path):
    settings = Settings(openai_api_key="", chroma_dir=local_chroma)
    chunks = retrieve_competency_benchmarks(
        RoleFamily.product_design,
        "product designer Figma user flows",
        k=5,
        chroma_dir=local_chroma,
        settings=settings,
    )
    assert chunks
    assert all(chunk.role_family is RoleFamily.product_design for chunk in chunks)


def test_retriever_exposed_as_langchain_tool():
    assert retrieve_competency_benchmarks_tool.name == "retrieve_competency_benchmarks"
    schema = retrieve_competency_benchmarks_tool.args_schema
    assert schema is not None
    assert "role_family" in schema.model_fields
    assert "query" in schema.model_fields
