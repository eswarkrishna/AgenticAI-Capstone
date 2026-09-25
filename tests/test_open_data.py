"""Open-data import: PII redaction, role-family mapping, weak labels, end-to-end on fake PDFs."""

from __future__ import annotations

import json

from resume_screener.eval.open_data import (
    JobDescription,
    best_jd,
    classify_bucket,
    find_pii,
    import_open_resumes,
    load_engineering_jds,
    redact_text,
    weak_label,
)
from resume_screener.eval.render_pdfs import markdown_to_pdf
from resume_screener.parsing.pdf import extract_resume_text
from resume_screener.schemas import EvalCase, MatchLabel

DIRTY = """Jordan Hale
Summary
Accountant with 7 years in Company Name, City , State.
Contact: jordan.hale@example.com | (555) 123-4567 | linkedin.com/in/jordan-hale
123 Maple Street, Apt 4
Lakewood, CO 80228
Skills
Excel, QuickBooks, Adobe Acrobat
Personal Information
Date of Birth: 3rd of May, 1990
Sex: Female
Marital Status: Single
Nationality: Indian
Education
B.Com, State University, 2012
Gender :
Male
Age : 33
"""


def test_redact_text_removes_contact_address_and_demographics():
    result = redact_text(DIRTY, fallback_title="Accountant")
    text = result.text
    for needle in (
        "jordan.hale@example.com",
        "555",
        "linkedin.com",
        "Maple Street",
        "80228",
        "3rd of May",
        "Female",
        "Single",
        "Indian",
        "Male",
        "33",
    ):
        assert needle not in text, needle
    assert text.startswith("ACCOUNTANT")
    assert "[REDACTED_PERSONAL_INFORMATION]" in text
    assert "[REDACTED_EMAIL]" in text
    assert "[REDACTED_PHONE]" in text
    assert "[REDACTED_URL]" in text
    assert "[REDACTED_ADDRESS]" in text
    assert "[REDACTED_DEMOGRAPHIC]" in text
    # Publisher placeholders and real content survive.
    assert "Company Name, City , State" in text
    assert "Adobe Acrobat" in text
    assert "B.Com, State University, 2012" in text
    assert result.counts["name_header"] == 1
    assert result.counts["personal_block"] == 1
    assert find_pii(text) == {}


def test_redact_text_leaves_clean_resume_untouched():
    clean = "SENIOR ACCOUNTANT\nSummary\nAudit and close at Company Name, City , State.\n"
    result = redact_text(clean)
    assert result.text == clean.rstrip("\n")
    assert not result.changed
    assert find_pii(clean) == {}


def test_collapsed_personal_block_and_relative_names_are_dropped():
    text = (
        "Skills\nExcel, Tally\n"
        "Limited PERSONAL DETAILS Mother's Name: Mrs. Soma Devi, DOB 22-April-1990\n"
        "Languages known: Hindi, English\n"
        "Education\nB.Com 2012\n"
        "Age & Date of Birth 25, 22-April-1990 Hobbies: Cricket\n"
    )
    result = redact_text(text)
    out = result.text
    for needle in ("Soma Devi", "22-April-1990", "Hindi", "Hobbies"):
        assert needle not in out, needle
    assert "Limited [REDACTED_PERSONAL_INFORMATION]" in out
    assert "Education\nB.Com 2012" in out
    assert find_pii(out) == {}


def test_prose_age_self_intro_references_and_odd_phone_suffix():
    text = (
        "TEACHER\nSummary\n"
        "I, Annika Kay, at age 33 now, teach yoga. At age 55 I still do.\n"
        "Reach the office at (701) 627-4707\u00c2 or the desk at 701.441.1165x22.\n"
        "References\nEdward Lone Fight, Former Chair (406) 638-4433\n"
        "Jane Roe, Principal\n"
        "Skills\nCurriculum design\n"
    )
    out = redact_text(text).text
    for needle in ("Annika", "33", "55", "627-4707", "441.1165", "Edward", "Jane Roe"):
        assert needle not in out, needle
    assert "[REDACTED_NAME]" in out
    assert "[REDACTED_REFERENCES]" in out
    assert "Skills\nCurriculum design" in out
    assert find_pii(out) == {}


def test_adobe_is_not_a_date_of_birth():
    text = "Skills\nAdobe Photoshop, Adobe Illustrator, dobby the tool\n"
    assert find_pii(text) == {}
    assert not redact_text(text).changed


