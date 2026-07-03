from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/mood", tags=["Mood Tracking"])


@router.post("/checkin", response_model=schemas.MoodOut, status_code=201)
def checkin(
    payload: schemas.MoodCheckIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    log = models.MoodLog(
        user_id=current_user.id,
        mood=payload.mood,
        sleep_hours=payload.sleep_hours,
        stress_level=payload.stress_level,
        journal=payload.journal,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/history", response_model=list[schemas.MoodOut])
def history(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)
    logs = (
        db.query(models.MoodLog)
        .filter(models.MoodLog.user_id == current_user.id, models.MoodLog.created_at >= since)
        .order_by(models.MoodLog.created_at.asc())
        .all()
    )
    return logs
