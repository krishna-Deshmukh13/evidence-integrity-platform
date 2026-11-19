"""Ask: a private chat per user about a single file."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import activity, chat
from ..database import get_db
from ..deps import client_ip, current_user, has_case_access, verify_evidence_access
from ..models import ChatMessage, Evidence, User

router = APIRouter(prefix="/api")


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


def _mine(db, evidence_id, user):
    return (db.query(ChatMessage).filter(ChatMessage.evidence_id == evidence_id, ChatMessage.user_id == user.id)
            .order_by(ChatMessage.id))


def _row(m):
    return {"id": m.id, "role": m.role, "content": m.content, "source": m.source, "created_at": m.created_at}


@router.get("/evidence/{evidence_id}/chat")
def get_chat(evidence_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ev = db.get(Evidence, evidence_id)
    if not ev:
        raise HTTPException(404, "Evidence not found")
    if not has_case_access(db, user, ev.case_id):
        return []
    return [_row(m) for m in _mine(db, evidence_id, user)]


@router.post("/evidence/{evidence_id}/chat")
def ask(evidence_id: int, body: Question, request: Request, db: Session = Depends(get_db),
        user: User = Depends(current_user)):
    ev = verify_evidence_access(db, user, evidence_id)
    history = _mine(db, evidence_id, user).all()
    db.add(ChatMessage(evidence_id=ev.id, user_id=user.id, role="user", content=body.question))
    text, source = chat.answer(ev, body.question, history)
    reply = ChatMessage(evidence_id=ev.id, user_id=user.id, role="assistant", content=text, source=source)
    db.add(reply)
    db.commit()
    activity.log(db, activity.actor_name(user), "ask", f"Asked about evidence {ev.filename}",  # question text not logged
                 ev.case_id, ev.id, client_ip(request))
    return _row(reply)


@router.delete("/evidence/{evidence_id}/chat")
def clear_chat(evidence_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    verify_evidence_access(db, user, evidence_id)
    db.query(ChatMessage).filter(ChatMessage.evidence_id == evidence_id,
                                 ChatMessage.user_id == user.id).delete()
    db.commit()
    return {"ok": True}
