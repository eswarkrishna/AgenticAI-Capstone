"""Role-family-filtered competency retriever, also exposed as a LangChain tool."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from resume_screener.config import Settings
from resume_screener.rag.ingest import query_competency
from resume_screener.schemas import RetrievedChunk, RoleFamily


def _distance_to_score(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return max(0.0, min(1.0, 1.0 - float(distance)))


def retrieve_competency_benchmarks(
    role_family: RoleFamily,
    query: str,
    k: int = 5,
    *,
    chroma_dir: Path | None = None,
    settings: Settings | None = None,
) -> list[RetrievedChunk]:
    """Return same-family competency chunks for `query`."""
    settings = settings or Settings()
    k = k or settings.top_k
    family = role_family.value if isinstance(role_family, RoleFamily) else str(role_family)
    hits = query_competency(
        query,
        k=k,
        chroma_dir=chroma_dir,
        settings=settings,
        role_family=family,
    )
    chunks: list[RetrievedChunk] = []
    for hit in hits:
        try:
            family_value = RoleFamily(hit["role_family"])
        except ValueError:
            continue
        if family_value.value != family:
            continue
        chunks.append(
            RetrievedChunk(
                id=str(hit["id"]),
                title=str(hit.get("title") or ""),
                text=str(hit.get("text") or ""),
                role_family=family_value,
                score=_distance_to_score(hit.get("distance")),
            )
        )
    return chunks[:k]


class RetrieveCompetencyArgs(BaseModel):
    role_family: RoleFamily = Field(description="engineering | product_design | operations")
    query: str = Field(description="Natural-language query, usually role title plus must-have skills")
    k: int = Field(default=5, ge=1, description="Number of chunks to return")


def _tool_retrieve(role_family: RoleFamily, query: str, k: int = 5) -> list[dict]:
    chunks = retrieve_competency_benchmarks(role_family, query, k=k)
    return [chunk.model_dump(mode="json") for chunk in chunks]


retrieve_competency_benchmarks_tool = StructuredTool.from_function(
    name="retrieve_competency_benchmarks",
    description=(
        "Retrieve O*NET-inspired competency benchmark chunks for a role family. "
        "Always pass role_family so results stay in-family."
    ),
    func=_tool_retrieve,
    args_schema=RetrieveCompetencyArgs,
)
