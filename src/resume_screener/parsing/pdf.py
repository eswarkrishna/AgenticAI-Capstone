"""PDF text extraction via PyMuPDF. No LLM calls."""

from __future__ import annotations

from pathlib import Path

import pymupdf


def extract_resume_text(path: Path) -> str:
    """Return concatenated text from every page of `path`.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if extraction yields only whitespace.
    """
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)

    with pymupdf.open(pdf_path) as doc:
        pages = [page.get_text("text") for page in doc]
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError(f"no extractable text in {pdf_path}")
    return text
