from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api/resources", tags=["Resource Hub"])


@router.get("", response_model=list[schemas.ResourceOut])
def list_resources(
    category: str | None = None,
    language: str = "English",
    search: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Resource).filter(models.Resource.language == language)
    if category and category != "All":
        q = q.filter(models.Resource.category == category)
    if search:
        q = q.filter(models.Resource.title.ilike(f"%{search}%"))
    return q.order_by(models.Resource.created_at.desc()).all()


@router.get("/categories")
def categories(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    rows = db.query(models.Resource.category).distinct().all()
    return {"categories": ["All"] + sorted({r[0] for r in rows})}


@router.get("/languages")
def languages(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    rows = db.query(models.Resource.language).distinct().all()
    langs = sorted({r[0] for r in rows})
    return {"languages": langs or ["English"]}


@router.post("", response_model=schemas.ResourceOut, status_code=201)
def create_resource(
    payload: schemas.ResourceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin", "counsellor")),
):
    resource = models.Resource(
        title=payload.title,
        category=payload.category,
        type=payload.type,
        duration_minutes=payload.duration_minutes,
        language=payload.language,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource
