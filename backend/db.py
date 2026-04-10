from __future__ import annotations

from functools import lru_cache
from typing import Any

from backend.config import get_settings


class DatabaseConnectionError(RuntimeError):
    pass


def is_database_exception(exc: Exception) -> bool:
    try:
        from pymongo.errors import PyMongoError
    except ModuleNotFoundError:
        return False

    return isinstance(exc, PyMongoError)


@lru_cache(maxsize=1)
def get_client() -> Any:
    settings = get_settings()
    try:
        from pymongo import MongoClient
    except ModuleNotFoundError as exc:
        raise DatabaseConnectionError(
            "pymongo is not installed. Install backend dependencies before starting the API."
        ) from exc

    return MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=settings.mongodb_timeout_ms,
        connectTimeoutMS=settings.mongodb_timeout_ms,
    )


def get_database() -> Any:
    settings = get_settings()
    return get_client()[settings.mongodb_db]
