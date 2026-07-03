from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/assessments", tags=["Assessments"])

PHQ9_QUESTIONS = [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself, or that you are a failure",
    "Trouble concentrating on things",
    "Moving or speaking slowly, or being fidgety/restless",
    "Thoughts that you would be better off dead or of hurting yourself",
]

GAD7_QUESTIONS = [
    "Feeling nervous, anxious, or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it's hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid as if something awful might happen",
]

QUESTION_SETS = {"PHQ9": PHQ9_QUESTIONS, "GAD7": GAD7_QUESTIONS}
SELF_HARM_ITEM_INDEX = {"PHQ9": 8}  # 0-indexed item that flags high risk directly


def classify_phq9(score: int) -> str:
    if score <= 4:
        return "Minimal"
    if score <= 9:
        return "Mild"
    if score <= 14:
        return "Moderate"
    if score <= 19:
        return "Moderately severe"
    return "Severe"


def classify_gad7(score: int) -> str:
    if score <= 4:
        return "Minimal"
    if score <= 9:
        return "Mild"
    if score <= 14:
        return "Moderate"
    return "Severe"


@router.get("/questions/{type}")
def get_questions(type: str):
    type = type.upper()
    if type not in QUESTION_SETS:
        raise HTTPException(status_code=404, detail="Unknown assessment type. Use PHQ9 or GAD7.")
    return {"type": type, "questions": QUESTION_SETS[type], "options": [
        "Not at all", "Several days", "More than half the days", "Nearly every day"
    ]}


@router.post("", response_model=schemas.AssessmentOut, status_code=201)
def submit_assessment(
    payload: schemas.AssessmentSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    type_key = payload.type.value
    expected_len = len(QUESTION_SETS[type_key])
    if len(payload.answers) != expected_len:
        raise HTTPException(status_code=422, detail=f"{type_key} requires exactly {expected_len} answers")

    score = sum(payload.answers)
    risk_level = classify_phq9(score) if type_key == "PHQ9" else classify_gad7(score)

    high_risk = risk_level in ("Moderately severe", "Severe")
    self_harm_idx = SELF_HARM_ITEM_INDEX.get(type_key)
    if self_harm_idx is not None and payload.answers[self_harm_idx] > 0:
        high_risk = True

    record = models.Assessment(
        user_id=current_user.id,
        type=payload.type,
        answers=payload.answers,
        score=score,
        risk_level=risk_level,
        high_risk_flag=high_risk,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    if high_risk:
        counsellors = db.query(models.User).filter(models.User.role == models.RoleEnum.counsellor).all()
        for c in counsellors:
            db.add(models.Notification(
                user_id=c.id,
                type="alert",
                message=f"{current_user.anonymous_id} scored '{risk_level}' on {type_key} — follow-up recommended.",
            ))
        db.commit()

    return record


@router.get("/history", response_model=list[schemas.AssessmentOut])
def history(
    type: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Assessment).filter(models.Assessment.user_id == current_user.id)
    if type:
        q = q.filter(models.Assessment.type == type.upper())
    return q.order_by(models.Assessment.created_at.desc()).all()
