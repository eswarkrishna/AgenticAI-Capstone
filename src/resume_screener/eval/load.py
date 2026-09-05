"""Load labelled resume–JD eval cases."""

from __future__ import annotations

import json
from pathlib import Path

from resume_screener.paths import EVAL_LABELS_PATH, REPO_ROOT
from resume_screener.schemas import EvalCase


def load_eval_cases(labels_path: Path | None = None) -> list[EvalCase]:
    path = Path(labels_path or EVAL_LABELS_PATH)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path} must be a JSON array")
    return [EvalCase.model_validate(item) for item in raw]


def resolve_eval_path(relative: str) -> Path:
    return REPO_ROOT / relative
