# FaaS Model — учебная on-premise реализация Function as a Service

Минимальная модель бессерверной платформы FaaS, разворачиваемая локально.
Принимает HTTP-вызовы, находит функцию в реестре, запускает её в изолированном
процессе с жёстким ограничением времени и возвращает результат.

## Архитектура

```
┌──────────┐  HTTP   ┌──────────────┐  lookup  ┌──────────────┐
│  Client  │ ──────► │  API Gateway │ ───────► │   Registry   │
└──────────┘         │  (FastAPI)   │          │ (registry.   │
                     └──────┬───────┘          │  json)       │
                            │ execute          └──────────────┘
                            ▼
                     ┌──────────────┐
                     │   Executor   │  mp.Process + timeout
                     │ (app/        │  → terminate → 504
                     │  executor.py)│
                     └──────┬───────┘
                            ▼
                     ┌──────────────┐
                     │   Function   │  код из functions/
                     │  (isolated)  │
                     └──────────────┘
```

Слои модели воспроизводят ключевые идеи on-premise FaaS:

- **Ingress / API Gateway** — FastAPI-приложение (`app/main.py`).
- **Control Plane** — реестр функций (`app/registry.py`, JSON).
- **Data Plane / Execution** — изоляция в отдельном процессе (`app/executor.py`).
- **Ограничение времени** — `queue.get(timeout=…)`, при истечении — `terminate()`/`kill()` и HTTP 504.
- **Наблюдаемость** — каждое выполнение возвращает `status`, `duration_ms`, `error.traceback`.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Требуется Python 3.10+ (проверено на 3.14).

## Запуск

```bash
python -m uvicorn app.main:app --reload
```

API доступен на http://127.0.0.1:8000, интерактивная документация — на `/docs`.

## Эндпоинты

| Метод | Путь                         | Назначение                          |
|-------|------------------------------|-------------------------------------|
| GET   | `/`                          | Сводка сервиса                      |
| GET   | `/functions`                 | Список зарегистрированных функций   |
| GET   | `/functions/{name}`          | Метаданные функции                  |
| POST  | `/functions`                 | Зарегистрировать функцию            |
| DELETE| `/functions/{name}`          | Удалить функцию                     |
| POST  | `/functions/{name}/invoke`   | Выполнить функцию                   |

### Примеры

```bash
# вызвать функцию hello
curl -X POST http://127.0.0.1:8000/functions/hello/invoke \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}'
# → {"status":"ok","result":{"message":"Hello, Alice!"},"duration_ms":12.3,"error":null}

# спровоцировать таймаут (лимит функции slow — 2 с)
curl -X POST http://127.0.0.1:8000/functions/slow/invoke \
  -H "Content-Type: application/json" -d '{"seconds": 10}'
# → HTTP 504 {"status":"timeout", ...}

# зарегистрировать новую функцию
curl -X POST http://127.0.0.1:8000/functions \
  -H "Content-Type: application/json" \
  -d '{"name":"cpu","module":"functions.cpu","handler":"handler","timeout":10}'
```

## Тестовые сценарии

Запустите сервер в одном терминале и smoke-тест в другом:

```bash
python scripts/smoke_test.py
```

Проверяются: успешный вызов, таймаут (504), ошибка в функции (500), несуществующая
функция (404), 10 параллельных вызовов, динамическая регистрация и удаление.

## Ограничения модели (отличия от промышленной FaaS)

- Изоляция на уровне процессов, а не контейнеров/VM.
- Холодный старт присутствует всегда (`spawn`/`forkserver` + импорт модуля).
- Нет автомасштабирования и балансировки между узлами.
- Нет аутентификации и квот — это учебная модель, а не production-сервис.

## Лицензия

MIT License. Подробнее см. в файле [LICENSE](LICENSE).
