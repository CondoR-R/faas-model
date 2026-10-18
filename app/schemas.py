"""Pydantic схемы запросов"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FunctionSpec(BaseModel):
    """Схема метаданных функции"""
    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-_]*$")
    module: str = Field(..., description="Python-путь модуля, например functions.hello")
    handler: str = Field("handler", description="Имя вызываемой функции внутри модуля")
    timeout: float = Field(5.0, gt=0, le=900, description="Лимит времени в секундах")


class InvokeResult(BaseModel):
    """Схема ответа после успешного выполнения фунции"""
    status: str
    result: Any = None
    duration_ms: float
    error: dict | None = None
