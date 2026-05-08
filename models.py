from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime


class User(Base):
    """Telegram foydalanuvchisi"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    first_name = Column(String)
    username = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    results = relationship("Result", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Quiz(Base):
    """Test (Quiz)"""
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"))
    timer_per_question = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[creator_id])


class Question(Base):
    """Savol"""
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
    """Test natijasi"""
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    quiz_code = Column(String)
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    chunk_range = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="results")


class Subscription(Base):
    """Dars jadvali obunasi"""
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    group_name = Column(String)
    notification_time = Column(String)  # "08:00" formatida
    user = relationship("User", back_populates="subscription")
