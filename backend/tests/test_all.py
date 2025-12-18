import json

import db


def _sample_detailed_status():
    return {
        "overall_inside": 3,
        "total_capacity": 6,
        "tables": [
            {"table_id": 1, "occupied": 0, "capacity": 3, "status_color": "green"},
            {"table_id": 2, "occupied": 3, "capacity": 3, "status_color": "red"},
        ],
        "last_update": "2025-12-16 12:34:56",
    }


def test_get_detailed_status_ok(app_client, monkeypatch):
    # детальный статус через api
    import main

    monkeypatch.setattr(main, "get_detailed_status", lambda table_capacity: _sample_detailed_status())

    r = app_client.get("/api/status/detailed")
    assert r.status_code == 200
    body = r.json()
    assert body["overall_inside"] == 3
    assert len(body["tables"]) == 2


def test_root_health_ok(app_client):
    # корневой эндпоинт
    r = app_client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "message" in body


def test_post_tables_update_rejects_invalid_payload_422(app_client):
    # нет поля занятости столов
    # некорректный payload
    r = app_client.post("/api/tables/update", json={"wrong_field": [0, 1, 2]})
    assert r.status_code == 422


def test_post_tables_update_ok(app_client, monkeypatch):
    # обновление статуса столов
    import main

    monkeypatch.setattr(main, "update_detailed_tables_status", lambda occupancy_list, table_capacity: True)
    monkeypatch.setattr(main, "get_detailed_status", lambda table_capacity: _sample_detailed_status())

    r = app_client.post("/api/tables/update", json={"table_occupancy": [0, 1, 2]})
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_post_tables_update_returns_503_when_db_returns_false(app_client, monkeypatch):
    # возврат 503 если бд не обновилась
    import main

    monkeypatch.setattr(main, "update_detailed_tables_status", lambda occupancy_list, table_capacity: False)

    r = app_client.post("/api/tables/update", json={"table_occupancy": [0, 0, 0]})
    assert r.status_code == 503


def test_websocket_sends_initial_status(app_client, monkeypatch):
    # websocket начальный статус
    import main

    monkeypatch.setattr(main, "get_detailed_status", lambda table_capacity: _sample_detailed_status())

    with app_client.websocket_connect("/ws/status") as ws:
        raw = ws.receive_text()
        payload = json.loads(raw)
        assert payload["overall_inside"] == 3
        assert payload["tables"][0]["table_id"] == 1
        ws.send_text("ping")


def test_post_tables_update_triggers_ws_broadcast(app_client, monkeypatch):
    # обновление вызывает broadcast
    import main

    monkeypatch.setattr(main, "update_detailed_tables_status", lambda occupancy_list, table_capacity: True)
    monkeypatch.setattr(main, "get_detailed_status", lambda table_capacity: _sample_detailed_status())

    calls = {"count": 0, "payload": None}

    async def fake_broadcast(data: str):
        calls["count"] += 1
        calls["payload"] = data

    monkeypatch.setattr(main.manager, "broadcast", fake_broadcast)

    r = app_client.post("/api/tables/update", json={"table_occupancy": [0, 1, 2]})
    assert r.status_code == 200
    assert calls["count"] == 1
    assert isinstance(calls["payload"], str)


def test_redistribute_overflow_pushes_downward_in_right_column():
    # переполнение стола 1 вниз
    # переполнение вниз по столбцу
    src = [5, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    out = db.redistribute_overflow_in_columns(src, table_capacity=3)
    assert out == [3, 2, 0, 0, 0, 0, 0, 0, 0, 0]
    assert sum(out) == sum(src)


def test_redistribute_overflow_handles_bottom_by_moving_upward():
    # переполнение снизу двигаем вверх
    # переполнение снизу вверх
    src = [0, 0, 0, 0, 0, 0, 0, 0, 0, 7]
    out = db.redistribute_overflow_in_columns(src, table_capacity=3)
    # остаток идет вверх столами
    assert out == [0, 0, 0, 0, 0, 0, 0, 1, 3, 3]
    assert sum(out) == sum(src)


def test_redistribute_overflow_left_column_11_to_18():
    # левая колонка перенос вниз
    # левая колонка перенос вниз
    src = [0] * 18
    src[10] = 6  # id стола 11 слева
    out = db.redistribute_overflow_in_columns(src, table_capacity=3)
    assert out[10] == 3
    assert out[11] == 3  # сдвиг на стол 12
    assert sum(out) == sum(src)


def test_redistribute_ignores_tables_outside_ui_columns():
    # столы 19 20 без изменений
    # столы вне схемы
    src = [0] * 20
    src[18] = 9  # стол 19 вне схемы
    src[19] = 1  # стол 20 вне схемы
    out = db.redistribute_overflow_in_columns(src, table_capacity=3)
    assert out[18] == 9
    assert out[19] == 1
    assert sum(out) == sum(src)
