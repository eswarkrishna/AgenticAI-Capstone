"""Import the LiveCareer open resume set: redact PII, keep a clean PDF, emit weak labels.

Source layout (Kaggle "Resume Dataset"): ``<source>/<CATEGORY>/<id>.pdf``.

Mapping agreed for this project:
- ``INFORMATION-TECHNOLOGY`` and software-titled ``ENGINEERING`` resumes are
  engineering candidates and are paired with the engineering JD whose
  must-haves overlap most. Label from overlap ratio; ``notes`` marks it weak.
- Every other category is a ``not_relevant`` pool against a random
  engineering JD.

Files that need no redaction are copied byte-for-byte so the real-world PDF
layout survives. Files with PII are redacted in text and re-rendered with
fpdf2. Every output PDF is re-extracted and re-scanned; anything with a
residual hit is excluded and reported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import shutil
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from resume_screener.eval.render_pdfs import markdown_to_pdf
from resume_screener.parsing.pdf import extract_resume_text
from resume_screener.paths import (
    EVAL_JDS_DIR,
    EVAL_OPEN_LABELS_PATH,
    OPEN_DATA_DIR,
    REPO_ROOT,
)
from resume_screener.schemas import EvalCase, MatchLabel, RoleFamily

# --------------------------------------------------------------------------- #
# PII patterns
# --------------------------------------------------------------------------- #

EMAIL_RX = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
URL_RX = re.compile(
    r"(?:https?://|www\.)\S+|\b[\w-]+\.(?:com|net|org|io|me|co)/\S+", re.I
)
PHONE_RX = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"
)
# "At age 55", "age: 41". Also catches "girls age 10-14"; over-redaction is fine.
AGE_PROSE_RX = re.compile(r"\b(?:at\s+)?age\s*[:\-]?\s*\d{2}\b", re.I)
# Self-introductions in prose: "I, Jane Q. Doe, ..." / "My name is Jane Doe".
SELF_INTRO_RX = re.compile(
    r"\bI,\s+[A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){1,3},|"
    r"(?i:\bmy name is)\s+[A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,3}"
)
STREET_RX = re.compile(
    r"\b\d{1,6}\s+(?:[A-Z][a-z]+\s){0,3}"
    r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Lane|Ln\.?|"
    r"Drive|Dr\.?|Court|Ct\.?|Way|Place|Pl\.?|Circle|Cir\.?|Terrace|Ter\.?)\b"
    r"(?:[,\s]+(?:Apt\.?|Unit|Suite|Ste\.?|#)\s*\w+)?"
)
CITY_STATE_ZIP_RX = re.compile(r"\b[A-Z][a-zA-Z .]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b")

_DEMO_FIELD = (
    r"(?:date of birth|d\.?o\.?b\.?|birth ?date|place of birth|gender|sex|"
    r"marital status|nationality|citizenship|religion|caste|"
    r"passport(?: no\.?| number)?|visa status|father'?s name|mother'?s name|"
    r"spouse(?: name)?|blood group|age)"
)
DEMO_LINE_RX = re.compile(rf"^\s*{_DEMO_FIELD}\s*[:\-–]\s*(?P<value>.*)$", re.I)
# A demographic field mid-line: drop everything to the end of that line.
# Personal-details blocks are often collapsed onto one line by PDF extraction.
DEMO_INLINE_RX = re.compile(rf"\b{_DEMO_FIELD}\s*[:\-–].*$", re.I | re.M)
DOB_WORD_RX = re.compile(
    r"(?:\b(?i:date of birth|birth ?date|place of birth)\b|\bDOB\b).*$", re.M
)
# Upper-case section title glued onto a content line (e.g. "PERSONAL DETAILS Age ...").
PERSONAL_INLINE_RX = re.compile(r"\bPERSONAL (?:DETAILS|INFORMATION|PROFILE|DATA|DOSSIER)\b")

NAME_HEADER_RX = re.compile(r"^(?:[A-Z][a-z]+[.,]?\s){1,3}[A-Z][a-z]+\.?$")

PERSONAL_HEADERS = frozenset(
    {
        "personal information",
        "personal details",
        "personal profile",
        "personal data",
        "personal",
        "personal dossier",
    }
)
SECTION_HEADERS = frozenset(
    {
        "summary",
        "professional summary",
        "career overview",
        "executive profile",
        "professional profile",
        "objective",
        "career objective",
        "skills",
        "skill highlights",
        "highlights",
        "core qualifications",
        "qualifications",
        "technical skills",
        "experience",
        "work experience",
        "work history",
        "professional experience",
        "employment history",
        "education",
        "education and training",
        "certifications",
        "credentials",
        "training",
        "accomplishments",
        "awards",
        "interests",
        "additional information",
        "affiliations",
        "professional affiliations",
        "languages",
        "publications",
        "references",
        "activities",
        "volunteer work",
    }
)
# References sections list third parties' names and phone numbers.
REFERENCE_HEADERS = frozenset({"references", "reference", "professional references"})
PERSONAL_BLOCK_MAX_LINES = 25

# Placeholders the publisher already inserted; these are not PII.
PUBLISHER_PLACEHOLDERS = ("Company Name", "City , State", "City, State")

# --------------------------------------------------------------------------- #
# Role-family mapping
# --------------------------------------------------------------------------- #

ENGINEERING_CATEGORIES = frozenset({"INFORMATION-TECHNOLOGY"})
SOFTWARE_TITLE_RX = re.compile(
    r"software|developer|programmer|devops|\bsre\b|\bdata\b|\bweb\b|cloud|"
    r"database|application|network|\bqa\b|test automation|\bit\b|firmware|"
    r"embedded|machine learning|\bml\b|full ?stack|front ?end|back ?end",
    re.I,
)
STRONG_MATCH_OVERLAP = 0.75

# Keyed by lower-cased JD must-have. Values are whole-word variants to look for.
SKILL_SYNONYMS: dict[str, tuple[str, ...]] = {
    "kubernetes": ("kubernetes", "k8s"),
    "postgresql": ("postgresql", "postgres"),
    "sql": ("sql", "postgresql", "mysql", "t-sql", "pl/sql", "sql server"),
    "apis": ("api", "apis", "rest", "restful"),
    "rest apis": ("rest", "restful", "api", "apis"),
    "ci/cd": ("ci/cd", "jenkins", "github actions", "gitlab ci", "continuous integration"),
    "containers": ("docker", "container", "containers"),
    "google cloud": ("google cloud", "gcp"),
    "observability": ("observability", "prometheus", "grafana", "datadog", "monitoring"),
    "javascript": ("javascript", "js"),
    "data warehousing": ("warehouse", "warehousing", "redshift", "snowflake", "bigquery"),
    "apache spark": ("spark",),
    "distributed systems": ("distributed", "microservices"),
    "system design": ("system design", "architecture", "architected"),
    "service design": ("service design", "microservice", "microservices"),
    "production ownership": ("on-call", "on call", "production support", "incident"),
    "incident leadership": ("incident", "incidents"),
    "mentoring": ("mentor", "mentored", "mentoring", "coached"),
    "python or go": ("python", "golang"),
    "go": ("golang",),
    "grpc": ("grpc",),
    "temporal workflows": ("temporal",),
    "nats messaging": ("nats",),
    "nix builds": ("nix",),
    "react": ("react", "reactjs", "react.js"),
    "css": ("css", "scss", "sass"),
    "accessibility": ("accessibility", "wcag", "a11y", "section 508"),
    "aws": ("aws", "amazon web services"),
}


# --------------------------------------------------------------------------- #
# Redaction
# --------------------------------------------------------------------------- #


@dataclass
class Redaction:
    text: str
    counts: Counter = field(default_factory=Counter)

    @property
    def changed(self) -> bool:
        return sum(self.counts.values()) > 0


def _is_section_header(line: str) -> bool:
    return line.strip().lower().rstrip(":") in SECTION_HEADERS


def _is_personal_header(line: str) -> bool:
    return line.strip().lower().rstrip(":") in PERSONAL_HEADERS


def _is_reference_header(line: str) -> bool:
    return line.strip().lower().rstrip(":") in REFERENCE_HEADERS


def redact_text(text: str, fallback_title: str = "Candidate") -> Redaction:
    """Return `text` with PII replaced by ``[REDACTED_*]`` tokens.

    Publisher placeholders (``Company Name``, ``City , State``) are kept.
    """
    counts: Counter = Counter()
    lines = text.splitlines()
    out: list[str] = []

    # 1. Name header: first non-empty line in Title Case that is not a section.
    first_idx = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if first_idx is not None:
        first = lines[first_idx].strip()
        if NAME_HEADER_RX.match(first) and not _is_section_header(first):
            lines[first_idx] = fallback_title.upper()
            counts["name_header"] += 1

    # 2. Personal-information blocks and demographic field lines.
    def _skip_block(start: int) -> int:
        """Index of the next section header after `start`, capped."""
        j = start
        dropped = 0
        while (
            j < len(lines)
            and dropped < PERSONAL_BLOCK_MAX_LINES
            and not _is_section_header(lines[j])
        ):
            j += 1
            dropped += 1
        return j

    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_personal_header(line):
            out.append("[REDACTED_PERSONAL_INFORMATION]")
            counts["personal_block"] += 1
            i = _skip_block(i + 1)
            continue
        if _is_reference_header(line):
            out.append("[REDACTED_REFERENCES]")
            counts["references_block"] += 1
            i = _skip_block(i + 1)
            continue
        inline = PERSONAL_INLINE_RX.search(line)
        if inline:
            out.append(line[: inline.start()] + "[REDACTED_PERSONAL_INFORMATION]")
            counts["personal_block"] += 1
            i = _skip_block(i + 1)
            continue
        match = DEMO_LINE_RX.match(line)
        if match:
            out.append("[REDACTED_DEMOGRAPHIC]")
            counts["demographic"] += 1
            i += 1
            if not match.group("value").strip():
                # "Gender :" with the value on the next line.
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i < len(lines) and not _is_section_header(lines[i]):
                    i += 1
            continue
        out.append(line)
        i += 1

    body = "\n".join(out)

    # 3. Inline substitutions.
    def _sub(rx: re.Pattern[str], token: str, key: str, source: str) -> str:
        result, n = rx.subn(token, source)
        counts[key] += n
        return result

    body = _sub(DEMO_INLINE_RX, "[REDACTED_DEMOGRAPHIC]", "demographic", body)
    body = _sub(DOB_WORD_RX, "[REDACTED_DEMOGRAPHIC]", "demographic", body)
    body = _sub(AGE_PROSE_RX, "[REDACTED_DEMOGRAPHIC]", "demographic", body)
    body = _sub(SELF_INTRO_RX, "[REDACTED_NAME]", "name_in_prose", body)
    body = _sub(URL_RX, "[REDACTED_URL]", "url", body)
    body = _sub(EMAIL_RX, "[REDACTED_EMAIL]", "email", body)
    body = _sub(STREET_RX, "[REDACTED_ADDRESS]", "address", body)
    body = _sub(CITY_STATE_ZIP_RX, "[REDACTED_ADDRESS]", "address", body)
    body = _sub(PHONE_RX, "[REDACTED_PHONE]", "phone", body)
    return Redaction(text=body, counts=counts)


def find_pii(text: str) -> Counter:
    """Count residual PII hits. Empty when the text is clean."""
    hits: Counter = Counter()
    for key, rx in (
        ("email", EMAIL_RX),
        ("url", URL_RX),
        ("phone", PHONE_RX),
        ("address", STREET_RX),
        ("address", CITY_STATE_ZIP_RX),
        ("demographic", DEMO_INLINE_RX),
        ("demographic", DOB_WORD_RX),
        ("demographic", AGE_PROSE_RX),
        ("name_in_prose", SELF_INTRO_RX),
        ("personal_block", PERSONAL_INLINE_RX),
    ):
        n = len(rx.findall(text))
        if n:
            hits[key] += n
    for line in text.splitlines():
        if _is_personal_header(line):
            hits["personal_block"] += 1
        elif _is_reference_header(line):
            hits["references_block"] += 1
    return hits


# --------------------------------------------------------------------------- #
# Mapping and weak labels
# --------------------------------------------------------------------------- #


def humanize_category(category: str) -> str:
    return category.replace("-", " ").title()


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def classify_bucket(category: str, title: str) -> str:
    """'engineering' for IT and software-titled ENGINEERING; else 'not_relevant_pool'."""
    if category in ENGINEERING_CATEGORIES:
        return "engineering"
    if category == "ENGINEERING" and SOFTWARE_TITLE_RX.search(title):
        return "engineering"
    return "not_relevant_pool"


@dataclass
class JobDescription:
    id: str
    path: str  # repo-relative posix
    title: str
    must_haves: list[str]


def load_engineering_jds(jds_dir: Path | None = None) -> list[JobDescription]:
    directory = Path(jds_dir or EVAL_JDS_DIR)
    jds: list[JobDescription] = []
    for path in sorted(directory.glob("eng-*.md")):
        title = ""
        must: list[str] = []
        section = ""
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("# ") and not title:
                title = line[2:].strip()
            elif line.startswith("## "):
                section = line[3:].strip().lower()
            elif line.startswith("- ") and section == "must-haves":
                must.append(line[2:].strip())
        rel = path.resolve().relative_to(REPO_ROOT).as_posix()
        jds.append(JobDescription(id=path.stem, path=rel, title=title, must_haves=must))
    if not jds:
        raise FileNotFoundError(f"no eng-*.md job descriptions in {directory}")
    return jds


def skill_present(skill: str, text_lower: str) -> bool:
    variants = SKILL_SYNONYMS.get(skill.lower(), (skill.lower(),))
    for variant in variants:
        if re.search(rf"(?<![\w]){re.escape(variant)}(?![\w])", text_lower):
            return True
    return False


def must_have_overlap(jd: JobDescription, text: str) -> tuple[int, int]:
    text_lower = text.lower()
    matched = sum(1 for skill in jd.must_haves if skill_present(skill, text_lower))
    return matched, len(jd.must_haves)


def weak_label(matched: int, total: int) -> MatchLabel:
    if total == 0 or matched == 0:
        return MatchLabel.not_relevant
    if matched / total >= STRONG_MATCH_OVERLAP:
        return MatchLabel.strong_match
    return MatchLabel.possible_fit


def best_jd(jds: list[JobDescription], text: str) -> tuple[JobDescription, int, int]:
    """Highest overlap ratio wins; ties go to the JD with more matched must-haves."""
    best = None
    for jd in jds:
        matched, total = must_have_overlap(jd, text)
        ratio = matched / total if total else 0.0
        key = (ratio, matched)
        if best is None or key > best[0]:
            best = (key, jd, matched, total)
    assert best is not None
    return best[1], best[2], best[3]


# --------------------------------------------------------------------------- #
# Import pipeline
# --------------------------------------------------------------------------- #


@dataclass
class ManifestRow:
    id: str
    category: str
    title: str
    bucket: str
    chars: int
    status: str  # kept | skipped:<reason>
    pdf_source: str  # original | rendered | ""
    redactions: dict[str, int]
    resume_pdf: str  # repo-relative posix or ""
    label: str = ""
    jd_id: str = ""
    must_have_matched: int = 0
    must_have_total: int = 0


@dataclass
class ImportReport:
    source_dir: str
    out_dir: str
    labels_path: str
    scanned: int
    kept: int
    skipped: dict[str, int]
    redacted_files: int
    redaction_counts: dict[str, int]
    buckets: dict[str, int]
    labels_written: int
    label_counts: dict[str, int]
    rows: list[ManifestRow]


def _normalized_hash(text: str) -> str:
    return hashlib.sha1(re.sub(r"\W+", "", text.lower()).encode()).hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _write_and_render(text: str, md_path: Path, pdf_path: Path) -> None:
    # A leading '#' would be read as a heading by markdown_to_pdf.
    safe = "\n".join(
        (" " + ln) if ln.lstrip().startswith("#") else ln for ln in text.splitlines()
    )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(safe + "\n", encoding="utf-8")
    markdown_to_pdf(md_path, pdf_path)


def process_pdf(
    src: Path, resumes_dir: Path, seen_hashes: dict[str, str]
) -> tuple[ManifestRow, str]:
    """Redact one PDF into `resumes_dir`. Returns (row, clean_text_for_labelling)."""
    category = src.parent.name
    rid = src.stem
    row = ManifestRow(
        id=rid, category=category, title="", bucket="", chars=0,
        status="", pdf_source="", redactions={}, resume_pdf="",
    )
    try:
        text = extract_resume_text(src)
    except ValueError:
        row.status = "skipped:empty_text"
        return row, ""
    row.chars = len(text)
    digest = _normalized_hash(text)
    if digest in seen_hashes:
        row.status = f"skipped:duplicate_of_{seen_hashes[digest]}"
        return row, ""
    seen_hashes[digest] = rid

    redaction = redact_text(text, fallback_title=humanize_category(category))
    row.title = first_line(redaction.text)
    row.bucket = classify_bucket(category, row.title)
    row.redactions = dict(redaction.counts)

    out_pdf = resumes_dir / f"{rid}.pdf"
    resumes_dir.mkdir(parents=True, exist_ok=True)
    if redaction.changed:
        _write_and_render(redaction.text, resumes_dir / f"{rid}.md", out_pdf)
        row.pdf_source = "rendered"
    else:
        shutil.copyfile(src, out_pdf)
        row.pdf_source = "original"

    # Verify what the pipeline will actually see.
    try:
        final_text = extract_resume_text(out_pdf)
    except ValueError:
        out_pdf.unlink(missing_ok=True)
        row.status = "skipped:render_empty"
        return row, ""
    residual = find_pii(final_text)
    if residual:
        out_pdf.unlink(missing_ok=True)
        (resumes_dir / f"{rid}.md").unlink(missing_ok=True)
        row.status = "skipped:pii_residual:" + ",".join(sorted(residual))
        return row, ""

    row.status = "kept"
    row.resume_pdf = _rel(out_pdf)
    return row, final_text


def build_labels(
    kept: list[tuple[ManifestRow, str]],
    jds: list[JobDescription],
    *,
    sample: int,
    seed: int,
) -> list[EvalCase]:
    rng = random.Random(seed)
    engineering = [item for item in kept if item[0].bucket == "engineering"]
    pool = [item for item in kept if item[0].bucket != "engineering"]

    if sample > 0:
        eng_n = min(len(engineering), sample // 2)
        engineering = rng.sample(engineering, eng_n)
        pool_n = min(len(pool), sample - eng_n)
        by_cat: dict[str, list] = {}
        for item in pool:
            by_cat.setdefault(item[0].category, []).append(item)
        for items in by_cat.values():
            rng.shuffle(items)
        picked: list = []
        while len(picked) < pool_n:
            progressed = False
            for cat in sorted(by_cat):
                if by_cat[cat] and len(picked) < pool_n:
                    picked.append(by_cat[cat].pop())
                    progressed = True
            if not progressed:
                break
        pool = picked

    cases: list[EvalCase] = []
    for row, text in engineering:
        jd, matched, total = best_jd(jds, text)
        label = weak_label(matched, total)
        row.label, row.jd_id = label.value, jd.id
        row.must_have_matched, row.must_have_total = matched, total
        cases.append(
            EvalCase(
                id=f"lc-{row.id}",
                role_family=RoleFamily.engineering,
                label=label,
                jd_path=jd.path,
                resume_pdf=row.resume_pdf,
                notes=(
                    f"weak label: must-have overlap {matched}/{total} vs {jd.id}; "
                    f"source category {row.category}; title '{row.title}'; "
                    "review before trusting"
                ),
            )
        )
    for row, _text in pool:
        jd = rng.choice(jds)
        row.label, row.jd_id = MatchLabel.not_relevant.value, jd.id
        cases.append(
            EvalCase(
                id=f"lc-{row.id}",
                role_family=RoleFamily.engineering,
                label=MatchLabel.not_relevant,
                jd_path=jd.path,
                resume_pdf=row.resume_pdf,
                notes=(
                    f"weak label: source category {row.category} is outside "
                    f"engineering; title '{row.title}'"
                ),
            )
        )
    cases.sort(key=lambda c: c.id)
    return cases


def import_open_resumes(
    source_dir: Path,
    *,
    out_dir: Path | None = None,
    labels_path: Path | None = None,
    jds_dir: Path | None = None,
    sample: int = 150,
    seed: int = 7,
    limit: int | None = None,
    progress: bool = False,
) -> ImportReport:
    source = Path(source_dir)
    if not source.is_dir():
        raise FileNotFoundError(source)
    out = Path(out_dir or OPEN_DATA_DIR)
    resumes_dir = out / "resumes"
    labels_out = Path(labels_path or EVAL_OPEN_LABELS_PATH)
    jds = load_engineering_jds(jds_dir)

    pdfs = sorted(source.rglob("*.pdf"))
    if limit is not None:
        pdfs = pdfs[:limit]
    seen: dict[str, str] = {}
    rows: list[ManifestRow] = []
    kept: list[tuple[ManifestRow, str]] = []
    for n, pdf in enumerate(pdfs, 1):
        row, text = process_pdf(pdf, resumes_dir, seen)
        rows.append(row)
        if row.status == "kept":
            kept.append((row, text))
        if progress and n % 250 == 0:
            print(f"  {n}/{len(pdfs)}", flush=True)

    cases = build_labels(kept, jds, sample=sample, seed=seed)
    labels_out.parent.mkdir(parents=True, exist_ok=True)
    labels_out.write_text(
        json.dumps([c.model_dump(mode="json") for c in cases], indent=2) + "\n",
        encoding="utf-8",
    )

    skipped = Counter(r.status for r in rows if r.status != "kept")
    redaction_counts: Counter = Counter()
    for r in rows:
        redaction_counts.update(r.redactions)
    report = ImportReport(
        source_dir=str(source),
        out_dir=str(out),
        labels_path=str(labels_out),
        scanned=len(rows),
        kept=len(kept),
        skipped=dict(skipped),
        redacted_files=sum(1 for r in rows if r.status == "kept" and r.pdf_source == "rendered"),
        redaction_counts=dict(redaction_counts),
        buckets=dict(Counter(r.bucket for r, _ in kept)),
        labels_written=len(cases),
        label_counts=dict(Counter(c.label.value for c in cases)),
        rows=rows,
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(
        json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8"
    )
    return report


def format_report(report: ImportReport) -> str:
    lines = [
        f"scanned={report.scanned} kept={report.kept} redacted={report.redacted_files}",
        f"skipped={report.skipped}",
        f"redactions={report.redaction_counts}",
        f"buckets={report.buckets}",
        f"labels_written={report.labels_written} label_counts={report.label_counts}",
        f"manifest={Path(report.out_dir) / 'manifest.json'}",
        f"labels={report.labels_path}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Redact and import the LiveCareer open resume PDFs."
    )
    parser.add_argument("--source", type=Path, required=True, help="<archive>/data/data")
    parser.add_argument("--out", type=Path, default=None, help=f"default {OPEN_DATA_DIR}")
    parser.add_argument("--labels", type=Path, default=None, help=f"default {EVAL_OPEN_LABELS_PATH}")
    parser.add_argument("--sample", type=int, default=150, help="cases to write; 0 = all kept")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--limit", type=int, default=None, help="scan only the first N PDFs")
    args = parser.parse_args(argv)
    report = import_open_resumes(
        args.source,
        out_dir=args.out,
        labels_path=args.labels,
        sample=args.sample,
        seed=args.seed,
        limit=args.limit,
        progress=True,
    )
    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
