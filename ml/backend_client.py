from __future__ import annotations

from typing import List, Optional

import requests


def create_session() -> requests.Session:
    """
    отключаем trust_env  чтобы не использовать прокси из окружения
    для надежной связи с бекендом
    """

    session = requests.Session()
    session.trust_env = False
    return session



# СВЯЗЬ ML И БЕКЕНДА: HTTP POST
def post_table_occupancy(
    session: requests.Session,
    url: str,
    status_list: List[int],
    timeout_seconds: float = 0.5,
    debug: bool = True,
) -> Optional[int]:
    """
    отправка статуса столов на бекенд
    возвращает статус http (none при ошибке соединения)
    """

    payload = {"table_occupancy": status_list}

    if debug:
        print(f"DEBUG: ML отправка данных на {url}: {status_list}")

    try:
        # СВЯЗЬ ML И БЕКЕНДА: HTTP REQUEST
        response = session.post(url, json=payload, timeout=timeout_seconds)
        if debug:
            if response.status_code == 200:
                print("бэкенд апдейт: успех (200 OK)")
                if response.text:
                    print(f"DEBUG: Бэкенд ответ: {response.text[:50]}...")
            else:
                print(
                    f"бэкенд апдейт: неудача (статус: {response.status_code}, ответ: {response.text})"
                )
        return int(response.status_code)
    except requests.exceptions.ConnectionError:
        if debug:
            print(
                f"ошибка соединения с бекендом: соединение отклонено fastapi не запущен на {url}?"
            )
        return None
    except requests.exceptions.RequestException as e:
        if debug:
            print(f"ошибка соединения с бекендом: {e}")
        return None
