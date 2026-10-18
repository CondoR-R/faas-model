"""Изолированный запуск функций с жёстким ограничением времени."""
from __future__ import annotations

import importlib
import multiprocessing as mp
import queue
import time
import traceback
from typing import Any


TERMINATE_TIMEOUT = 1


def execute(module: str, handler: str, event: Any, timeout: float) -> dict:
    """Запускает функцию в отдельном процессе с ограничением `timeout` секунд.

    params:
        module - имя модуля
        handler - название функции в модуле
        event - данные для запуска (словарь-событие)
        timeout - ограничение времени выполнения

    return: словарь с результатом выполнения запроса
    """
    q: mp.Queue = mp.Queue() # межпроцессорная очередь
    # дочерний процесс, выполняющий функцию _worker
    proc = mp.Process(target=_worker, args=(module, handler, event, q), daemon=True)
    started = time.perf_counter() # фиксация времени до старта
    proc.start() # запуск дочернего процесса

    # Ожидание результата с таймаутом
    try:
        status, payload = q.get(timeout=timeout) # блокирующее чтение из очереди
    except queue.Empty:
        _terminate(proc) # принудительно убиваем дочерний процесс
        return {
            "status": "timeout",
            "payload": {
                "type": "TimeoutError",
                "message": f"Execution exceeded {timeout} s",
            },
            "duration": time.perf_counter() - started,
        }

    _drain(proc) # завершение процесса
    return {
        "status": status,
        "payload": payload,
        "duration": time.perf_counter() - started,
    }


def _worker(module: str, handler: str, event: Any, q: mp.Queue) -> None:
    """Выполняется в дочернем процессе: импортирует функцию и запускает её.

    params:
        module - имя модуля
        handler - название функции из модуля
        event - данные для запуска (словарь-событие)
        q - межпроцессная очередь
    """
    try:
        mod = importlib.import_module(module) # динамический импорт
        fn = getattr(mod, handler)
        result = fn(event)
        
        # передача данных в родительский процесс
        try:
            q.put(("ok", result))
        except Exception as exc:  # несериализуемый результат
            q.put((
                "error",
                {
                    "type": type(exc).__name__,
                    "message": f"Unserializable result: {exc}",
                    "traceback": traceback.format_exc(),
                },
            ))
    except BaseException as exc:  # ловим любое падение функции
        q.put((
            "error",
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        ))


def _drain(proc: mp.Process) -> None:
    """Корректное завершение процесса

    params:
        proc - завершаемый процесс
    """
    # самостоятельное завершение процесса
    proc.join(timeout=TERMINATE_TIMEOUT)

    # завершение процесса
    _terminate(proc)


def _terminate(proc: mp.Process) -> None:
    """Принудительное завершение
    
    params:
        proc - завершаемый процесс
    """
    # завершение процесса
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=TERMINATE_TIMEOUT)

    # принудительное завершение
    if proc.is_alive():
        proc.kill()
        proc.join()
