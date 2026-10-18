"""Точка входа в приложение и API-шлюз"""
from __future__ import annotations

import importlib
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.executor import execute
from app.registry import Registry
from app.schemas import FunctionSpec, InvokeResult

# создание приложения
app = FastAPI(
    title="FaaS Model",
    version="0.1.0",
    description="Учебная on-premise модель Function as a Service",
)

# создание реестра
registry = Registry("registry.json")


@app.get("/")
def root() -> dict:
    """Корневой эндпоинт.
    
    return: информация о сервисе
    """
    return {
        "service": "faas-model",
        "version": "0.1.0",
        "endpoints": [
            "GET  /functions",
            "GET  /functions/{name}",
            "POST /functions",
            "DELETE /functions/{name}",
            "POST /functions/{name}/invoke",
        ],
    }


@app.get("/functions")
def list_functions() -> list[dict]:
    """Получение списка доступных функций

    return: список метаданных функций"""
    return registry.list()


@app.get("/functions/{name}")
def get_function(name: str) -> dict:
    """Получение метаданных о функции

    params:
        name - название функции

    raise: HTTPException, если функция не найдена в реестре

    return: метаданные о функции
    """
    spec = registry.get(name)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Function '{name}' not found")
    return spec


@app.post("/functions", status_code=201)
def register_function(spec: FunctionSpec) -> dict:
    """Регистрация фунции в реестре

    params:
        spec - метаданные функции

    raise: HTTPException, при ошибки добавлении функции в реестре 
           (не существует модуля или фунции)

    return: информация о сохраненной функции
    """
    try:
        module = importlib.import_module(spec.module)
        getattr(module, spec.handler)
    except (ImportError, AttributeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid function spec: {exc}",
        ) from exc
    registry.add(spec.model_dump())
    return spec.model_dump()


@app.delete("/functions/{name}", status_code=204)
def unregister_function(name: str) -> None:
    """Удаление функции из реестра

    params:
        name - название фунции

    raise: HTTPException, если фунция не найдена
    """
    if not registry.remove(name):
        raise HTTPException(status_code=404, detail=f"Function '{name}' not found")


@app.post("/functions/{name}/invoke")
def invoke(name: str, event: dict[str, Any] | None = None):
    """Вызов функции.

    params:
        name - имя функции
        event - тело запроса

    raise: HTTPException, если фунция не найдена

    return:
        InvokeResult, при успешном выполнении функции
        JSONResponse, при превышении времени ожидания или при ошибке внутри функции
    """
    # поиск фунции в реестре
    spec = registry.get(name)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Function '{name}' not found")

    # запуск функции через execute
    outcome = execute(
        module=spec["module"],
        handler=spec["handler"],
        event=event or {},
        timeout=float(spec["timeout"]),
    )
    duration_ms = round(outcome["duration"] * 1000, 2)

    # успешное выполнение функции
    if outcome["status"] == "ok":
        return InvokeResult(
            status="ok", result=outcome["payload"], duration_ms=duration_ms
        )

    # превышен лимит ожидания
    if outcome["status"] == "timeout":
        return JSONResponse(
            status_code=504,
            content=InvokeResult(
                status="timeout",
                error=outcome["payload"],
                duration_ms=duration_ms,
            ).model_dump(),
        )

    # ошибка внутри функции
    return JSONResponse(
        status_code=500,
        content=InvokeResult(
            status="error",
            error=outcome["payload"],
            duration_ms=duration_ms,
        ).model_dump(),
    )
