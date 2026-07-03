from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles

router = APIRouter(prefix="/api/admin", tags=["Admin Analytics"])


@router.get("/analytics", response_model=schemas.AdminAnalytics)
def analytics(db: Session = Depends(get_db), current_user: models.User = Depends(require_roles("admin"))):
    total_students = db.query(models.User).filter(models.User.role == models.RoleEnum.student).count()

    avg_stress_row = db.query(func.avg(models.MoodLog.stress_level)).scalar()
    avg_stress_score = round((avg_stress_row or 0) * 10, 1)  # scale 0-10 -> 0-100

    students_screened = (
        db.query(models.Assessment.user_id).distinct().count()
    )

    high_risk_flags = db.query(models.Assessment).filter(models.Assessment.high_risk_flag == True).count()  # noqa: E712

    week_ago = datetime.utcnow() - timedelta(days=7)
    active_chats_7d = (
        db.query(models.ChatMessage.session_id)
        .filter(models.ChatMessage.created_at >= week_ago)
        .distinct()
        .count()
    )

    dept_rows = (
        db.query(models.User.department, func.avg(models.MoodLog.stress_level))
        .join(models.MoodLog, models.MoodLog.user_id == models.User.id)
        .filter(models.User.department.isnot(None))
        .group_by(models.User.department)
        .all()
    )
    department_stress = [
        {"dept": dept or "Unspecified", "score": round((score or 0) * 10, 1)} for dept, score in dept_rows
    ]

    six_months_ago = datetime.utcnow() - timedelta(days=180)
    trend_rows = (
        db.query(
            func.strftime("%Y-%m", models.Assessment.created_at).label("month"),
            models.Assessment.type,
            func.avg(models.Assessment.score),
        )
        .filter(models.Assessment.created_at >= six_months_ago)
        .group_by("month", models.Assessment.type)
        .order_by("month")
        .all()
    )
    trend_map: dict[str, dict] = {}
    for month, atype, avg_score in trend_rows:
        entry = trend_map.setdefault(month, {"m": month})
        key = "depression" if atype.value == "PHQ9" else "anxiety"
        entry[key] = round(avg_score or 0, 1)
    monthly_trend = list(trend_map.values())

    hostel_count = db.query(models.User).filter(
        models.User.role == models.RoleEnum.student, models.User.is_hostel == True  # noqa: E712
    ).count()
    day_scholar_count = max(total_students - hostel_count, 0)
    hostel_split = [
        {"name": "Hostel", "value": hostel_count},
        {"name": "Day scholar", "value": day_scholar_count},
    ]

    return schemas.AdminAnalytics(
        avg_stress_score=avg_stress_score,
        students_screened=students_screened,
        total_students=total_students,
        high_risk_flags=high_risk_flags,
        active_chats_7d=active_chats_7d,
        department_stress=department_stress,
        monthly_trend=monthly_trend,
        hostel_split=hostel_split,
    )
