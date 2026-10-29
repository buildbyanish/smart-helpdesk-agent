
"""Grounded tool-routing loop for the Corvanta helpdesk assessment."""
from __future__ import annotations

import re
from typing import Any

from app.tools import (
    PolicySearch,
    get_employee_profile,
    create_helpdesk_ticket,
    FALLBACK,
)

RELEVANCE_THRESHOLD = 0.30
LEXICAL_THRESHOLD = 0.08
MAX_TOOL_CALLS = 5


def _wants_ticket(message: str) -> bool:
    return bool(
        re.search(
            r"\b(raise|create|open|log|submit)\b.{0,35}"
            r"\b(ticket|incident|helpdesk request)\b|"
            r"\b(ticket|incident)\b.{0,25}"
            r"\b(please|for me|create|raise|open)\b",
            message,
            re.I,
        )
    )


def _category(message: str) -> str:
    m = message.lower()

    if any(w in m for w in ["laptop", "screen", "keyboard", "device", "hardware"]):
        return "hardware"
    if any(w in m for w in ["vpn", "wifi", "network", "internet"]):
        return "network"
    if any(w in m for w in ["password", "login", "access", "account"]):
        return "access"
    if any(w in m for w in ["software", "application", "app"]):
        return "software"

    return "other"


def _is_country_dependent(message: str) -> bool:
    m = message.lower()
    return any(
        word in m
        for word in [
            "travel", "trip", "allowance", "hotel", "flight",
            "colombo", "bengaluru", "bangalore", "carry forward",
            "leave", "approv", "currency", "daily rate",
        ]
    )


def _doc_type(message: str) -> str | None:
    m = message.lower()

    if any(
        word in m
        for word in [
            "leave", "carry forward", "annual leave",
            "casual leave", "sick leave", "business trip",
        ]
    ):
        return "leave"

    if any(
        word in m
        for word in [
            "laptop", "screen", "device", "refresh",
            "replacement", "damage", "costs", "cost",
        ]
    ):
        return "laptop"

    if any(
        word in m
        for word in [
            "vpn", "password", "login", "ticket",
            "reset", "mfa", "helpdesk",
        ]
    ):
        return "it-helpdesk"

    if any(
        word in m
        for word in [
            "travel", "hotel", "flight", "allowance",
            "per diem", "trip",
        ]
    ):
        return "travel"

    return None


def _format_source(hit: dict[str, Any]) -> str:
    metadata = hit.get("metadata", {})
    return (
        f"{metadata.get('source', 'Unknown source')} - "
        f"{metadata.get('page_or_section', 'Unknown section')}"
    )


