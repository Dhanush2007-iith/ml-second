from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..gemini_service import contains_crisis_language

router = APIRouter(prefix="/api/peer", tags=["Peer Support"])

BLOCKED_TERMS = ["kill", "hate speech placeholder"]  # simple automatic moderation heuristic


@router.get("/posts", response_model=list[schemas.ForumPostOut])
def list_posts(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return (
        db.query(models.ForumPost)
        .filter(models.ForumPost.is_hidden == False)  # noqa: E712
        .order_by(models.ForumPost.created_at.desc())
        .all()
    )


@router.post("/posts", response_model=schemas.ForumPostOut, status_code=201)
def create_post(
    payload: schemas.ForumPostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    auto_hidden = any(term in payload.content.lower() for term in BLOCKED_TERMS)
    post = models.ForumPost(
        user_id=current_user.id,
        author_display=current_user.anonymous_id,
        content=payload.content,
        tag=payload.tag,
        is_hidden=auto_hidden,
    )
    db.add(post)

    if contains_crisis_language(payload.content):
        volunteers = db.query(models.User).filter(models.User.role == models.RoleEnum.volunteer).all()
        for v in volunteers:
            db.add(models.Notification(
                user_id=v.id, type="alert",
                message=f"Crisis language detected in a peer support post by {current_user.anonymous_id}.",
            ))

    db.commit()
    db.refresh(post)
    return post


@router.post("/posts/{post_id}/reply", response_model=schemas.ForumPostOut)
def reply_to_post(post_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    post = db.query(models.ForumPost).filter(models.ForumPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.reply_count += 1
    db.commit()
    db.refresh(post)
    return post


@router.post("/posts/{post_id}/report", response_model=schemas.ForumPostOut)
def report_post(post_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    post = db.query(models.ForumPost).filter(models.ForumPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.report_count += 1
    if post.report_count >= 3:
        post.is_hidden = True
    db.commit()
    db.refresh(post)
    return post
