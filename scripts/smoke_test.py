"""Проверка всех ключевых сценариев. Требует запущенного сервера на 127.0.0.1:8000."""
import concurrent.futures

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=30.0) as c:
        # Получение списка функций
        r = c.get("/functions")
        print(f"1) GET /functions -> {r.status_code}, {len(r.json())} функций")

        # вызов функции hello
        r = c.post("/functions/hello/invoke", json={"name": "Alice"})
        print(f"2) hello        -> {r.status_code} {r.json()}")

        # вызов функции slow
        r = c.post("/functions/slow/invoke", json={"seconds": 5})
        print(f"3) slow (timeout ожидается 504) -> {r.status_code} {r.json()['status']}")

        # вызов функции error
        r = c.post("/functions/error/invoke", json={})
        print(f"4) error (ожидается 500) -> {r.status_code} {r.json()['error']['type']}")

        # вызов несуществующей функции
        r = c.post("/functions/missing/invoke", json={})
        print(f"5) missing (ожидается 404) -> {r.status_code}")

        # параллельные вызовы
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            codes = list(pool.map(
                lambda _: c.post("/functions/hello/invoke", json={}).status_code,
                range(10),
            ))
        print(f"6) 10 параллельных hello -> {codes}")

        # добавление новой функции
        r = c.post(
            "/functions",
            json={
                "name": "cpu2",
                "module": "functions.cpu",
                "handler": "handler",
                "timeout": 3.0,
            },
        )
        print(f"7) register cpu2 -> {r.status_code}")

        # удаление функции
        r = c.delete("/functions/cpu2")
        print(f"8) delete cpu2   -> {r.status_code}")


if __name__ == "__main__":
    main()
