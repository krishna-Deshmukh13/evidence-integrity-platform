"""Global assistant chatbot API routes: message exchange, history retrieval, and thread clearing."""
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import activity, assistant
from ..database import get_db
from ..deps import client_ip, current_user
from ..models import AssistantMessage, User

router = APIRouter(prefix="/api/assistant")


class AssistantChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    context: Optional[Dict[str, Any]] = None


def serialize_message(m: AssistantMessage) -> dict:
    try:
        results = json.loads(m.results) if m.results else []
    except Exception:
        results = []
    try:
        based_on = json.loads(m.based_on) if m.based_on else []
    except Exception:
        based_on = []

    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "source": m.source,
        "results": results,
        "based_on": based_on,
        "created_at": m.created_at,
    }


@router.get("/chat")
def get_chat_history(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Retrieve saved assistant chat thread for the current user."""
    messages = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.user_id == user.id)
        .order_by(AssistantMessage.id.asc())
        .limit(50)
        .all()
    )
    return [serialize_message(m) for m in messages]


@router.post("/chat")
def chat(body: AssistantChatIn, request: Request,
         db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Send a message to the assistant chatbot and receive contextual response with cards and sources."""
    ctx = body.context or {}
    case_id = ctx.get("case_id")
    evidence_id = ctx.get("evidence_id")

    # 1. Save user question to database
    user_msg = AssistantMessage(
        user_id=user.id,
        role="user",
        content=body.message.strip(),
        source="user",
        results="[]",
        based_on="[]"
    )
    db.add(user_msg)
    db.flush()

    # 2. Process message via intent routing & fact gathering
    reply_text, source, cards, based_on = assistant.process_message(db, user, body.message, ctx)

    # 3. Save assistant reply to database
    assistant_msg = AssistantMessage(
        user_id=user.id,
        role="assistant",
        content=reply_text,
        source=source,
        results=json.dumps(cards),
        based_on=json.dumps(based_on)
    )
    db.add(assistant_msg)
    db.commit()

    # 4. Activity log: record ONLY that a question was asked, NEVER the question text or answer text
    activity.log(
        db,
        activity.actor_name(user),
        "assistant_ask",
        "Asked assistant a question",
        case_id=case_id,
        evidence_id=evidence_id,
        ip=client_ip(request)
    )

    return serialize_message(assistant_msg)


@router.post("/clear")
@router.delete("/chat")
def clear_chat(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Clear private chat thread for the current user."""
    db.query(AssistantMessage).filter(AssistantMessage.user_id == user.id).delete()
    db.commit()
    return {"ok": True}
