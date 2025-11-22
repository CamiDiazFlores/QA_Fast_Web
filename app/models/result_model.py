# app/models/result_model.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.config import Base  # Importar desde config, NO desde __init__

class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    status = Column(String(50), nullable=False)  # 'passed', 'failed', 'error'
    logs = Column(Text, nullable=True)
    screenshot_path = Column(String(500), nullable=True)
    execution_time = Column(String(50), nullable=True)
    executed_by_agent = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
