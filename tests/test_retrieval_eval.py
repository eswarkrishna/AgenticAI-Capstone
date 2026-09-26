"""Each labelled JD should retrieve its competency cluster in the top-k."""

from __future__ import annotations

from pathlib import Path

import pytest

from resume_screener.config import Settings
from resume_screener.eval.retrieval import EXPECTED_CLUSTER, evaluate_retrieval, query_from_jd
from resume_screener.paths import KB_DIR
from resume_screener.rag.ingest import ingest_competency_kb


@pytest.fixture
def local_chroma(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("RESUME_SCREENER_EMBEDDINGS", "local")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    chroma_dir = tmp_path / "chroma"
    settings = Settings(openai_api_key="", chroma_dir=chroma_dir)
    ingest_competency_kb(kb_dir=KB_DIR, chroma_dir=chroma_dir, settings=settings)
    return chroma_dir


def test_every_case_has_an_expected_cluster():
    from resume_screener.eval.load import load_eval_cases

    ids = {case.id for case in load_eval_cases()}
    assert set(EXPECTED_CLUSTER) == ids


def test_query_from_jd_uses_title_and_must_haves():
    query = query_from_jd(
        "# Backend Software Engineer\n\n## Must-haves\n- Python\n- PostgreSQL\n\n## Years\n5+\n"
    )
    assert "Backend Software Engineer" in query
    assert "Python" in query
    assert "PostgreSQL" in query
    assert "5+" not in query


def test_expected_cluster_is_in_top_k(local_chroma: Path):
    settings = Settings(openai_api_key="", chroma_dir=local_chroma)
    report = evaluate_retrieval(settings, k=5)
    assert report["available"] is True, report["error"]
    assert report["misses"] == [], report
    assert report["hit_rate"] == 1.0
