from __future__ import annotations

from collections import Counter

from resume_screener.eval.load import load_eval_cases, resolve_eval_path
from resume_screener.parsing.pdf import extract_resume_text
from resume_screener.schemas import EvalCase, MatchLabel, RoleFamily

HARD_CASE_MARKERS = (
    "synonym skills",
    "keyword-stuffed",
    "career-switcher",
    "overqualified mismatch",
    "missing degree",
    "uncommon tool",
)


def test_labels_json_validates_thirty_eval_cases():
    cases = load_eval_cases()
    assert len(cases) == 30
    assert all(isinstance(case, EvalCase) for case in cases)
    assert len({case.id for case in cases}) == 30


def test_role_family_balance():
    families = Counter(case.role_family for case in load_eval_cases())
    assert families[RoleFamily.engineering] == 10
    assert families[RoleFamily.product_design] == 10
    assert families[RoleFamily.operations] == 10


def test_label_balance_is_cross_cut():
    cases = load_eval_cases()
    labels = Counter(case.label for case in cases)
    assert labels[MatchLabel.strong_match] == 10
    assert labels[MatchLabel.possible_fit] == 10
    assert labels[MatchLabel.not_relevant] == 10
    # Cross-cut: not 10 of each family×label cell (that would be 90).
    cells = Counter((case.role_family, case.label) for case in cases)
    assert len(cells) == 9
    assert max(cells.values()) < 10


def test_hard_cases_documented_in_notes():
    notes = " ".join(case.notes.lower() for case in load_eval_cases())
    for marker in HARD_CASE_MARKERS:
        assert marker in notes, f"missing hard case marker: {marker}"


def test_eval_source_files_exist_and_pdfs_extract():
    for case in load_eval_cases():
        jd = resolve_eval_path(case.jd_path)
        pdf = resolve_eval_path(case.resume_pdf)
        md = pdf.with_suffix(".md")
        assert jd.is_file(), case.jd_path
        assert md.is_file(), md
        assert pdf.is_file(), case.resume_pdf
        text = extract_resume_text(pdf)
        assert text.strip(), case.id


def test_readme_documents_pdf_and_index_regen():
    from resume_screener.paths import REPO_ROOT

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "python -m resume_screener.eval.render_pdfs" in readme
    assert "python -m resume_screener.rag.ingest" in readme
