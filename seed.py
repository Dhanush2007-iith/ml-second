from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


@router.get("/counsellors", response_model=list[schemas.CounsellorOut])
def list_counsellors(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.User).filter(models.User.role == models.RoleEnum.counsellor).all()


@router.post("/book", response_model=schemas.AppointmentOut, status_code=201)
def book_appointment(
    payload: schemas.AppointmentBook,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("student")),
):
    counsellor = db.query(models.User).filter(
        models.User.id == payload.counsellor_id, models.User.role == models.RoleEnum.counsellor
    ).first()
    if not counsellor:
        raise HTTPException(status_code=404, detail="Counsellor not found")
    if payload.scheduled_time < datetime.utcnow():
        raise HTTPException(status_code=422, detail="Appointment time must be in the future")

    appt = models.Appointment(
        student_id=current_user.id,
        counsellor_id=counsellor.id,
        mode=payload.mode,
        anonymous=payload.anonymous,
        scheduled_time=payload.scheduled_time,
        status=models.AppointmentStatusEnum.confirmed,
    )
    db.add(appt)
    db.add(models.Notification(
        user_id=counsellor.id,
        type="reminder",
        message=f"New appointment booked by {current_user.anonymous_id} on {payload.scheduled_time.strftime('%d %b, %I:%M %p')}.",
    ))
    db.commit()
    db.refresh(appt)

    return schemas.AppointmentOut(
        id=appt.id, counsellor_id=appt.counsellor_id, student_id=appt.student_id,
        mode=appt.mode, anonymous=appt.anonymous, scheduled_time=appt.scheduled_time,
        status=appt.status, qr_code=appt.qr_code, counsellor_name=counsellor.full_name,
        student_display=current_user.anonymous_id if appt.anonymous else current_user.full_name,
    )


@router.get("/my", response_model=list[schemas.AppointmentOut])
def my_appointments(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_roles("student"))
):
    appts = (
        db.query(models.Appointment)
        .filter(models.Appointment.student_id == current_user.id)
        .order_by(models.Appointment.scheduled_time.desc())
        .all()
    )
    out = []
    for a in appts:
        counsellor = db.query(models.User).filter(models.User.id == a.counsellor_id).first()
        out.append(schemas.AppointmentOut(
            id=a.id, counsellor_id=a.counsellor_id, student_id=a.student_id, mode=a.mode,
            anonymous=a.anonymous, scheduled_time=a.scheduled_time, status=a.status,
            qr_code=a.qr_code, counsellor_name=counsellor.full_name if counsellor else None,
            student_display=current_user.anonymous_id if a.anonymous else current_user.full_name,
        ))
    return out


@router.get("/counsellor", response_model=list[schemas.AppointmentOut])
def counsellor_appointments(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_roles("counsellor"))
):
    appts = (
        db.query(models.Appointment)
        .filter(models.Appointment.counsellor_id == current_user.id)
        .order_by(models.Appointment.scheduled_time.asc())
        .all()
    )
    out = []
    for a in appts:
        student = db.query(models.User).filter(models.User.id == a.student_id).first()
        display = student.anonymous_id if (a.anonymous or not student) else student.full_name
        out.append(schemas.AppointmentOut(
            id=a.id, counsellor_id=a.counsellor_id, student_id=a.student_id, mode=a.mode,
            anonymous=a.anonymous, scheduled_time=a.scheduled_time, status=a.status,
            qr_code=a.qr_code, counsellor_name=current_user.full_name, student_display=display,
        ))
    return out


@router.patch("/{appointment_id}/status", response_model=schemas.AppointmentOut)
def update_status(
    appointment_id: int,
    payload: schemas.AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("counsellor", "admin")),
):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role == models.RoleEnum.counsellor and appt.counsellor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own appointments")

    appt.status = payload.status
    db.commit()
    db.refresh(appt)

    student = db.query(models.User).filter(models.User.id == appt.student_id).first()
    counsellor = db.query(models.User).filter(models.User.id == appt.counsellor_id).first()
    return schemas.AppointmentOut(
        id=appt.id, counsellor_id=appt.counsellor_id, student_id=appt.student_id, mode=appt.mode,
        anonymous=appt.anonymous, scheduled_time=appt.scheduled_time, status=appt.status,
        qr_code=appt.qr_code, counsellor_name=counsellor.full_name if counsellor else None,
        student_display=student.anonymous_id if student else None,
    )
