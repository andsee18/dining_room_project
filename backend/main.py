from fastapi import FastAPI
from db import init_db
from models import UpdateData, StatusResponse
from db import update_status, get_current_status
from apscheduler.schedulers.background import BackgroundScheduler
from ml_integration import process_video
from db import update_status

from db import (
    update_status,
    get_history,
    get_daily_stats,
    generate_daily_report
)


app = FastAPI()
scheduler = BackgroundScheduler()

@app.on_event("startup")
async def startup():
    init_db()
    scheduler.add_job(update_from_ml, 'interval', minutes=1)
scheduler.start()

@app.get("/")
def root():
    return {"message": "РАБОТАЕТ!!!!!!!!"}

@app.get("/db-test")
def db_test():
    from db import connect_db
    conn = connect_db()
    if conn is None:
        return {"error": "DB connection failed"}
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM current_status WHERE id=1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return {
            "people_inside": row[1],
            "free_tables": row[2],
            "last_update": row[3]
        }
    return {"error": "No data"}

@app.post("/update")
def update(update_data: UpdateData):
    success = update_status(update_data.entered, update_data.exited, update_data.occupied_tables)
    if success:
        return {"success": True}
    else:
        return {"success": False, "error": "Update failed"}

@app.get("/status", response_model=StatusResponse)
def status():
    data = get_current_status()
    if data:
        return data
    else:
        return {"people_inside": 0, "free_tables": 20, "last_update": "N/A"} 

def update_from_ml():
    try:
        video_path = 'path/to/your/video.mp4'
        ml_data = process_video(video_path)
        print(f"ML data received: {ml_data}") 

        success = update_status(
            entered=ml_data['entered'],
            exited=ml_data['exited'],
            occupied_tables=ml_data['occupied_tables']
        )
        if success:
            print("Update from ML successful")
        else:
            print("Update from ML failed")
    except Exception as e:
        print(f"ML integration error: {e}")

@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()

@app.get("/history")
def api_history(limit: int = 100):
    return get_history(limit)


@app.get("/history/day/{date}")
def api_daily_stats(date: str):
    return get_daily_stats(date)


@app.post("/history/generate/{date}")
def api_generate_daily_report(date: str):
    generate_daily_report(date)
    return {"status": "ok"}