def _grounded_answer(
    message: str,
    hits: list[dict[str, Any]],
) -> str:
    """Choose concise, relevant sentences and preserve source citations."""
    if not hits:
        return FALLBACK

    query = message.lower()

    # Select an answer intent so unrelated policy sections are not returned.
    if any(word in query for word in ("not working", "broken", "malfunction")):
        intent = "troubleshooting"
        relevant_terms = {
            "troubleshoot", "repair", "fault", "issue", "support",
            "helpdesk", "service", "contact", "report", "technical",
            "restart", "check", "working", "problem",
        }
    elif any(word in query for word in ("lost", "stolen", "theft")):
        intent = "loss"
        relevant_terms = {"loss", "lost", "theft", "stolen", "police", "report"}
    elif any(word in query for word in ("replacement", "refresh", "replace")):
        intent = "replacement"
        relevant_terms = {"replacement", "refresh", "replace", "eligible", "years"}
    elif any(word in query for word in ("leave", "carry forward", "annual leave")):
        intent = "leave"
        relevant_terms = {"leave", "annual", "casual", "sick", "holiday", "carry", "forward"}
    elif any(word in query for word in ("travel", "allowance", "hotel", "flight", "per diem")):
        intent = "travel"
        relevant_terms = {"travel", "allowance", "hotel", "flight", "daily", "per", "diem", "reimbursement"}
    elif any(word in query for word in ("password", "login", "vpn", "mfa")):
        intent = "access"
        relevant_terms = {"password", "login", "vpn", "mfa", "reset", "access", "account"}
    else:
        intent = "general"
        relevant_terms = {
            word for word in re.findall(r"[a-z0-9]+", query)
            if len(word) > 2
        }

    ranked = []

    for hit in hits:
        text = re.sub(r"\s+", " ", hit.get("text", "")).strip()
        if not text:
            continue

        passage = text.lower()
        passage_words = set(re.findall(r"[a-z0-9]+", passage))
        overlap = len(relevant_terms & passage_words)

        if overlap == 0:
            continue

        score = overlap + float(hit.get("score", 0.0))

        # For troubleshooting, prioritize actionable support instructions
        # and avoid charging, loss, and refresh sections unless asked.
        if intent == "troubleshooting":
            if any(term in passage for term in (
                "helpdesk", "service desk", "support", "contact",
                "troubleshoot", "repair", "technical",
            )):
                score += 3

            if any(term in passage for term in (
                "lkr", "inr", "salary deduction", "depreciated value",
                "refresh cycle", "new joiners", "replacement request",
                "police report",
            )):
                score -= 5

        if intent == "replacement" and any(
            term in passage for term in ("replacement", "refresh", "eligible")
        ):
            score += 2

        ranked.append((score, hit, text))

    ranked.sort(key=lambda item: item[0], reverse=True)

    if intent == "leave":
        current = [
            item for item in ranked
            if item[1].get("metadata", {}).get("source")
            == "leave-policy-2026.md"
        ]
        old = [
            item for item in ranked
            if item[1].get("metadata", {}).get("source")
            == "leave-policy-2025.pdf"
        ]

        if current:
            ranked = current + [
                item for item in ranked
                if item not in current and item not in old
            ]
        elif old:
            ranked = [item for item in ranked if item not in old]

    snippets = []
    seen = set()

    for _, hit, text in ranked:
        if text in seen:
            continue
        seen.add(text)

        # Extract sentences that match the user's intent, not arbitrary
        # first characters from a large retrieved passage.
        sentences = re.split(r"(?<=[.!?])\s+", text)
        selected = []

        for sentence in sentences:
            sentence_lower = sentence.lower()
            words = set(re.findall(r"[a-z0-9]+", sentence_lower))
            matches = len(words & relevant_terms)

            if matches == 0:
                continue

            if intent == "troubleshooting" and any(
                term in sentence_lower for term in (
                    "lkr", "inr", "salary deduction", "depreciated value",
                    "refresh cycle", "new joiners", "replacement request",
                    "police report",
                )
            ):
                continue

            selected.append(sentence.strip())

            if len(selected) >= 3:
                break

        if not selected:
            continue

        excerpt = " ".join(selected)
        if len(excerpt) > 600:
            excerpt = excerpt[:597].rsplit(" ", 1)[0] + "..."

        snippets.append(f"{excerpt} [{_format_source(hit)}]")

        if len(snippets) >= 2:
            break

    if not snippets:
        return FALLBACK

    if intent == "leave":
        prefix = "According to the current Leave Policy 2026:"
    elif intent == "troubleshooting":
        prefix = "For your laptop issue:"
    else:
        prefix = "Relevant policy information:"

    return prefix + "\n\n" + "\n\n".join(snippets)


