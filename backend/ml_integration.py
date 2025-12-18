import random  # Для mock

def process_video(video_path: str) -> dict:
    # Заглушка: Симулируем детекцию от ML (случайные числа)
    # Замените на реальный ML-код позже
    entered = random.randint(0, 10)  # 0-10 зашедших
    exited = random.randint(0, 5)    # 0-5 ушедших
    occupied_tables = random.randint(0, 20)  # 0-20 занятых столов
    return {
        "entered": entered,
        "exited": exited,
        "occupied_tables": occupied_tables
    }