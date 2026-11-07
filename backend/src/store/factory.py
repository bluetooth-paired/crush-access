"""存储工厂：按环境变量选择后端，失败时安全降级。"""
from __future__ import annotations

import logging
from functools import lru_cache

from settings import get_settings
from store.base import AnalysisStore
from store.memory_store import MemoryStore

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_store() -> AnalysisStore:
    settings = get_settings()
    backend = (settings.store_backend or "memory").lower()

    if backend == "postgres":
        if not settings.database_url:
            logger.warning("STORE_BACKEND=postgres 但未提供 DATABASE_URL，已降级为 memory。")
            return MemoryStore()
        try:
            from store.postgres_store import PostgresStore

            return PostgresStore(settings.database_url)
        except Exception as e:  # noqa: BLE001 - 降级必须不影响服务可用性
            logger.warning("postgres 存储初始化失败，已降级为 memory：%s", type(e).__name__)
            return MemoryStore()

    return MemoryStore()


def reset_store() -> None:
    """测试用：清空工厂缓存。"""
    get_store.cache_clear()
