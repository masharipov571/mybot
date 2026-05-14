from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    first_name = Column(String)
    username = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    results = relationship("Result", back_populates="user")
    subscription = relationship("Subscription", back_populates="user", uselist=False)

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    title = Column(String, nullable=True) # Fan nomi
    creator_id = Column(Integer, ForeignKey("users.id"))
    timer_per_question = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    text = Column(String)
    option_a = Column(String)
    option_b = Column(String)
    option_c = Column(String)
    option_d = Column(String)
    correct_option = Column(String)
    quiz = relationship("Quiz", back_populates="questions")

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    quiz_code = Column(String)
    correct_count = Column(Integer)
    incorrect_count = Column(Integer)
    chunk_range = Column(String)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="results")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    group_name = Column(String)
    notification_time = Column(String)
    user = relationship("User", back_populates="subscription")
