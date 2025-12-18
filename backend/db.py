import psycopg2
from datetime import datetime
from typing import List, Dict, Any
import os

# конфигурация подключения постгрес тут
DB_NAME = os.getenv("POSTGRES_DB", "stolovka_db")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# константы проекта для расчетов
DEFAULT_TABLE_CAPACITY = 3
TOTAL_TABLES = 20  # общее число столов в базе


def redistribute_overflow_in_columns(occupancy_list: List[int], table_capacity: int) -> List[int]:
    """перераспределение переполнения по колонкам"""
    if table_capacity <= 0:
        return list(occupancy_list)

    n = len(occupancy_list)
    if n == 0:
        return []

    out = list(occupancy_list)

    def _apply_column(ids_top_to_bottom: List[int]):
        # фильтруем ид по длине
        ids = [i for i in ids_top_to_bottom if 1 <= i <= n]
        if len(ids) <= 1:
            return

        # переносим переполнение вниз столбца
        for k in range(len(ids) - 1):
            table_id = ids[k]
            idx = table_id - 1
            occ = out[idx]
            if occ <= table_capacity:
                continue

            overflow = occ - table_capacity
            out[idx] = table_capacity

            next_id = ids[k + 1]
            out[next_id - 1] += overflow

        # переполнение снизу переносим вверх
        last_id = ids[-1]
        last_idx = last_id - 1
        last_occ = out[last_idx]
        if last_occ <= table_capacity:
            return

        overflow = last_occ - table_capacity
        out[last_idx] = table_capacity

        for k in range(len(ids) - 2, -1, -1):
            if overflow <= 0:
                break
            table_id = ids[k]
            idx = table_id - 1
            space = table_capacity - out[idx]
            if space <= 0:
                continue
            add = min(space, overflow)
            out[idx] += add
            overflow -= add

        if overflow > 0:
            out[last_idx] += overflow

    _apply_column(list(range(1, 11)))   # правая колонка интерфейса столов
    _apply_column(list(range(11, 19)))  # левая колонка интерфейса столов
    return out

# утилиты работы с бд тут

