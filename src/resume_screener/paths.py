"""Repository paths for eval data and the competency KB."""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
REPO_ROOT = SRC_DIR.parent

EVAL_DIR = REPO_ROOT / "data" / "eval"
EVAL_LABELS_PATH = EVAL_DIR / "labels.json"
EVAL_RESUMES_DIR = EVAL_DIR / "resumes"
EVAL_JDS_DIR = EVAL_DIR / "jds"
EVAL_OPEN_LABELS_PATH = EVAL_DIR / "labels_open.json"
KB_DIR = REPO_ROOT / "data" / "competency_kb"

# Open-data resumes (LiveCareer set) live outside git; see .gitignore.
EXTERNAL_DIR = REPO_ROOT / "data" / "external"
OPEN_DATA_DIR = EXTERNAL_DIR / "livecareer"

COLLECTION_NAME = "competency_benchmarks"

CHECKPOINT_PATH = REPO_ROOT / "data" / "checkpoints.db"
OVERRIDES_PATH = REPO_ROOT / "data" / "overrides.jsonl"