class HelpdeskAgent:
    def __init__(self, data_dir=None):
        self.searcher = (
            PolicySearch(data_dir=data_dir)
            if data_dir
            else PolicySearch()
        )
        self.data_dir = data_dir

    def run(
        self,
        message: str,
        employee_id: str | None = None,
        session_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        if not message or not message.strip():
            raise ValueError("Message must not be empty.")

        history = session_history or []
        original = message.strip()

        if history and history[-1].get("awaiting_country"):
            if re.search(r"\b(india|indian)\b", original, re.I):
                clarified_country = "IN"
            elif re.search(r"\b(sri lanka|sri lankan|colombo)\b", original, re.I):
                clarified_country = "LK"
            else:
                clarified_country = None

            if clarified_country:
                original = (
                    history[-1]["original_question"]
                    + f" (country: {clarified_country})"
                )

        calls: list[dict[str, Any]] = []
        ticket_id = None
        country = None

        if employee_id:
            profile = (
                get_employee_profile(employee_id, self.data_dir)
                if self.data_dir
                else get_employee_profile(employee_id)
            )

            calls.append({
                "tool": "get_employee_profile",
                "input": {"employee_id": employee_id},
            })

            if not profile:
                return {
                    "answer": (
                        f"I couldn't find employee ID {employee_id} "
                        "in the employee directory."
                    ),
                    "sources": [],
                    "confidence_flag": "low",
                    "tool_calls": calls,
                    "ticket_id": None,
                    "awaiting_country": False,
                }

            country = profile["country"]

        country_match = re.search(
            r"\b(Sri Lanka|Sri Lankan|Colombo|India|Indian|Bengaluru|Bangalore)\b",
            original,
            re.I,
        )

        if country_match:
            country = (
                "LK"
                if country_match.group(1).lower()
                in {"sri lanka", "sri lankan", "colombo"}
                else "IN"
            )

        if _is_country_dependent(original) and not country:
            return {
                "answer": (
                    "Which country are you based in—India or Sri Lanka? "
                    "I need this to check the correct policy."
                ),
                "sources": [],
                "confidence_flag": "partial",
                "tool_calls": calls,
                "ticket_id": None,
                "awaiting_country": True,
                "original_question": message,
            }

        if "business" in original.lower() and any(
            word in original.lower()
            for word in ["trip", "travel", "colombo"]
        ):
            queries = [(original, "leave"), (original, "travel")]
        else:
            queries = [(original, _doc_type(original))]

        all_hits: list[dict[str, Any]] = []

        for query, doc_type in queries:
            if len(calls) >= MAX_TOOL_CALLS:
                break

            hits = self.searcher.search_policies(
                query,
                country=country,
                doc_type=doc_type,
                k=4,
            )

            calls.append({
                "tool": "search_policies",
                "input": {
                    "query": query,
                    "country": country,
                    "doc_type": doc_type,
                },
            })
            all_hits.extend(hits)

        if _wants_ticket(message) and len(calls) < MAX_TOOL_CALLS:
            category = _category(message)
            ticket_id = (
                create_helpdesk_ticket(category, message, self.data_dir)
                if self.data_dir
                else create_helpdesk_ticket(category, message)
            )

            calls.append({
                "tool": "create_helpdesk_ticket",
                "input": {"category": category, "summary": message},
            })

        if not all_hits:
            return {
                "answer": FALLBACK,
                "sources": [],
                "confidence_flag": "low",
                "tool_calls": calls,
                "ticket_id": ticket_id,
                "awaiting_country": False,
            }

        threshold = (
            RELEVANCE_THRESHOLD
            if self.searcher._collection is not None
            else LEXICAL_THRESHOLD
        )
        relevant = [
            hit for hit in all_hits
            if hit.get("score", 0.0) >= threshold
        ]

        if not relevant:
            return {
                "answer": FALLBACK,
                "sources": [],
                "confidence_flag": "low",
                "tool_calls": calls,
                "ticket_id": ticket_id,
                "awaiting_country": False,
            }

        if "leave" in original.lower() or "carry forward" in original.lower():
            current = [
                hit for hit in relevant
                if hit["metadata"].get("source") == "leave-policy-2026.md"
            ]
            old = [
                hit for hit in relevant
                if hit["metadata"].get("source") == "leave-policy-2025.pdf"
            ]

            if current:
                relevant = current + [
                    hit for hit in relevant
                    if hit not in current and hit not in old
                ]
            elif old:
                relevant = [hit for hit in relevant if hit not in old]

        answer = _grounded_answer(original, relevant)

        if ticket_id:
            answer += f"\n\nHelpdesk ticket created: {ticket_id}."

        sources = list(dict.fromkeys(
            _format_source(hit) for hit in relevant[:4]
        ))

        confidence_flag = (
            "high" if relevant and answer != FALLBACK else "low"
        )

        if len(queries) > 1 and len({
            hit["metadata"]["doc_type"] for hit in relevant
        }) < 2:
            confidence_flag = "partial"

        return {
            "answer": answer,
            "sources": sources,
            "confidence_flag": confidence_flag,
            "tool_calls": calls[:MAX_TOOL_CALLS],
            "ticket_id": ticket_id,
            "awaiting_country": False,
        }
