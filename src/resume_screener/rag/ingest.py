"""Chunk competency markdown and persist a Chroma collection."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import chromadb

from resume_screener.config import Settings
from resume_screener.paths import COLLECTION_NAME, KB_DIR
from resume_screener.rag.embeddings import embedding_function_for

_META_RE = re.compile(r"^(role_family|source):\s*(.+)$", re.IGNORECASE)
_HEADING_RE = re.compile(r"^#\s+(.+)$")
_SECTION_RE = re.compile(r"^##\s+(.+)$")


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "chunk"


def parse_kb_file(path: Path) -> tuple[str, str, str, list[tuple[str, str]]]:
    """Return (title, role_family, source, [(section_title, body), ...])."""
    lines = path.read_text(encoding="utf-8").splitlines()
    title = path.stem.replace("-", " ").title()
    role_family = "engineering"
    source = "O*NET-inspired public competency summary"
    sections: list[tuple[str, list[str]]] = []
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal current, buf
        if current is None:
            return
        body = "\n".join(buf).strip()
        if body:
            sections.append((current, body.splitlines()))
        current, buf = None, []

    for raw in lines:
        line = raw.rstrip()
        heading = _HEADING_RE.match(line)
        if heading and current is None and not sections:
            title = heading.group(1).strip()
            continue
        meta = _META_RE.match(line)
        if meta and current is None:
            key, value = meta.group(1).lower(), meta.group(2).strip()
            if key == "role_family":
                role_family = value
            elif key == "source":
                source = value
            continue
        section = _SECTION_RE.match(line)
        if section:
            flush()
            current = section.group(1).strip()
            buf = []
            continue
        if current is not None:
            buf.append(line)

    flush()
    return title, role_family, source, [(name, "\n".join(body)) for name, body in sections]


def chunk_kb_dir(kb_dir: Path) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for path in sorted(kb_dir.glob("*.md")):
        title, role_family, source, sections = parse_kb_file(path)
        doc_slug = _slug(path.stem)
        for section_title, body in sections:
            chunk_id = f"{doc_slug}::{_slug(section_title)}"
            text = f"{title}\n{section_title}\n{body}".strip()
            chunks.append(
                {
                    "id": chunk_id,
                    "title": f"{title} / {section_title}",
                    "text": text,
                    "role_family": role_family,
                    "source": source,
                }
            )
    return chunks


def _client(chroma_dir: Path) -> chromadb.PersistentClient:
    chroma_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    return chromadb.PersistentClient(path=str(chroma_dir))


def ingest_competency_kb(
    kb_dir: Path | None = None,
    chroma_dir: Path | None = None,
    settings: Settings | None = None,
) -> int:
    """Rebuild the competency_benchmarks collection. Returns chunk count."""
    settings = settings or Settings()
    kb_dir = Path(kb_dir or KB_DIR)
    chroma_dir = Path(chroma_dir or settings.chroma_dir)

    chunks = chunk_kb_dir(kb_dir)
    if not chunks:
        raise FileNotFoundError(f"no competency markdown files in {kb_dir}")

    embed_fn = embedding_function_for(settings)
    client = _client(chroma_dir)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    texts = [c["text"] for c in chunks]
    embeddings = _embed_batched(embed_fn, texts)
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[
            {
                "role_family": c["role_family"],
                "source": c["source"],
                "title": c["title"],
            }
            for c in chunks
        ],
    )
    return len(chunks)


def _embed_batched(embed_fn, texts: list[str], batch_size: int = 64) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        vectors.extend(embed_fn(texts[start : start + batch_size]))
    return vectors


def query_competency(
    query: str,
    k: int = 5,
    chroma_dir: Path | None = None,
    settings: Settings | None = None,
    role_family: str | None = None,
) -> list[dict]:
    settings = settings or Settings()
    chroma_dir = Path(chroma_dir or settings.chroma_dir)
    embed_fn = embedding_function_for(settings)
    client = _client(chroma_dir)
    collection = client.get_collection(name=COLLECTION_NAME)
    query_embedding = _embed_batched(embed_fn, [query])[0]
    available = max(collection.count(), 1)
    fetch = min(max(k, 1) * (3 if role_family else 1), available)
    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": fetch,
    }
    if role_family:
        kwargs["where"] = {"role_family": role_family}
    result = collection.query(**kwargs)
    hits: list[dict] = []
    ids = (result.get("ids") or [[]])[0]
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]
    for i, chunk_id in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        hits.append(
            {
                "id": chunk_id,
                "title": (meta or {}).get("title", ""),
                "text": docs[i] if i < len(docs) else "",
                "role_family": (meta or {}).get("role_family", ""),
                "source": (meta or {}).get("source", ""),
                "distance": dists[i] if i < len(dists) else None,
            }
        )
    if role_family:
        hits = [h for h in hits if h.get("role_family") == role_family]
    return hits[:k]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest competency KB into Chroma")
    parser.add_argument("--kb-dir", type=Path, default=None)
    parser.add_argument("--chroma-dir", type=Path, default=None)
    parser.add_argument("--query", default="backend software engineer")
    args = parser.parse_args(argv)

    count = ingest_competency_kb(kb_dir=args.kb_dir, chroma_dir=args.chroma_dir)
    settings = Settings()
    chroma_dir = Path(args.chroma_dir or settings.chroma_dir)
    print(f"ingested {count} chunks into {chroma_dir / COLLECTION_NAME}")
    hits = query_competency(
        args.query, k=settings.top_k, chroma_dir=chroma_dir, settings=settings
    )
    print(f"smoke query {args.query!r} -> {len(hits)} chunk(s)")
    for hit in hits:
        print(f"  {hit['id']}\t{hit['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