def test_classify_bucket_follows_agreed_mapping():
    assert classify_bucket("INFORMATION-TECHNOLOGY", "IT MANAGER") == "engineering"
    assert classify_bucket("ENGINEERING", "SOFTWARE ENGINEERING MANAGER") == "engineering"
    assert classify_bucket("ENGINEERING", "MECHANICAL ENGINEERING INTERN") == "not_relevant_pool"
    assert classify_bucket("DESIGNER", "GRAPHIC DESIGNER") == "not_relevant_pool"
    assert classify_bucket("CHEF", "EXECUTIVE CHEF") == "not_relevant_pool"


def test_weak_label_thresholds():
    assert weak_label(0, 4) is MatchLabel.not_relevant
    assert weak_label(1, 4) is MatchLabel.possible_fit
    assert weak_label(3, 4) is MatchLabel.strong_match
    assert weak_label(4, 4) is MatchLabel.strong_match
    assert weak_label(0, 0) is MatchLabel.not_relevant


def test_best_jd_uses_synonyms():
    jds = [
        JobDescription("a", "jds/a.md", "Platform", ["Kubernetes", "containers", "CI/CD"]),
        JobDescription("b", "jds/b.md", "Frontend", ["React", "TypeScript"]),
    ]
    text = "Ran k8s clusters with Docker images and Jenkins pipelines."
    jd, matched, total = best_jd(jds, text)
    assert jd.id == "a"
    assert (matched, total) == (3, 3)


def test_load_engineering_jds_reads_must_haves():
    jds = load_engineering_jds()
    assert {jd.id for jd in jds} >= {"eng-sm-01", "eng-nr-02"}
    sm01 = next(jd for jd in jds if jd.id == "eng-sm-01")
    assert "PostgreSQL" in sm01.must_haves
    assert sm01.path == "data/eval/jds/eng-sm-01.md"


def test_import_end_to_end_on_fake_dataset(tmp_path):
    source = tmp_path / "src"
    it_dir = source / "INFORMATION-TECHNOLOGY"
    chef_dir = source / "CHEF"
    md = tmp_path / "md"
    md.mkdir()
    it_md = md / "it.md"
    it_md.write_text(
        "SOFTWARE DEVELOPER\nSummary\nPython REST APIs on PostgreSQL with Docker.\n"
        "Call me at (555) 987-6543 or dev@example.com\nSex: Male\n",
        encoding="utf-8",
    )
    chef_md = md / "chef.md"
    chef_md.write_text(
        "EXECUTIVE CHEF\nSummary\nRan kitchens for Company Name in City , State.\n",
        encoding="utf-8",
    )
    dup_md = md / "dup.md"
    dup_md.write_text(chef_md.read_text(encoding="utf-8"), encoding="utf-8")
    markdown_to_pdf(it_md, it_dir / "1001.pdf")
    markdown_to_pdf(chef_md, chef_dir / "2001.pdf")
    markdown_to_pdf(dup_md, chef_dir / "2002.pdf")

    out = tmp_path / "out"
    labels = tmp_path / "labels_open.json"
    report = import_open_resumes(
        source, out_dir=out, labels_path=labels, sample=0, seed=1
    )

    assert report.scanned == 3
    assert report.kept == 2
    assert any(k.startswith("skipped:duplicate_of_2001") for k in report.skipped)
    assert report.redacted_files == 1
    assert report.buckets == {"engineering": 1, "not_relevant_pool": 1}

    it_text = extract_resume_text(out / "resumes" / "1001.pdf")
    assert "555" not in it_text and "dev@example.com" not in it_text
    assert "Male" not in it_text
    assert find_pii(it_text) == {}
    chef_row = next(r for r in report.rows if r.id == "2001")
    assert chef_row.pdf_source == "original"

    cases = [EvalCase.model_validate(item) for item in json.loads(labels.read_text())]
    by_id = {c.id: c for c in cases}
    assert by_id["lc-1001"].label is MatchLabel.strong_match
    assert by_id["lc-1001"].jd_path == "data/eval/jds/eng-sm-01.md"
    assert "weak label" in by_id["lc-1001"].notes
    assert by_id["lc-2001"].label is MatchLabel.not_relevant
    assert (out / "manifest.json").is_file()
