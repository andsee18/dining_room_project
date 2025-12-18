import psycopg2
from datetime import datetime

DB_NAME = 'stolovka_db'
DB_USER = 'postgres'
DB_PASSWORD = 'password'
DB_HOST = 'localhost'
DB_PORT = '5432'

def connect_db():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None

def init_db():
    conn = connect_db()
    if conn is None:
        return
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS current_status (
            id INTEGER PRIMARY KEY,
            people_inside INTEGER NOT NULL,
            free_tables INTEGER NOT NULL,
            last_update TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id SERIAL PRIMARY KEY,
            timestamp TEXT NOT NULL,
            entered INTEGER NOT NULL,
            exited INTEGER NOT NULL,
            occupied_tables INTEGER NOT NULL
        )
    ''')

    cursor.execute("SELECT * FROM current_status WHERE id=1")
    if not cursor.fetchone():
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO current_status (id, people_inside, free_tables, last_update) VALUES (1, 0, 20, %s)",
            (now,)
        )
    conn.commit()
    cursor.close()
    conn.close()

def update_status(entered: int, exited: int, occupied_tables: int):
    # 0. Подключение к базе
    conn = connect_db()
    if not conn:
        return

    cursor = conn.cursor()

    # 1. Получаем текущее число людей
    cursor.execute("SELECT people_inside FROM current_status WHERE id = 1")
    row = cursor.fetchone()

    # Если там ничего нет (пустая таблица), считаем 0
    current_people = row[0] if row else 0

    # 2. Считаем новое число людей
    new_people = current_people + entered - exited
    if new_people < 0:
        new_people = 0  # защита от отрицательных значений

    # 3. Считаем свободные столы
    free_tables = 20 - occupied_tables

    # 4. Обновляем current_status
    cursor.execute("""
        UPDATE current_status
        SET people_inside=%s,
            free_tables=%s,
            last_update=NOW()
        WHERE id = 1
    """, (new_people, free_tables))

    # 5. Добавляем запись в историю посещений
    cursor.execute("""
        INSERT INTO visit_history(
            timestamp, entered, exited, people_inside, occupied_tables, free_tables
        )
        VALUES (NOW(), %s, %s, %s, %s, %s)
    """, (entered, exited, new_people, occupied_tables, free_tables))

    # 6. Сохраняем изменения
    conn.commit()

    # 7. Закрываем соединение
    cursor.close()
    conn.close()


def get_current_status():
    conn = connect_db()
    print("Connected to DB successfully")  # Если увидите — подключение ок
    if conn is None:
        return None
    cursor = conn.cursor()
    cursor.execute("SELECT people_inside, free_tables, last_update FROM current_status WHERE id=1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return {
            "people_inside": row[0],
            "free_tables": row[1],
            "last_update": row[2]
        }
    return None


def get_history(limit: int = 100):
    conn = connect_db()
    if not conn:
        return []

    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, entered, exited, people_inside, occupied_tables, free_tables
        FROM visit_history
        ORDER BY timestamp DESC
        LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "timestamp": r[0],
            "entered": r[1],
            "exited": r[2],
            "people_inside": r[3],
            "occupied_tables": r[4],
            "free_tables": r[5],
        }
        for r in rows
    ]

def get_daily_stats(date: str):
    conn = connect_db()
    if not conn:
        return None

    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            SUM(entered),
            SUM(exited),
            MAX(people_inside),
            MIN(people_inside)
        FROM visit_history
        WHERE DATE(timestamp) = %s
    """, (date,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "date": date,
        "entered_total": row[0] or 0,
        "exited_total": row[1] or 0,
        "max_inside": row[2] or 0,
        "min_inside": row[3] or 0
    }

def generate_daily_report(date: str):
    stats = get_daily_stats(date)
    if not stats:
        return

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO daily_reports(date, entered_total, exited_total, max_inside, min_inside)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (date) DO UPDATE
        SET entered_total = EXCLUDED.entered_total,
            exited_total = EXCLUDED.exited_total,
            max_inside = EXCLUDED.max_inside,
            min_inside = EXCLUDED.min_inside;
    """, (
        stats["date"],
        stats["entered_total"],
        stats["exited_total"],
        stats["max_inside"],
        stats["min_inside"]
    ))

    conn.commit()
    cursor.close()
    conn.close()

