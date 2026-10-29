from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.agent import HelpdeskAgent

app = FastAPI(title="Corvanta HR & IT Helpdesk Agent", version="1.0.0")
agent = HelpdeskAgent()
sessions: dict[str, list[dict]] = defaultdict(list)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    employee_id: Optional[str] = None
    session_id: str = "default"

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence_flag: str
    tool_calls: list[dict]
    ticket_id: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be empty")
    try:
        history = sessions[body.session_id]
        result = agent.run(message, body.employee_id, history)
        if result.pop("awaiting_country", False):
            history.append({"awaiting_country": True, "original_question": result.pop("original_question", message)})
        else:
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": result["answer"]})
            # Keep bounded session history.
            del history[:-12]
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        # Do not expose stack traces or internal paths to callers.
        raise HTTPException(status_code=500, detail="The helpdesk agent encountered an internal error. Please try again.")
