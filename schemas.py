from pydantic import BaseModel
from typing import List, Optional


class QuestionCreate(BaseModel):
    text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str


class QuizCreate(BaseModel):
    telegram_id: int
    timer_per_question: int = 30
    questions: List[QuestionCreate]


class SubmitResult(BaseModel):
    telegram_id: int
    quiz_code: str
    correct_count: int
    incorrect_count: int
    chunk_range: Optional[str] = None
