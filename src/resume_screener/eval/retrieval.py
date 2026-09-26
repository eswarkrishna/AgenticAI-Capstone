"""Check that each labelled JD retrieves its competency cluster."""

from __future__ import annotations

from typing import Any

from resume_screener.config import Settings
from resume_screener.eval.load import load_eval_cases, resolve_eval_path
from resume_screener.rag.retriever import retrieve_competency_benchmarks
from resume_screener.schemas import EvalCase, RoleFamily

# KB filename stems that count as a hit. Most JDs have one cluster.
# eng-pf-01 names both a backend occupation and distributed systems.
EXPECTED_CLUSTER: dict[str, tuple[str, ...]] = {
    "eng-sm-01": ("backend-software-engineer",),
    "eng-sm-02": ("data-engineer",),
    "eng-sm-03": ("frontend-engineer",),
    "eng-sm-04": ("devops-sre",),
    "eng-pf-01": ("distributed-systems", "backend-software-engineer", "python-backend"),
    "eng-pf-02": ("backend-software-engineer",),
    "eng-pf-03": ("distributed-systems",),
    "eng-nr-01": ("backend-software-engineer",),
    "eng-nr-02": ("backend-software-engineer",),
    "eng-nr-03": ("backend-software-engineer",),
    "pd-sm-01": ("b2b-saas-pm",),
    "pd-sm-02": ("product-designer",),
    "pd-sm-03": ("ux-researcher",),
    "pd-pf-01": ("product-manager",),
    "pd-pf-02": ("product-designer",),
    "pd-pf-03": ("product-manager",),
    "pd-pf-04": ("ux-researcher",),
    "pd-nr-01": ("product-designer",),
    "pd-nr-02": ("product-manager",),
    "pd-nr-03": ("ux-researcher",),
    "ops-sm-01": ("supply-chain-manager",),
    "ops-sm-02": ("logistics-coordinator",),
    "ops-sm-03": ("procurement-specialist",),
    "ops-pf-01": ("operations-manager",),
    "ops-pf-02": ("inventory-planning",),
    "ops-pf-03": ("warehouse-operations",),
    "ops-nr-01": ("warehouse-operations",),
    "ops-nr-02": ("logistics-coordinator",),
    "ops-nr-03": ("procurement-specialist",),
    "ops-nr-04": ("supply-chain-manager",),
}


def query_from_jd(jd_text: str) -> str:
    """Title plus must-have bullets. This is what a recruiter's JD actually says."""
    parts: list[str] = []
    in_must = False
    for raw in jd_text.splitlines():
        line = raw.strip()
        if line.startswith("# ") and not parts:
            parts.append(line[2:].strip())
            continue
        if line.lower().startswith("## must"):
            in_must = True
            continue
        if line.startswith("##"):
            in_must = False
            continue
        if in_must and line.startswith("- "):
            parts.append(line[2:].strip())
    return " ".join(parts)


def _hit(case: EvalCase, settings: Settings, k: int) -> dict[str, Any]:
    jd_text = resolve_eval_path(case.jd_path).read_text(encoding="utf-8")
    query = query_from_jd(jd_text)
    family = case.role_family if isinstance(case.role_family, RoleFamily) else RoleFamily(case.role_family)
    chunks = retrieve_competency_benchmarks(
        family,
        query,
        k=k,
        settings=settings,
        chroma_dir=settings.chroma_dir,
    )
    expected = EXPECTED_CLUSTER[case.id]
    ids = [chunk.id for chunk in chunks]
    return {
        "id": case.id,
        "expected": list(expected),
        "hit": any(
            chunk_id.startswith(f"{stem}::") for chunk_id in ids for stem in expected
        ),
        "retrieved": ids,
    }


def evaluate_retrieval(
    settings: Settings | None = None,
    *,
    k: int = 5,
) -> dict[str, Any]:
    """For each JD, whether the expected competency file is in the top-k."""
    settings = settings or Settings()
    try:
        rows = [_hit(case, settings, k) for case in load_eval_cases()]
    except Exception as exc:  # noqa: BLE001 — report the failure, do not hide it
        return {
            "available": False,
            "k": k,
            "hit_rate": None,
            "hits": 0,
            "n": 0,
            "misses": [],
            "error": str(exc),
        }
    hits = sum(1 for row in rows if row["hit"])
    misses = [row["id"] for row in rows if not row["hit"]]
    return {
        "available": True,
        "k": k,
        "hit_rate": hits / len(rows) if rows else 0.0,
        "hits": hits,
        "n": len(rows),
        "misses": misses,
        "error": None,
    }
