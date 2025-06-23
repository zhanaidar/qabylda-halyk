from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    department = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Test(Base):
    __tablename__ = "tests"
    
    id = Column(Integer, primary_key=True)
    test_code = Column(String(50), unique=True, nullable=False)
    candidate_name = Column(String(255), nullable=False)
    candidate_email = Column(String(255))
    position = Column(String(100), nullable=False)
    level = Column(String(50), nullable=False)
    creator_email = Column(String(255), nullable=False)
    custom_requirements = Column(Text)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Результаты
    total_score = Column(Float, default=0.0)
    final_evaluation = Column(Text)
    status = Column(String(50), default="created")  # created, started, completed, expired
    duration_minutes = Column(Integer)
    
    # Прокторинг (пока JSON строка)
    violations_count = Column(Integer, default=0)
    proctoring_data = Column(Text)  # JSON string
    
    # Связи
    questions = relationship("TestQuestion", back_populates="test")

class TestQuestion(Base):
    __tablename__ = "test_questions"
    
    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_type = Column(String(50), nullable=False)  # main, extension, deep
    
    # Контент
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text)
    
    # Оценки
    ai_score = Column(Float)
    ai_evaluation = Column(Text)
    
    # Метрики
    typing_speed = Column(Float)  # символов в минуту
    time_spent_seconds = Column(Integer)
    answered_at = Column(DateTime)
    
    # Связи
    test = relationship("Test", back_populates="questions")