import pytest


@pytest.fixture()
def app_client(monkeypatch):
    # импорт внутри фикстуры тестов
    import main
    from fastapi.testclient import TestClient

    # отключаем бд и планировщик
    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(main.scheduler, "start", lambda: None)
    monkeypatch.setattr(main.scheduler, "shutdown", lambda: None)

    return TestClient(main.app)
