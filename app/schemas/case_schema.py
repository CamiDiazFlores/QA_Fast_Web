# app/schemas/case_schema.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TestCaseCreate(BaseModel):
    """Schema para crear un caso de prueba"""
    name: str
    description: Optional[str] = None
    steps: str
    expected_result: str
    url: Optional[str] = None

class TestCaseResponse(BaseModel):
    """Schema para respuesta de caso de prueba"""
    id: int
    name: str
    description: Optional[str] = None
    steps: str
    expected_result: str
    url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Para Pydantic v2 (antes era orm_mode = True)


# === Alias opcionales para mantener compatibilidad con tu código ===
CaseCreate = TestCaseCreate
CaseResponse = TestCaseResponse
