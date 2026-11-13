#!/usr/bin/env python3
"""
Версия приложения Meeting Processor.

Значение __version__ обновляется при выпуске релиза и должно совпадать с тегом в git.
Переменная окружения APP_VERSION перекрывает его (удобно для сборок и стендов).
"""

import os

__version__ = "0.18"


def get_app_version() -> str:
    """Возвращает версию приложения: APP_VERSION из окружения или __version__"""
    return os.getenv("APP_VERSION", "").strip() or __version__
