import json, shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.agent import HelpdeskAgent
from app.main import app, sessions

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def copied_data(tmp_path):
    target = tmp_path / "data"
    shutil.copytree(ROOT / "data", target)
    return target


def test_single_document_answer_uses_current_leave_policy(copied_data):
    result = HelpdeskAgent(copied_data).run("How many days of annual leave can I carry forward?", employee_id="E1003")
    assert "15 days" in result["answer"]
    assert any("leave-policy-2026.md" in s for s in result["sources"])
    assert result["confidence_flag"] in {"high", "partial"}


def test_two_policy_question_searches_twice(copied_data):
    result = HelpdeskAgent(copied_data).run("I'm taking 3 days of leave for a business trip to Colombo. What approvals do I need?", employee_id="E1003")
    searches = [c for c in result["tool_calls"] if c["tool"] == "search_policies"]
    assert len(searches) == 2
    assert {c["input"]["doc_type"] for c in searches} == {"leave", "travel"}


def test_country_clarification_when_missing(copied_data):
    result = HelpdeskAgent(copied_data).run("What is my daily travel allowance?")
    assert "Which country" in result["answer"]
    assert result["confidence_flag"] == "partial"


def test_out_of_scope_fallback(copied_data):
    result = HelpdeskAgent(copied_data).run("What is the capital of Australia?")
    assert result["answer"] == "I couldn't find this in the provided documents."
    assert result["confidence_flag"] == "low"


def test_no_ticket_without_explicit_request(copied_data):
    before = json.loads((copied_data / "tickets.json").read_text())
    HelpdeskAgent(copied_data).run("My laptop screen is broken. What should I do?", employee_id="E1004")
    after = json.loads((copied_data / "tickets.json").read_text())
    assert after == before


def test_ticket_created_only_when_requested(copied_data):
    result = HelpdeskAgent(copied_data).run("My laptop screen is broken, please raise a ticket.", employee_id="E1004")
    assert result["ticket_id"]
    tickets = json.loads((copied_data / "tickets.json").read_text())
    assert tickets[-1]["ticket_id"] == result["ticket_id"]


def test_unknown_employee_reported(copied_data):
    result = HelpdeskAgent(copied_data).run("How do I reset my password?", employee_id="E9999")
    assert "couldn't find employee ID" in result["answer"]
    assert result["confidence_flag"] == "low"


def test_api_empty_message_rejected():
    client = TestClient(app)
    response = client.post("/chat", json={"message": "   ", "session_id": "empty-test"})
    assert response.status_code == 422
