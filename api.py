from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
import random
import string
import os

from database import get_db
import models
import schemas

router = APIRouter()

# ─── Admin ID'lari ────────────────────────────────────────────────────────────
# Railway Variables da ADMIN_TELEGRAM_ID o'rnating (asosiy usul)
# Yoki bu yerga to'g'ridan-to'g'ri yozing
ALLOWED_ADMINS = {
    "7294699676",  # Asosiy admin
    "123456789",   # Mahalliy test uchun
}
env_admin = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
if env_admin:
    ALLOWED_ADMINS.add(env_admin)


def is_admin(telegram_id: str) -> bool:
    return str(telegram_id).strip() in ALLOWED_ADMINS


# ─── Quiz CRUD ────────────────────────────────────────────────────────────────

@router.post("/quiz")
def create_quiz(quiz_data: schemas.QuizCreate, db: Session = Depends(get_db)):
    """Yangi quiz yaratish"""
    # Foydalanuvchini topish yoki yaratish
    user = db.query(models.User).filter(
        models.User.telegram_id == quiz_data.telegram_id
    ).first()
    if not user:
        user = models.User(telegram_id=quiz_data.telegram_id, first_name="Mehmon")
        db.add(user)
        db.commit()
        db.refresh(user)

    # Noyob 6 xonali kod generatsiyasi
    while True:
        code = ''.join(random.choices(string.digits, k=6))
        if not db.query(models.Quiz).filter(models.Quiz.code == code).first():
            break

    # Quizni saqlash
    new_quiz = models.Quiz(
        code=code,
        creator_id=user.id,
        timer_per_question=quiz_data.timer_per_question
    )
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)

    # Savollarni saqlash
    for q in quiz_data.questions:
        new_q = models.Question(
            quiz_id=new_quiz.id,
            text=q.text,
            option_a=q.option_a,
            option_b=q.option_b,
            option_c=q.option_c,
            option_d=q.option_d,
            correct_option=q.correct_option.lower()
        )
        db.add(new_q)
    db.commit()

    return {"code": code, "total_questions": len(quiz_data.questions)}


@router.get("/quiz/{code}")
def get_quiz(code: str, db: Session = Depends(get_db)):
    """Quiz ma'lumotlarini olish"""
    quiz = db.query(models.Quiz).filter(models.Quiz.code == code).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz topilmadi")

    return {
        "id": quiz.id,
        "code": quiz.code,
        "timer_per_question": quiz.timer_per_question,
        "questions": [
            {
                "text": q.text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_option": q.correct_option
            }
            for q in quiz.questions
        ]
    }


# ─── Natijalar ────────────────────────────────────────────────────────────────

@router.post("/result")
def submit_result(res_data: schemas.SubmitResult, db: Session = Depends(get_db)):
    """Test natijasini saqlash"""
    user = db.query(models.User).filter(
        models.User.telegram_id == res_data.telegram_id
    ).first()
    if not user:
        user = models.User(telegram_id=res_data.telegram_id, first_name="Mehmon")
        db.add(user)
        db.commit()
        db.refresh(user)

    new_res = models.Result(
        user_id=user.id,
        quiz_code=res_data.quiz_code,
        chunk_range=res_data.chunk_range,
        correct_count=res_data.correct_count,
        incorrect_count=res_data.incorrect_count
    )
    db.add(new_res)
    db.commit()
    return {"status": "success"}


@router.get("/results/{telegram_id}")
def get_results(telegram_id: int, db: Session = Depends(get_db)):
    """Foydalanuvchi natijalarini olish"""
    user = db.query(models.User).filter(
        models.User.telegram_id == telegram_id
    ).first()
    if not user:
        return []

    results = (
        db.query(models.Result)
        .filter(models.Result.user_id == user.id)
        .order_by(desc(models.Result.date))
        .all()
    )

    return [
        {
            "quiz_code": r.quiz_code,
            "chunk_range": r.chunk_range,
            "correct_count": r.correct_count,
            "incorrect_count": r.incorrect_count,
            "date": r.date.isoformat() if r.date else None
        }
        for r in results
    ]


# ─── Admin Panel ──────────────────────────────────────────────────────────────

@router.get("/admin/check/{telegram_id}")
def check_admin(telegram_id: str):
    """Foydalanuvchi admin ekanligini tekshirish"""
    return {"is_admin": is_admin(telegram_id)}


@router.get("/admin/quizzes")
def get_admin_quizzes(telegram_id: str, db: Session = Depends(get_db)):
    """Admin paneli uchun barcha quizlar ro'yxati"""
    if not is_admin(telegram_id):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    quizzes = db.query(models.Quiz).order_by(desc(models.Quiz.created_at)).all()

    result_data = []
    for q in quizzes:
        creator = db.query(models.User).filter(models.User.id == q.creator_id).first()
        results = db.query(models.Result).filter(models.Result.quiz_code == q.code).all()

        participants = []
        for r in results:
            p_user = db.query(models.User).filter(models.User.id == r.user_id).first()
            total = r.correct_count + r.incorrect_count
            perc = round((r.correct_count / total) * 100) if total > 0 else 0
            participants.append({
                "first_name": p_user.first_name if p_user else "Noma'lum",
                "username": p_user.username if p_user else "",
                "chunk_range": r.chunk_range or "",
                "correct": r.correct_count,
                "incorrect": r.incorrect_count,
                "percent": perc,
                "date": r.date.strftime("%d.%m.%Y %H:%M") if r.date else ""
            })

        result_data.append({
            "code": q.code,
            "created_at": q.created_at.strftime("%d.%m.%Y %H:%M") if q.created_at else "",
            "creator_name": creator.first_name if creator else "Noma'lum",
            "creator_username": creator.username if creator else "",
            "total_questions": len(q.questions),
            "participants_count": len(participants),
            "participants": participants
        })

    return result_data


@router.delete("/admin/quiz/{code}")
def delete_quiz(code: str, telegram_id: str, db: Session = Depends(get_db)):
    """Quizni o'chirish"""
    if not is_admin(telegram_id):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    quiz = db.query(models.Quiz).filter(models.Quiz.code == code).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz topilmadi")

    db.delete(quiz)
    db.commit()
    return {"status": "success", "deleted_code": code}


@router.get("/admin/users")
def get_users(telegram_id: str, db: Session = Depends(get_db)):
    """Barcha foydalanuvchilar ro'yxati"""
    if not is_admin(telegram_id):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    users = db.query(models.User).all()
    return [
        {
            "id": u.id,
            "telegram_id": u.telegram_id,
            "first_name": u.first_name,
            "username": u.username or "",
            "results_count": len(u.results)
        }
        for u in users
    ]
