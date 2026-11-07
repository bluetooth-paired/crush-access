"""运行配置：全部通过环境变量注入，禁止把密钥写入源码。

关键环境变量：
- LLM_API_KEY / LLM_BASE_URL / LLM_MODEL      显式指定 OpenAI 兼容模型服务
- DEEPSEEK_API_KEY                            使用 DeepSeek（base 默认 https://api.deepseek.com/v1）
- MOONSHOT_API_KEY                            使用 Kimi / Moonshot（base 默认 https://api.moonshot.cn/v1）
- ANALYSIS_TTL_SECONDS                       分析报告有效期（默认 7 天）
- STORE_BACKEND                              memory | postgres
- DATABASE_URL / PGDATABASE_URL              postgres 后端连接串
- CORS_ALLOW_ORIGINS                         逗号分隔的额外允许来源
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from env_loader import load_project_env

# 必须在读取任何环境变量之前加载 .env（幂等，找不到文件时静默跳过）
load_project_env()

APP_NAME = "crush-access-agent-backend"
APP_VERSION = "1.1.1"


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(str(raw).strip())
    except ValueError:
        return default
    return value if value > 0 else default


def _offset_env(name: str, default: int) -> int:
    """时区偏移（小时），允许 -14 ~ +14，非法值回退默认。"""
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(str(raw).strip())
    except ValueError:
        return default
    return value if -14 <= value <= 14 else default


def _str_env(name: str, default: str = "") -> str:
    raw = os.getenv(name)
    return raw.strip() if raw and raw.strip() else default


def _list_env(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    items = tuple(item.strip() for item in raw.split(",") if item.strip())
    return items or default


@dataclass(frozen=True)
class Settings:
    app_name: str = APP_NAME
    version: str = APP_VERSION
    # 报告与会话有效期
    analysis_ttl_seconds: int = 7 * 24 * 3600
    session_ttl_seconds: int = 7 * 24 * 3600
    # 输入保护
    max_messages_per_request: int = 3000
    max_message_chars: int = 4000
    max_advisor_message_chars: int = 2000
    max_advisor_turns: int = 60
    # 存储后端
    store_backend: str = "memory"
    database_url: str = ""
    # CORS
    cors_allow_origins: tuple[str, ...] = ()
    cors_allow_origin_regex: str = r"https://([a-zA-Z0-9-]+\.)*github\.io"
    cors_allow_credentials: bool = False
    # 模型
    llm_timeout_seconds: int = 120
    llm_max_retries: int = 3
    # 证据检索
    evidence_limit: int = 8
    # 无时区时间戳的默认时区偏移（小时）：微信导出通常是本地时间，默认 +8
    naive_tz_offset_hours: int = 8
    # 军师回复长度上限（超出时按句号截断，并在 ai_config 中标记）
    max_advisor_reply_chars: int = 500


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        analysis_ttl_seconds=_int_env("ANALYSIS_TTL_SECONDS", 7 * 24 * 3600),
        session_ttl_seconds=_int_env("SESSION_TTL_SECONDS", 7 * 24 * 3600),
        max_messages_per_request=_int_env("MAX_MESSAGES_PER_REQUEST", 3000),
        max_message_chars=_int_env("MAX_MESSAGE_CHARS", 4000),
        max_advisor_message_chars=_int_env("MAX_ADVISOR_MESSAGE_CHARS", 2000),
        max_advisor_turns=_int_env("MAX_ADVISOR_TURNS", 60),
        store_backend=_str_env("STORE_BACKEND", "memory").lower(),
        database_url=_str_env("DATABASE_URL") or _str_env("PGDATABASE_URL"),
        cors_allow_origins=_list_env(
            "CORS_ALLOW_ORIGINS",
            (
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5500",
                "http://localhost:8080",
            ),
        ),
        cors_allow_origin_regex=_str_env(
            "CORS_ALLOW_ORIGIN_REGEX", r"https://([a-zA-Z0-9-]+\.)*github\.io"
        ),
        cors_allow_credentials=_str_env("CORS_ALLOW_CREDENTIALS", "false").lower() == "true",
        llm_timeout_seconds=_int_env("LLM_TIMEOUT_SECONDS", 120),
        llm_max_retries=_int_env("LLM_MAX_RETRIES", 3),
        evidence_limit=_int_env("ADVISOR_EVIDENCE_LIMIT", 8),
        naive_tz_offset_hours=_offset_env("ASSUME_NAIVE_TZ_OFFSET_HOURS", 8),
        max_advisor_reply_chars=_int_env("MAX_ADVISOR_REPLY_CHARS", 500),
    )
