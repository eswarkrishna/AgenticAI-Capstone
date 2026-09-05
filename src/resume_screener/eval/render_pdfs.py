"""Render resume markdown to PDF with fpdf2 so PyMuPDF stays on the extract path."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from resume_screener.paths import EVAL_RESUMES_DIR

_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")


def _ascii(text: str) -> str:
    return (
        text.replace("—", "-")
        .replace("–", "-")
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def markdown_to_pdf(md_path: Path, pdf_path: Path) -> None:
    pdf = FPDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_left_margin(18)
    pdf.set_right_margin(18)
    width = pdf.epw

    for raw in md_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line:
            pdf.ln(3)
            continue
        heading = _HEADING.match(line)
        pdf.set_x(pdf.l_margin)
        if heading:
            level = len(heading.group(1))
            title = _ascii(heading.group(2).strip())
            size = {1: 16, 2: 13, 3: 11}[level]
            if level == 2:
                pdf.ln(2)
            pdf.set_font("Helvetica", "B", size)
            pdf.multi_cell(
                width, size * 0.45, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT
            )
            continue
        body = _ascii(line.strip())
        if body.startswith("- "):
            body = f"* {body[2:]}"
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(width, 6, body, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(pdf_path))


def render_eval_resumes(resumes_dir: Path | None = None) -> list[Path]:
    directory = Path(resumes_dir or EVAL_RESUMES_DIR)
    written: list[Path] = []
    for md_path in sorted(directory.glob("*.md")):
        pdf_path = md_path.with_suffix(".pdf")
        markdown_to_pdf(md_path, pdf_path)
        written.append(pdf_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render eval resume markdown to PDF")
    parser.add_argument("--resumes-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    written = render_eval_resumes(args.resumes_dir)
    print(f"rendered {len(written)} PDFs")
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
