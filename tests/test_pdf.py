from __future__ import annotations

from pathlib import Path

import pytest

from resume_screener.parsing.pdf import extract_resume_text

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_resume.pdf"


def test_extract_resume_text_returns_non_empty_from_fixture():
    text = extract_resume_text(FIXTURE)
    assert text.strip()
    assert "Software Engineer" in text
    assert "Python" in text


def test_extract_resume_text_missing_file():
    with pytest.raises(FileNotFoundError):
        extract_resume_text(FIXTURE.parent / "does-not-exist.pdf")
