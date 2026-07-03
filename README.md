from sqlalchemy.orm import Session

from . import models
from .security import hash_password

COUNSELLORS = [
    {"full_name": "Dr. Ananya Rao", "email": "ananya.rao@mindbridge.edu", "specialization": "Anxiety & academic stress", "rating": 4.9},
    {"full_name": "Dr. Kabir Mehta", "email": "kabir.mehta@mindbridge.edu", "specialization": "Depression & burnout", "rating": 4.8},
    {"full_name": "Dr. Sana Ilyas", "email": "sana.ilyas@mindbridge.edu", "specialization": "Relationships & identity", "rating": 5.0},
]

RESOURCES = [
    {"title": "4-7-8 breathing for instant calm", "category": "Anxiety", "type": "Audio", "duration_minutes": 5, "language": "English"},
    {"title": "Building a wind-down routine", "category": "Sleep", "type": "Guide", "duration_minutes": 6, "language": "English"},
    {"title": "Reframing perfectionism worksheet", "category": "Exam prep", "type": "PDF", "duration_minutes": 8, "language": "English"},
    {"title": "Understanding burnout vs. laziness", "category": "Burnout", "type": "Video", "duration_minutes": 10, "language": "English"},
    {"title": "5-minute body scan meditation", "category": "Meditation", "type": "Audio", "duration_minutes": 5, "language": "English"},
    {"title": "Talking to friends about how you feel", "category": "Relationships", "type": "Guide", "duration_minutes": 4, "language": "English"},
    {"title": "The science of small wins", "category": "Motivation", "type": "Video", "duration_minutes": 7, "language": "English"},
    {"title": "Recognising early signs of low mood", "category": "Depression", "type": "Guide", "duration_minutes": 6, "language": "English"},
    {"title": "Saans ki shakti: tanav kam karein", "category": "Stress", "type": "Audio", "duration_minutes": 5, "language": "Hindi"},
]

FORUM_POSTS = [
    {"author_display": "QuietOwl22", "content": "Anyone else feel behind even when they're not?", "tag": "Motivation"},
    {"author_display": "CalmRiver", "content": "Found a great 10-min walk route around campus that helps me reset between classes.", "tag": "Self-care"},
    {"author_display": "MorningLight", "content": "First therapy session today, feeling nervous but hopeful.", "tag": "Support"},
]

ADMIN_SEED = {"full_name": "Campus Admin", "email": "admin@mindbridge.edu", "password": "Admin@123"}


def run_seed(db: Session) -> None:
    if db.query(models.User).count() > 0:
        return

    for c in COUNSELLORS:
        db.add(models.User(
            full_name=c["full_name"],
            email=c["email"],
            hashed_password=hash_password("Counsellor@123"),
            role=models.RoleEnum.counsellor,
            specialization=c["specialization"],
            rating=c["rating"],
        ))

    db.add(models.User(
        full_name=ADMIN_SEED["full_name"],
        email=ADMIN_SEED["email"],
        hashed_password=hash_password(ADMIN_SEED["password"]),
        role=models.RoleEnum.admin,
    ))

    for r in RESOURCES:
        db.add(models.Resource(**r))

    db.commit()

    # forum posts need a user id, use the first counsellor as a system seeder isn't ideal;
    # create a lightweight anonymous seed student instead
    seed_student = models.User(
        full_name="Seed Student",
        email="seed.student@mindbridge.edu",
        hashed_password=hash_password("Student@123"),
        role=models.RoleEnum.student,
        department="General",
    )
    db.add(seed_student)
    db.commit()
    db.refresh(seed_student)

    for p in FORUM_POSTS:
        db.add(models.ForumPost(user_id=seed_student.id, **p, reply_count=3))
    db.commit()