def connect_db():
    """подключаемся к постгрес базе"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        # логируем ошибку без выхода
        print(
            f"ERROR: Failed to connect to PostgreSQL at {DB_HOST}:{DB_PORT}. "
            f"Check server status and credentials. DETAILS: {e}"
        )
        return None
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None

# инициализация таблиц базы данных

def init_db():
    """инициализация таблиц в базе"""
    conn = connect_db()
    
    if conn is None: 
        print("INFO: Skipping DB initialization due to connection error.")
        return
        
    cursor = conn.cursor()
    
    try:
        # создаем таблицу общей статистики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS current_status (
                id INTEGER PRIMARY KEY,
                people_inside INTEGER NOT NULL,
                free_tables INTEGER NOT NULL,
                last_update TIMESTAMP WITHOUT TIME ZONE NOT NULL
            )
        ''')
        
        # создаем таблицу статуса столов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS table_status (
                id INTEGER PRIMARY KEY,
                occupied_seats INTEGER NOT NULL DEFAULT 0
            )
        ''')

        # создаем таблицу истории визитов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visit_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                entered INTEGER NOT NULL,
                exited INTEGER NOT NULL,
                people_inside INTEGER NOT NULL,
                occupied_tables INTEGER NOT NULL,
                free_tables INTEGER NOT NULL
            )
        ''')
        
        # создаем таблицу дневных отчетов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_reports (
                date DATE PRIMARY KEY,
                entered_total INTEGER NOT NULL,
                exited_total INTEGER NOT NULL,
                max_inside INTEGER NOT NULL,
                min_inside INTEGER NOT NULL
            )
        ''')

        # инициализируем строку общей статистики
        cursor.execute("SELECT id FROM current_status WHERE id=1")
        if not cursor.fetchone():
            initial_free_tables = TOTAL_TABLES * DEFAULT_TABLE_CAPACITY
            cursor.execute(
                "INSERT INTO current_status (id, people_inside, free_tables, last_update) VALUES (1, 0, %s, NOW())",
                (initial_free_tables,)
            )
            
        # инициализируем строки всех столов
        for i in range(1, TOTAL_TABLES + 1):
            cursor.execute("SELECT id FROM table_status WHERE id = %s", (i,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO table_status (id, occupied_seats) VALUES (%s, 0)", (i,))

        conn.commit()
        
        print(f"INFO: PostgreSQL tables initialized successfully for database: {DB_NAME}")
        
    except Exception as e:
        print(f"FATAL ERROR: An unexpected error occurred during DB initialization: {e}")
        conn.rollback()
        return
        
    finally:
        cursor.close()
        conn.close()

# обновление статуса столов из мл

def update_detailed_tables_status(occupancy_list: List[int], table_capacity: int) -> bool:
    """обновляем статус столов из мл"""
    conn = connect_db()
    if conn is None: 
        return False
        
    cursor = conn.cursor()
    
    try:
        print("DEBUG DB: Stage 1 - Start calculation.") 
        
        adjusted_occupancy_list = redistribute_overflow_in_columns(occupancy_list, table_capacity)

        total_occupied_seats = sum(adjusted_occupancy_list)
        total_tables = len(adjusted_occupancy_list)
        total_capacity = total_tables * table_capacity
        free_tables_count = max(0, total_capacity - total_occupied_seats)
        
        print("DEBUG DB: Stage 2 - Calculated stats.")

        # обновляем таблицу статуса столов
        for idx, occupied in enumerate(adjusted_occupancy_list):
            table_id = idx + 1 
            cursor.execute("""
                INSERT INTO table_status (id, occupied_seats) 
                VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE 
                SET occupied_seats = EXCLUDED.occupied_seats
            """, (table_id, occupied))
        
        print("DEBUG DB: Stage 3 - Table statuses updated.")
        
        # обновляем общую строку статуса
        cursor.execute("""
            UPDATE current_status SET 
            people_inside = %s, 
            free_tables = %s, 
            last_update = NOW() 
            WHERE id = 1
        """, (total_occupied_seats, free_tables_count))
        
        # пишем запись в историю
        occupied_tables_count = sum(1 for occupied in adjusted_occupancy_list if occupied > 0) 
        
        cursor.execute("""
            INSERT INTO visit_history(
                timestamp, entered, exited, people_inside, occupied_tables, free_tables
            )
            VALUES (NOW(), %s, %s, %s, %s, %s)
        """, (0, 0, total_occupied_seats, occupied_tables_count, free_tables_count)) 
        
        conn.commit()
        
        print("DEBUG DB: Stage 4 - Commit successful. Returning True.")
        return True
        
    except Exception as e:
        print(f"DB Error in update_detailed_tables_status: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

# чтение статуса для фронта

def get_detailed_status(table_capacity: int) -> Dict[str, Any]:
    """читаем статус столов для интерфейса"""
    conn = connect_db()
    if conn is None:
        return None
    cursor = conn.cursor()
    
    try:
        # читаем общую статистику из бд
        cursor.execute("SELECT people_inside, free_tables, last_update FROM current_status WHERE id=1")
        overall_data = cursor.fetchone()
        
        # читаем статус столов из бд
        cursor.execute("SELECT id, occupied_seats FROM table_status ORDER BY id")
        table_rows = cursor.fetchall()
        
        tables_list = []
        
        if table_rows:
            for row in table_rows:
                table_id = row[0]
                occupied = row[1]
                
                # вычисляем цвет статуса стола
                if occupied == 0:
                    color = "green"
                elif occupied < table_capacity:
                    color = "yellow"
                else:
                    color = "red"
                
                tables_list.append({
                    "table_id": table_id,
                    "occupied": occupied,
                    "capacity": table_capacity,
                    "status_color": color
                })
        
        last_update_value = overall_data[2] if overall_data else None
        if last_update_value is None:
            last_update_str = "N/A"
        elif hasattr(last_update_value, "strftime"):
            last_update_str = last_update_value.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # совместимость старого формата времени
            last_update_str = str(last_update_value)

        return {
            "overall_inside": overall_data[0] if overall_data else 0,
            "total_capacity": len(table_rows) * table_capacity,
            "tables": tables_list,
            "last_update": last_update_str,
        }
    except Exception as e:
        print(f"DB Error in get_detailed_status: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


# старые функции для совместимости

def update_status(entered: int, exited: int, occupied_tables: int):
    """
    (Legacy) Обновляет статус на основе приращений (entered/exited). 
    """
    conn = connect_db()
    if not conn:
        return False

    cursor = conn.cursor()

    try:
        # читаем текущее число людей
        cursor.execute("SELECT people_inside FROM current_status WHERE id = 1")
        row = cursor.fetchone()
        current_people = row[0] if row else 0

        # считаем новое число людей
        new_people = current_people + entered - exited
        if new_people < 0:
            new_people = 0 

        # считаем число свободных столов
        free_tables = TOTAL_TABLES - occupied_tables

        # обновляем таблицу общей статистики
        cursor.execute("""
            UPDATE current_status
            SET people_inside=%s,
                free_tables=%s,
                last_update=NOW()
            WHERE id = 1
        """, (new_people, free_tables))

        # пишем запись в историю
        cursor.execute("""
            INSERT INTO visit_history(
                timestamp, entered, exited, people_inside, occupied_tables, free_tables
            )
            VALUES (NOW(), %s, %s, %s, %s, %s)
        """, (entered, exited, new_people, occupied_tables, free_tables))

        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error in update_status: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def get_current_status():
    conn = connect_db()
    if conn is None:
        return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT people_inside, free_tables, last_update FROM current_status WHERE id=1")
        row = cursor.fetchone()
        if row:
            return {
                "people_inside": row[0],
                "free_tables": row[1],
                "last_update": row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else "N/A"
            }
        return None
    finally:
        cursor.close()
        conn.close()


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
    
    # форматируем время для ответа
    results = [
        {
            "timestamp": r[0].strftime('%Y-%m-%d %H:%M:%S'),
            "entered": r[1],
            "exited": r[2],
            "people_inside": r[3],
            "occupied_tables": r[4],
            "free_tables": r[5],
        }
        for r in rows
    ]

    cursor.close()
    conn.close()

    return results

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
            MIN(people_inside),
            AVG(people_inside)
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
        "min_inside": row[3] or 0,
        "avg_inside": round(row[4], 2) if row[4] else 0
    }


def get_weekday_hourly_occupancy(days_back: int = 30, start_hour: int = 9, end_hour: int = 16) -> Dict[str, Any]:
    """средняя занятость по дням"""
    conn = connect_db()
    if not conn:
        return None

    hours = list(range(start_hour, end_hour + 1))
    weekday_labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]

    # буферы значений по часам
    buckets: Dict[tuple[int, int], List[int]] = {}
    for w in range(6):
        for h in hours:
            buckets[(w, h)] = []

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT timestamp, people_inside
            FROM visit_history
            WHERE timestamp >= NOW() - (%s || ' days')::interval
            """,
            (days_back,),
        )
        rows = cursor.fetchall()

        for ts, people_inside in rows:
            if ts is None:
                continue

            weekday_idx = ts.weekday()  # понедельник это нулевой индекс
            if weekday_idx < 0 or weekday_idx > 5:
                continue

            hour = ts.hour
            if hour < start_hour or hour > end_hour:
                continue

            try:
                buckets[(weekday_idx, hour)].append(int(people_inside))
            except Exception:
                continue

        occupancy_by_day: Dict[str, List[int]] = {}
        for w_idx, label in enumerate(weekday_labels):
            values: List[int] = []
            for h in hours:
                vals = buckets[(w_idx, h)]
                if not vals:
                    values.append(0)
                else:
                    values.append(int(round(sum(vals) / len(vals))))
            occupancy_by_day[label] = values

        # для ui показываем только столы 1..18 по 3 места
        ui_total_capacity = 18 * DEFAULT_TABLE_CAPACITY

        return {
            "days": weekday_labels,
            "hours": [str(h).zfill(2) for h in hours],
            "occupancy": occupancy_by_day,
            "total_capacity": ui_total_capacity,
        }
    finally:
        cursor.close()
        conn.close()

def generate_daily_report(date: str):
    conn = connect_db()
    if not conn:
        return False
    
    stats = get_daily_stats(date)
    if not stats:
        return False

    cursor = conn.cursor()

    try:
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
        return True
    except Exception as e:
        print(f"DB Error in generate_daily_report: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()