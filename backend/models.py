from pydantic import BaseModel, Field
from datetime import datetime

class UpdateData(BaseModel):
    entered: int = Field(..., ge=0)  # Количество зашедших, >=0, обязательно
    exited: int = Field(..., ge=0)   # Ушедших, >=0, обязательно
    occupied_tables: int = Field(..., ge=0, le=20)  # Занятых столов, 0-20, обязательно

class StatusResponse(BaseModel):
    people_inside: int
    free_tables: int
    last_update: str