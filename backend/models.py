from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# модель запроса от мл
class OccupancyUpdate(BaseModel):
    """модель данных приема от мл"""
    # список занятости по столам
    table_occupancy: List[int]
    # время можно брать на сервере
    
# старые модели для совместимости
class UpdateData(BaseModel):
    # модель для старого апи
    entered: int
    exited: int
    occupied_tables: int

class StatusResponse(BaseModel):
    people_inside: int
    free_tables: int
    last_update: str

# модель статуса для фронта
class DetailedTableStatus(BaseModel):
    table_id: int
    occupied: int
    capacity: int  # емкость мест для стола
    status_color: str  # цвет статуса для интерфейса

class DetailedStatusResponse(BaseModel):
    overall_inside: int
    total_capacity: int
    tables: List[DetailedTableStatus]
    last_update: str