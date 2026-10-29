
"""The three assignment tools: policy search, employee lookup, and ticket creation."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.ingestion import DATA_DIR, DB_DIR, COLLECTION_NAME, load_documents

FALLBACK = "I couldn't find this in the provided documents."


class PolicySearch:
    def __init__(
        self,
        data_dir: Path = DATA_DIR,
        db_dir: Path = DB_DIR,
    ):
        self.data_dir = data_dir
        self.db_dir = db_dir
        self._docs = None
        self._model = None
        self._collection = None

        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            client = chromadb.PersistentClient(path=str(db_dir))
            self._collection = client.get_collection(COLLECTION_NAME)
            self._model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
        except Exception:
            # Keep the lexical fallback available if vector search
            # or its model cannot be initialized.
            self._docs = load_documents(data_dir)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        stop = {
            "the", "a", "an", "is", "are", "of", "to", "for",
            "i", "my", "what", "how", "do", "can", "you", "me",
            "in", "on", "and", "it", "this", "that", "with",
            "who", "does", "if", "am", "into", "your", "be",
            "please", "should", "would", "could", "about",
            "tell", "give", "need", "want", "help",
        }
        return {
            token
            for token in re.findall(r"[a-z0-9]+", text.lower())
            if token not in stop
        }

    @staticmethod
    def _metadata_matches(
        metadata: dict[str, Any],
        country: str | None,
        doc_type: str | None,
    ) -> bool:
        """Apply country and document-type filters consistently."""
        if country and country.upper() in {"IN", "LK"}:
            doc_country = str(metadata.get("country", "")).upper()
            if doc_country not in {country.upper(), "BOTH"}:
                return False

        if doc_type:
            actual_type = str(metadata.get("doc_type", "")).lower()
            if actual_type != doc_type.lower():
                return False

        return True

    def search_policies(
        self,
        query: str,
        country: str | None = None,
        doc_type: str | None = None,
        k: int = 4,
    ) -> list[dict[str, Any]]:
        if not query or not query.strip() or k <= 0:
            return []

        country = country.upper() if country else None
        doc_type = doc_type.lower() if doc_type else None
        docs = self._docs

        # Retrieve additional vector candidates, then rerank them
        # using query relevance and the requested policy scope.
        if self._collection is not None and self._model is not None:
            filters = []

            if country in {"IN", "LK"}:
                filters.append({
                    "$or": [
                        {"country": country},
                        {"country": "both"},
                    ]
                })

            if doc_type:
                filters.append({"doc_type": doc_type})

            where = None
            if len(filters) == 1:
                where = filters[0]
            elif len(filters) > 1:
                where = {"$and": filters}

            vector = self._model.encode(
                [query],
                normalize_embeddings=True,
            ).tolist()[0]

            result = self._collection.query(
                query_embeddings=[vector],
                n_results=max(k * 3, 10),
                where=where,
                include=["documents", "metadatas", "distances"],
            )

            texts = result.get("documents", [[]])[0] or []
            metadatas = result.get("metadatas", [[]])[0] or []
            distances = result.get("distances", [[]])[0] or []

            docs = [
                {
                    "text": text,
                    "metadata": metadata or {},
                    "score": max(0.0, 1.0 - float(distance)),
                }
                for text, metadata, distance in zip(
                    texts, metadatas, distances
                )
            ]

        if docs is None:
            docs = load_documents(self.data_dir)

        query_tokens = self._tokens(query)
        query_lower = query.lower()

        # Expand common support requests with related troubleshooting terms.
        intent_groups = {
            "not working": {
                "troubleshoot", "repair", "fault", "issue",
                "damage", "report", "service", "support",
            },
            "broken": {"damage", "repair", "fault", "report"},
            "lost": {"loss", "theft", "police", "report"},
            "password": {"password", "reset", "login", "account"},
            "vpn": {"vpn", "network", "connection", "access"},
            "travel allowance": {
                "travel", "allowance", "daily", "per", "diem",
                "hotel", "transport", "reimbursement",
            },
            "leave policy": {
                "leave", "annual", "casual", "sick", "holiday",
                "eligibility", "policy",
            },
        }

        intent_terms: set[str] = set()
        for phrase, keywords in intent_groups.items():
            if phrase in query_lower:
                intent_terms.update(keywords)

        ranked: list[dict[str, Any]] = []

        for item in docs:
            metadata = item.get("metadata") or {}

            if not self._metadata_matches(
                metadata, country, doc_type
            ):
                continue

            text = str(item.get("text", ""))
            tokens = self._tokens(text)

            if not tokens:
                continue

            overlap = query_tokens & tokens
            coverage = len(overlap) / max(1, len(query_tokens))
            intent_overlap = len(intent_terms & tokens)

            # Chroma similarity and lexical fallback use different scales.
            # Use overlap/coverage as the shared reranking signals.
            base_score = float(item.get("score", 0.0))
            score = (
                0.35 * coverage
                + 0.15 * min(intent_overlap, 4) / 4
                + 0.10 * base_score
            )

            if overlap or intent_overlap:
                ranked.append({
                    "text": text,
                    "metadata": metadata,
                    "score": score,
                })

        ranked.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return ranked[:k]


def get_employee_profile(
    employee_id: str,
    data_dir: Path = DATA_DIR,
) -> dict[str, Any] | None:
    """Return an employee profile by ID, ignoring letter case."""
    path = data_dir / "employees.json"
    rows = json.loads(path.read_text(encoding="utf-8"))

    return next(
        (
            row for row in rows
            if row.get("employee_id", "").upper()
            == employee_id.strip().upper()
        ),
        None,
    )


def create_helpdesk_ticket(
    category: str,
    summary: str,
    data_dir: Path = DATA_DIR,
) -> str:
    """Create and persist a helpdesk ticket."""
    valid = {"hardware", "software", "access", "network", "other"}
    category = category.strip().lower()
    summary = summary.strip()

    if category not in valid:
        raise ValueError(
            "Invalid category. Choose one of: "
            + ", ".join(sorted(valid))
        )

    if not summary:
        raise ValueError("Ticket summary cannot be empty.")

    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "tickets.json"

    try:
        tickets = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(tickets, list):
            tickets = []
    except (FileNotFoundError, json.JSONDecodeError):
        tickets = []

    numeric_ids = [
        int(re.sub(r"\D", "", str(ticket.get("ticket_id", "0"))) or 0)
        for ticket in tickets
        if isinstance(ticket, dict)
    ]

    ticket_id = f"HD-{max(numeric_ids, default=1000) + 1}"

    tickets.append({
        "ticket_id": ticket_id,
        "category": category.title(),
        "summary": summary,
    })

    path.write_text(
        json.dumps(tickets, indent=2),
        encoding="utf-8",
    )

    return ticket_id
