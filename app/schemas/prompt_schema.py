# app/schemas/prompt_schema.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PromptBase(BaseModel):
    test_case_id: int
    template_name: str
    prompt_text: str

class PromptCreate(PromptBase):
    pass

class PromptResponse(PromptBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
