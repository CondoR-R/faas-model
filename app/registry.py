"""Реестр функций — JSON-файл с потокобезопасным доступом."""
from __future__ import annotations

import json
from pathlib import Path
from threading import Lock


class Registry:
    def __init__(self, path: str) -> None:
        """Запоминает путь к JSON-файлу, устанавливает мьтютекс
        для избежания гонки процессов. Если файла нет по указанному
        пути, создает пустой файл с {}.

        params:
            path - путь к JSON-файлу с реестром функций
        """
        self.path = Path(path)
        self._lock = Lock()
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict:
        """Чтение файла. Читает файл целиком как строку и парсит 
        JSON в словарь. Результат — словарь вида 
        {имя_функции: спецификация}.

        return: словарь с доступными функциями
        """
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        """Запись в файл. Полностью перезаписывает файл

        params:
            data - словарь с данными о новой функции
        """
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def list(self) -> list[dict]:
        """Получение списка всех функций

        return: список доступных функций
        """
        with self._lock:
            return list(self._load().values())

    def get(self, name: str) -> dict | None:
        """Получение одной функции

        return: словарь с информацией о функции либо None, если
        такой функции нет в реестре
        """
        with self._lock:
            return self._load().get(name)

    def add(self, spec: dict) -> None:
        """Добавление новой функции"""
        with self._lock:
            data = self._load()
            data[spec["name"]] = spec
            self._save(data)

    def remove(self, name: str) -> bool:
        """Удаление функции

        return: True — удалено, False — не найдено
        """
        with self._lock:
            data = self._load()
            if name not in data:
                return False
            del data[name]
            self._save(data)
            return True
