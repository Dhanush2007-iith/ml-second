import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

QUOTES = [
    "Small steps every day still move you forward.",
    "You don't have to see the whole staircase, just the next step.",
    "Rest is productive too.",
    "Asking for help is a sign of strength, not weakness.",
    "This feeling is real, and it is also temporary.",
]


def compute_wellness_score(db: Session, user_id: int) -> int:
    recent = (
        db.query(models.MoodLog)
        .filter(models.MoodLog.user_id == user_id)
        .order_by(models.MoodLog.created_at.desc())
        .limit(7)
        .all()
    )
    if not recent:
        return 70
    mood_points = {"great": 100, "okay": 65, "low": 30}
    avg_mood = sum(mood_points[m.mood.value] for m in recent) / len(recent)
    avg_stress_penalty = sum(m.stress_level for m in recent) / len(recent) * 3
    score = max(0, min(100, round(avg_mood - avg_stress_penalty + 20)))
    return score


@router.get("/student")
def student_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("student")),
):
    week_ago = datetime.utcnow() - timedelta(days=7)
    logs = (
        db.query(models.MoodLog)
        .filter(models.MoodLog.user_id == current_user.id, models.MoodLog.created_at >= week_ago)
        .order_by(models.MoodLog.created_at.asc())
        .all()
    )
    mood_points = {"great": 8, "okay": 6, "low": 3}
    week_mood = [
        {"day": log.created_at.strftime("%a"), "score": mood_points[log.mood.value]}
        for log in logs
    ]

    upcoming = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.student_id == current_user.id,
            models.Appointment.scheduled_time >= datetime.utcnow(),
            models.Appointment.status != models.AppointmentStatusEnum.cancelled,
        )
        .order_by(models.Appointment.scheduled_time.asc())
        .first()
    )
    upcoming_out = None
    if upcoming:
        counsellor = db.query(models.User).filter(models.User.id == upcoming.counsellor_id).first()
        upcoming_out = {
            "id": upcoming.id,
            "counsellor_name": counsellor.full_name if counsellor else "Counsellor",
            "mode": upcoming.mode.value,
            "scheduled_time": upcoming.scheduled_time.isoformat(),
            "status": upcoming.status.value,
        }

    recommended = (
        db.query(models.Resource).order_by(func.random()).limit(3).all()
    )

    streak = min(len(logs), 30)

    return {
        "full_name": current_user.full_name,
        "quote": random.choice(QUOTES),
        "wellness_score": compute_wellness_score(db, current_user.id),
        "week_mood": week_mood,
        "upcoming_appointment": upcoming_out,
        "recommended_resources": [
            {"id": r.id, "title": r.title, "type": r.type, "category": r.category} for r in recommended
        ],
        "streak_days": streak,
    }


@router.get("/counsellor")
def counsellor_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("counsellor")),
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    appts = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.counsellor_id == current_user.id,
            models.Appointment.scheduled_time >= today_start,
            models.Appointment.scheduled_time < today_end,
        )
        .order_by(models.Appointment.scheduled_time.asc())
        .all()
    )
    appt_out = []
    for a in appts:
        student = db.query(models.User).filter(models.User.id == a.student_id).first()
        display = student.anonymous_id if a.anonymous else student.full_name
        appt_out.append({
            "id": a.id,
            "display_name": display,
            "time": a.scheduled_time.strftime("%I:%M %p"),
            "status": a.status.value,
        })

    high_risk = (
        db.query(models.Assessment)
        .join(models.Appointment, models.Appointment.student_id == models.Assessment.user_id)
        .filter(
            models.Appointment.counsellor_id == current_user.id,
            models.Assessment.high_risk_flag == True,  # noqa: E712
        )
        .order_by(models.Assessment.created_at.desc())
        .limit(5)
        .all()
    )
    alerts = []
    for h in high_risk:
        student = db.query(models.User).filter(models.User.id == h.user_id).first()
        alerts.append({
            "student_display": student.anonymous_id if student else "Anonymous",
            "type": h.type.value,
            "risk_level": h.risk_level.value,
        })

    return {"today_appointments": appt_out, "risk_alerts": alerts}


@router.get("/volunteer")
def volunteer_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("volunteer")),
):
    posts_to_moderate = db.query(models.ForumPost).filter(models.ForumPost.report_count > 0).count()
    return {
        "assigned_checkins": db.query(models.User).filter(models.User.role == models.RoleEnum.student).count() % 10,
        "posts_to_moderate": posts_to_moderate,
        "training_modules_left": 2,
    }
