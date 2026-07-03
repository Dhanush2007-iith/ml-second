import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..gemini_service import get_ai_response, CRISIS_LINES

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])


@router.post("/message", response_model=schemas.ChatReply)
def send_message(
    payload: schemas.ChatSend,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session_id = payload.session_id or uuid.uuid4().hex

    prior = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == current_user.id, models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in prior]

    user_msg = models.ChatMessage(
        user_id=current_user.id, session_id=session_id, role="user", content=payload.message
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    reply_text, crisis = get_ai_response(payload.message, history)

    ai_msg = models.ChatMessage(
        user_id=current_user.id,
        session_id=session_id,
        role="ai",
        content=reply_text,
        crisis_flag=crisis,
    )
    db.add(ai_msg)

    if crisis:
        counsellors = db.query(models.User).filter(models.User.role == models.RoleEnum.counsellor).all()
        for c in counsellors:
            db.add(models.Notification(
                user_id=c.id,
                type="alert",
                message=f"Crisis language detected in {current_user.anonymous_id}'s AI chat — immediate outreach recommended.",
            ))

    db.commit()

    full_history = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == current_user.id, models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )

    return schemas.ChatReply(
        session_id=session_id,
        reply=reply_text,
        crisis=crisis,
        crisis_resources=CRISIS_LINES if crisis else None,
        history=full_history,
    )


@router.get("/history", response_model=list[schemas.ChatMessageOut])
def get_history(
    session_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.ChatMessage).filter(models.ChatMessage.user_id == current_user.id)
    if session_id:
        q = q.filter(models.ChatMessage.session_id == session_id)
    return q.order_by(models.ChatMessage.created_at.asc()).all()


@router.get("/crisis-resources")
def crisis_resources():
    return {"resources": CRISIS_LINES}
