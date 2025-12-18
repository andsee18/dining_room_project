# dining_room_project

Проект мониторинга загруженности столовой:

- ML (YOLO) считает людей за столами по видео и шлёт список занятости на backend.
- Backend (FastAPI) сохраняет данные в Postgres и раздаёт обновления по WebSocket/HTTP.
- Frontend (Next.js) показывает план столов и живую загруженность.

# виртуальные окружения

- для backend: .venv (или env)
- для ml: ml310_env (или другое рабочее окружение)
- для frontend: node_modules (npm install в папке frontend)

перед запуском активируйте нужное окружение

# инициализация базы

таблицы создаются автоматически при первом запуске backend. если таблиц нет — просто запускаем backend, он всё создаст

# запуск тестов

перед запуском тестов для backend и ml активировать соответствующее виртуальное окружение


# запуск 


# 1)Запуск postgreSQL

я запускаю в powershell

cd "C:\Program Files\PostgreSQL\18\bin"


.\psql.exe -U ВАШUSER

CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'password';

\q

.\psql.exe -U andrew -d postgres

CREATE DATABASE stolovka_db OWNER postgres;

\q

.\pg_ctl.exe -D "C:\pgdata" start

# 2)Запуск бэк

cd backend

uvicorn main:app --reload

# 3)Запуск ml

C:\Python310\python.exe -m venv ml310_env

.\ml310_env\Scripts\Activate.ps1

pip install numpy opencv-python

pip install requests

pip install ultralytics

python main_detector.py v1.MP4



# 4)проверка

SELECT * FROM table_status; - id стола и скок чел сидит
SELECT * FROM current_status; - общая стата
SELECT * FROM visit_history ORDER BY timestamp DESC LIMIT 20; - история изменений
SELECT * FROM table_status;

# 4)фронт node js

cd frontend
npm install
npm run dev


## Тесты

В проекте тесты разделены по подсистемам (backend / frontend / ml) и держатся максимально простыми: по одному основному файлу тестов на подсистему.

Что используется:

- Backend: `pytest` — быстрый и стандартный для Python/FastAPI, удобно тестировать чистые функции (например, бизнес-логику перераспределения) и API-эндпоинты через тестовый клиент.
- Frontend: `Vitest` + Testing Library (jsdom) — быстро запускается в Node, хорошо подходит для тестирования React-компонентов и логики взаимодействия (HTTP polling/WS URL) без реального браузера.
- ML: `pytest` — позволяет тестировать “чистые” хелперы (геометрия/IoU/dedup/сглаживание) детерминированно, без необходимости гонять YOLO/видео в тестах.

### Backend

cd backend
./env/Scripts/python.exe -m pip install -r requirements-dev.txt
./env/Scripts/python.exe -m pytest -q

### Frontend

cd frontend
npm install
npm test

### ML

cd ml
./ml310_env/Scripts/python.exe -m pip install -r requirements-dev.txt
./ml310_env/Scripts/python.exe -m pytest -q
