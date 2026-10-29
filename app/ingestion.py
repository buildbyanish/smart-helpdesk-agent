
"""Load policy documents and create citation-aware, metadata-filtered chunks."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_DIR = Path(__file__).resolve().parents[1] / ".chroma"
COLLECTION_NAME = "corvanta_policy_chunks"

# Smaller chunks reduce the chance of mixing unrelated policy topics.
CHUNK_WORDS = 120
OVERLAP_WORDS = 20


def _pdf_pages(path: Path) -> list[tuple[str, int]]:
    import fitz

    with fitz.open(path) as doc:
        return [
            (page.get_text("text"), i + 1)
            for i, page in enumerate(doc)
        ]


def _markdown_sections(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?m)(?=^#{1,4}\s+)", text)
    output = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        heading = next(
            (
                line.lstrip("# ").strip()
                for line in part.splitlines()
                if line.startswith("#")
            ),
            "Document overview",
        )
        output.append((part, heading))

    return output


def _split_words(
    text: str,
    size: int = CHUNK_WORDS,
    overlap: int = OVERLAP_WORDS,
) -> list[str]:
    """Split by paragraphs first, then sentence boundaries where possible."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    if len(text.split()) <= size:
        return [text]

    paragraphs = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    chunks = []
    current = []

    for paragraph in paragraphs:
        words = paragraph.split()

        if not words:
            continue

        if len(words) > size:
            if current:
                chunks.append(" ".join(current))
                current = []

            start = 0
            while start < len(words):
                end = min(start + size, len(words))
                chunks.append(" ".join(words[start:end]))

                if end == len(words):
                    break

                start = end - overlap
            continue

        if current and len(current) + len(words) > size:
            chunks.append(" ".join(current))

            # Retain a small overlap for context.
            current = current[-overlap:] if overlap else []

        current.extend(words)

    if current:
        chunks.append(" ".join(current))

    return chunks


def _metadata(
    path: Path,
    page_or_section: str,
    text: str = "",
) -> dict[str, Any]:
    name = path.name.lower()
    content = text.lower()

    if "india" in name:
        country = "IN"
    elif "sri-lanka" in name:
        country = "LK"
    else:
        # Use passage-level country metadata for mixed-country documents.
        mentions_india = bool(
            re.search(r"\b(india|indian|inr|₹)\b", content)
        )
        mentions_sri_lanka = bool(
            re.search(r"\b(sri lanka|sri lankan|colombo|lkr)\b", content)
        )

        if mentions_india and mentions_sri_lanka:
            country = "both"
        elif mentions_india:
            country = "IN"
        elif mentions_sri_lanka:
            country = "LK"
        else:
            country = "both"

    if "travel" in name:
        doc_type = "travel"
    elif "leave-policy" in name:
        doc_type = "leave"
    elif "laptop" in name:
        doc_type = "laptop"
    else:
        doc_type = "it-helpdesk"

    version = (
        "2026" if "2026" in name
        else "2025" if "2025" in name
        else "1"
    )

    effective = (
        "2026-01-01" if version == "2026"
        else "2025-01-01" if version == "2025"
        else "unknown"
    )

    return {
        "source": path.name,
        "page_or_section": page_or_section,
        "country": country,
        "doc_type": doc_type,
        "version": version,
        "effective_date": effective,
    }


def load_documents(
    data_dir: Path = DATA_DIR,
) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []

    if not data_dir.exists():
        return docs

    for path in sorted(data_dir.iterdir()):
        if path.suffix.lower() == ".pdf":
            for text, page in _pdf_pages(path):
                for index, chunk in enumerate(_split_words(text)):
                    metadata = _metadata(
                        path,
                        f"Page {page}",
                        chunk,
                    )
                    chunk_id = hashlib.sha256(
                        f"{path.name}|{page}|{index}|{chunk}".encode()
                    ).hexdigest()

                    docs.append({
                        "id": chunk_id,
                        "text": chunk,
                        "metadata": metadata,
                    })

        elif path.suffix.lower() == ".md":
            for text, section in _markdown_sections(path):
                for index, chunk in enumerate(_split_words(text)):
                    metadata = _metadata(path, section, chunk)
                    chunk_id = hashlib.sha256(
                        f"{path.name}|{section}|{index}|{chunk}".encode()
                    ).hexdigest()

                    docs.append({
                        "id": chunk_id,
                        "text": chunk,
                        "metadata": metadata,
                    })

    return docs


def index_documents(
    data_dir: Path = DATA_DIR,
    persist_dir: Path = DB_DIR,
) -> int:
    docs = load_documents(data_dir)

    try:
        import chromadb
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        client = chromadb.PersistentClient(path=str(persist_dir))

        # Rebuild the collection so old chunks and old metadata do not remain.
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        collection = client.get_or_create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        for start in range(0, len(docs), 64):
            batch = docs[start:start + 64]
            vectors = model.encode(
                [item["text"] for item in batch],
                normalize_embeddings=True,
            ).tolist()

            collection.upsert(
                ids=[item["id"] for item in batch],
                documents=[item["text"] for item in batch],
                metadatas=[item["metadata"] for item in batch],
                embeddings=vectors,
            )

        return len(docs)

    except ImportError:
        persist_dir.mkdir(parents=True, exist_ok=True)
        (persist_dir / "chunks.json").write_text(
            json.dumps(docs, indent=2),
            encoding="utf-8",
        )
        return len(docs)


if __name__ == "__main__":
    count = index_documents()
    print(f"Indexed {count} chunks.")
