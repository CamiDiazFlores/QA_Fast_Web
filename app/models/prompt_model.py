# app/models/prompt_model.py
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.config import Base  # Importar desde config, NO desde __init__

class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    prompt_text = Column(Text, nullable=False)
    generated_code = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
