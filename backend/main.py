from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json 
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import sys 
from starlette.concurrency import run_in_threadpool  # асинхронный вызов синхронного кода

# импорт функций базы данных
from db import (
    init_db,
    update_status, 
    get_current_status,
    get_history,
    get_daily_stats,
    generate_daily_report,
    update_detailed_tables_status, 
    get_detailed_status,
    get_weekday_hourly_occupancy,
)
from models import (
    UpdateData, 
    StatusResponse, 
    OccupancyUpdate, 
    DetailedStatusResponse
)

# конфигурация параметров приложения тут
app = FastAPI(title="Dining Room Occupancy Monitor")
scheduler = BackgroundScheduler()

# емкость мест на стол
TABLE_CAPACITY = 3 

# настройка корс для запросов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# менеджер подключений вебсокет клиентов
class ConnectionManager:
    """управляет подключениями вебсокет клиентов"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """добавляем клиента и шлем статус"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # загрузка из бд без блокировки
        initial_data = await run_in_threadpool(get_detailed_status, TABLE_CAPACITY)
        
        if initial_data:
            initial_json = json.dumps(initial_data, default=str)
            await websocket.send_text(initial_json)

    def disconnect(self, websocket: WebSocket):
        """удаляем клиента из списка"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: str):
        """рассылаем статус всем клиентам"""
        disconnected_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except RuntimeError:
                disconnected_connections.append(connection)
                
        for connection in disconnected_connections:
            self.active_connections.remove(connection)

manager = ConnectionManager() 


@app.on_event("startup")
async def startup():
    """запуск приложения и сервисов"""
    # инициализация бд при старте
    init_db() 
    scheduler.start()
    print("FastAPI Backend Started. WebSockets Manager Ready.")

@app.on_event("shutdown")
def shutdown():
    """остановка сервисов приложения тут"""
    scheduler.shutdown()


## СВЯЗЬ ФРОНТЕНДА И БЕКЕНДА: WEBSOCKET
@app.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    """поток вебсокет обновлений фронта"""
    await manager.connect(websocket)
    try:
        while True:
            # ждем входящие сообщения сокета
            await websocket.receive_text() 
    except Exception:
        manager.disconnect(websocket)
        print("WebSocket disconnected.")

## СВЯЗЬ ML И БЕКЕНДА: HTTP POST
@app.post("/api/tables/update", tags=["ML Integration"])
async def ml_update_tables(update_data: OccupancyUpdate):
    """прием статуса столов из мл"""
    
    occupancy_list = update_data.table_occupancy
    
    print(f"DEBUG: FastAPI received payload: {occupancy_list}")
    
    success = False
    try:
        # вызов бд через тредпул
        success = await run_in_threadpool(
            update_detailed_tables_status, 
            occupancy_list, 
            TABLE_CAPACITY
        )
    except Exception as e:
        print(f"Database update failed: {e}")
        # ошибка при работе с бд
        raise HTTPException(status_code=500, detail=f"Database update failed: {e}")

    if success:
        
        # чтение статуса через тредпул
        new_status_data = await run_in_threadpool(
            get_detailed_status, 
            TABLE_CAPACITY
        )
        
        # сериализация статуса в джсон
        status_json = json.dumps(new_status_data, default=str) 
        
        # рассылка обновлений всем сокетам
        await manager.broadcast(status_json) 
        
        # возвращаем успешный ответ клиенту
        return {"success": True, "message": "Tables status received and broadcasted"}
    else:
        # бд вернула ложь ошибка
        raise HTTPException(status_code=503, detail="Database service not available or operation failed.")

## СВЯЗЬ ФРОНТЕНДА И БЕКЕНДА: HTTP GET
@app.get("/api/status/detailed", response_model=DetailedStatusResponse, tags=["Frontend API"])
async def detailed_status():  # асинхронный обработчик статуса хттп
    """хттп статус столов для интерфейса"""
    # чтение из бд тредпул
    data = await run_in_threadpool(get_detailed_status, TABLE_CAPACITY)
    
    if data:
        return data
    else:
        raise HTTPException(status_code=503, detail="Service Unavailable or No data in DB")


## СВЯЗЬ ФРОНТЕНДА И БЕКЕНДА: HTTP GET
@app.get("/api/stats/weekly", tags=["Frontend API"])
async def weekly_stats(days_back: int = 30, start_hour: int = 9, end_hour: int = 16):
    """статистика по часам недели"""
    if start_hour < 0 or end_hour > 23 or start_hour > end_hour:
        raise HTTPException(status_code=422, detail="invalid start_hour end_hour")

    data = await run_in_threadpool(get_weekday_hourly_occupancy, days_back, start_hour, end_hour)
    if data:
        return data
    raise HTTPException(status_code=503, detail="Service Unavailable or No data in DB")


# старые эндпоинты для совместимости

@app.get("/")
def root():
    return {"message": "Dining Room Monitor Backend is Operational. WebSockets on /ws/status."}

@app.post("/update", tags=["Legacy"])
def update(update_data: UpdateData):
    """старый эндпоинт обновления счетчиков"""
    # старый эндпоинт синхронный умышленно
    success = update_status(update_data.entered, update_data.exited, update_data.occupied_tables)
    if success:
        return {"success": True, "warning": "Legacy update ignored. Use /api/tables/update"}
    else:
        return {"success": False, "error": "Update failed"}

@app.get("/history", tags=["Stats and Reports"])
def api_history(limit: int = 100):
    # эндпоинт синхронный умышленно тут
    return get_history(limit)

@app.get("/history/day/{date}", tags=["Stats and Reports"])
def api_daily_stats(date: str):
    # эндпоинт синхронный умышленно тут
    return get_daily_stats(date)

@app.post("/history/generate/{date}", tags=["Stats and Reports"])
def api_generate_daily_report(date: str):
    # эндпоинт синхронный умышленно тут
    generate_daily_report(date)
    return {"status": "ok"}