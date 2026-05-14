from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import random
import string
import os

from database import get_db
import models
import schemas

router = APIRouter()

# Admin ID lari (Haqiqiy va Test)
ALLOWED_ADMINS = ["7294699676", "123456789", os.getenv("ADMIN_TELEGRAM_ID", "").strip()]

@router.post("/quiz")
def create_quiz(quiz_data: schemas.QuizCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_id == quiz_data.telegram_id).first()
    if not user:
        user = models.User(telegram_id=quiz_data.telegram_id, first_name="Mehmon")
        db.add(user)
        db.commit()
        db.refresh(user)

    code = ''.join(random.choices(string.digits, k=6))
    while db.query(models.Quiz).filter(models.Quiz.code == code).first():
        code = ''.join(random.choices(string.digits, k=6))

    new_quiz = models.Quiz(
        code=code,
        title=quiz_data.title,
        creator_id=user.id,
        timer_per_question=quiz_data.timer_per_question
    )
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)

    for q in quiz_data.questions:
        new_q = models.Question(
            quiz_id=new_quiz.id,
            text=q.text,
            option_a=q.option_a,
            option_b=q.option_b,
            option_c=q.option_c,
            option_d=q.option_d,
            correct_option=q.correct_option
        )
        db.add(new_q)
    
    db.commit()
    return {"code": code}

@router.get("/quiz/{code}")
def get_quiz(code: str, start: int = 1, end: int = 25, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(models.Quiz.code == code).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz topilmadi")
    
    # Savollarni tartib bilan olamiz
    all_questions = sorted(quiz.questions, key=lambda x: x.id)
    total_count = len(all_questions)
    
    # Kerakli oraliqni qirqib olamiz (1-indexed inputni 0-indexed listga o'tkazamiz)
    selected_questions = all_questions[start-1:end]
    
    questions_data = []
    for q in selected_questions:
        options = [
            ("a", q.option_a),
            ("b", q.option_b),
            ("c", q.option_c),
            ("d", q.option_d)
        ]
        
        correct_text = ""
        if q.correct_option.lower() == "a": correct_text = q.option_a
        elif q.correct_option.lower() == "b": correct_text = q.option_b
        elif q.correct_option.lower() == "c": correct_text = q.option_c
        elif q.correct_option.lower() == "d": correct_text = q.option_d
        
        # FAQAT VARIANTLARNI ARALASHTIRAMIZ
        random.shuffle(options)
        
        new_q = {
            "text": q.text,
            "option_a": options[0][1],
            "option_b": options[1][1],
            "option_c": options[2][1],
            "option_d": options[3][1],
            "correct_option": ""
        }
        
        for idx, opt_pair in enumerate(options):
            if opt_pair[1] == correct_text:
                new_q["correct_option"] = ["a", "b", "c", "d"][idx]
                break
        
        questions_data.append(new_q)
        
    return {
        "id": quiz.id,
        "code": quiz.code,
        "title": quiz.title,
        "total_questions": total_count,
        "timer_per_question": quiz.timer_per_question,
        "questions": questions_data
    }

@router.post("/result")
def submit_result(res_data: schemas.SubmitResult, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_id == res_data.telegram_id).first()
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
    user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    if not user:
        return []

    results = db.query(models.Result).filter(models.Result.user_id == user.id).order_by(desc(models.Result.date)).all()
    
    return [
        {
            "quiz_code": r.quiz_code,
            "chunk_range": r.chunk_range,
            "correct_count": r.correct_count,
            "incorrect_count": r.incorrect_count,
            "date": r.date.isoformat()
        } for r in results
    ]

@router.get("/public/quizzes")
def get_public_quizzes(db: Session = Depends(get_db)):
    # Oxirgi 20 ta yaratilgan quizni qaytaramiz
    quizzes = db.query(models.Quiz).order_by(desc(models.Quiz.created_at)).limit(20).all()
    
    result_data = []
    for q in quizzes:
        result_data.append({
            "code": q.code,
            "title": q.title or "Noma'lum fan",
            "created_at": q.created_at.strftime("%Y-%m-%d %H:%M"),
            "total_questions": len(q.questions)
        })
    return result_data

@router.get("/admin/check/{telegram_id}")
def check_admin(telegram_id: str, password: str = None):
    # Faqat belgilangan adminlar va to'g'ri parol bo'lsa
    is_admin_user = (telegram_id.strip() in ALLOWED_ADMINS)
    # Agar parol kiritilgan bo'lsa, uni ham tekshiramiz
    if password:
        return {"is_admin": is_admin_user and password == "1213"}
    return {"is_admin": is_admin_user}

@router.get("/admin/users")
def get_admin_users(telegram_id: str, db: Session = Depends(get_db)):
    if telegram_id.strip() not in ALLOWED_ADMINS:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    users = db.query(models.User).order_by(desc(models.User.id)).all()
    return [
        {
            "id": u.id,
            "telegram_id": u.telegram_id,
            "first_name": u.first_name,
            "username": u.username,
            "is_admin": u.is_admin
        } for u in users
    ]

@router.get("/admin/quizzes")
def get_admin_quizzes(telegram_id: str, db: Session = Depends(get_db)):
    if telegram_id.strip() not in ALLOWED_ADMINS:
        raise HTTPException(status_code=403, detail="Forbidden")

    quizzes = db.query(models.Quiz).order_by(desc(models.Quiz.created_at)).all()
    
    result_data = []
    for q in quizzes:
        creator = db.query(models.User).filter(models.User.id == q.creator_id).first()
        results = db.query(models.Result).filter(models.Result.quiz_code == q.code).all()
        
        participants = []
        for r in results:
            p_user = db.query(models.User).filter(models.User.id == r.user_id).first()
            participants.append({
                "first_name": p_user.first_name if p_user else "Noma'lum",
                "username": p_user.username if p_user else "",
                "chunk_range": r.chunk_range,
                "correct": r.correct_count,
                "incorrect": r.incorrect_count,
                "date": r.date.strftime("%Y-%m-%d %H:%M")
            })
            
        result_data.append({
            "code": q.code,
            "created_at": q.created_at.strftime("%Y-%m-%d %H:%M"),
            "creator_name": creator.first_name if creator else "Noma'lum",
            "creator_username": creator.username if creator else "",
            "total_questions": len(q.questions),
            "participants": participants
        })
        
    return result_data

@router.delete("/admin/quiz/{code}")
def delete_quiz(code: str, telegram_id: str, db: Session = Depends(get_db)):
    if telegram_id.strip() not in ALLOWED_ADMINS:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    quiz = db.query(models.Quiz).filter(models.Quiz.code == code).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz topilmadi")
    
    db.delete(quiz)
    db.commit()
    return {"status": "success"}
