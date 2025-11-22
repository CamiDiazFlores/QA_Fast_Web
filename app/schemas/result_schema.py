# app/schemas/result_schema.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TestResultBase(BaseModel):
    test_case_id: int
    status: str
    logs: Optional[str] = None
    screenshot_path: Optional[str] = None
    execution_time: Optional[str] = None
    executed_by_agent: Optional[bool] = True

class TestResultCreate(TestResultBase):
    pass

class TestResultResponse(TestResultBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2


# Esquema para la respuesta de ejecución completa
class ExecutionResponse(BaseModel):
    """Respuesta completa de la ejecución de un caso de prueba"""
    case_id: int
    code: str  # Código Selenium generado
    output: Optional[str] = None  # Salida de la ejecución
    success: bool  # Si la prueba fue exitosa
    logs: Optional[str] = None  # Logs de ejecución
    
    class Config:
        from_attributes = True
