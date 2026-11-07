"""PostgreSQL 存储：多进程/重启后仍可读，适合生产部署。

通过 `STORE_BACKEND=postgres` + `DATABASE_URL`（或 `PGDATABASE_URL`）启用；
连接失败时由 factory 自动降级为内存存储，并在 /health 中如实暴露实际后端。
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from store.base import (
    AnalysisStore,
    RecordExpired,
    RecordNotFound,
    StoredAnalysis,
    StoredSession,
    check_access,
    deep_copy,
    new_id,
    utcnow,
)

logger = logging.getLogger(__name__)

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS crush_analyses (
        analysis_id TEXT PRIMARY KEY,
        client_id   TEXT NOT NULL,
        report      JSONB NOT NULL,
        conversation JSONB NOT NULL,
        created_at  TIMESTAMPTZ NOT NULL,
        expires_at  TIMESTAMPTZ NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_crush_analyses_expires ON crush_analyses (expires_at)",
    """
    CREATE TABLE IF NOT EXISTS crush_advisor_sessions (
        session_id  TEXT PRIMARY KEY,
        analysis_id TEXT NOT NULL,
        client_id   TEXT NOT NULL,
        messages    JSONB NOT NULL DEFAULT '[]'::jsonb,
        created_at  TIMESTAMPTZ NOT NULL,
        updated_at  TIMESTAMPTZ NOT NULL,
        expires_at  TIMESTAMPTZ NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_crush_sessions_expires ON crush_advisor_sessions (expires_at)",
]


class PostgresStore(AnalysisStore):
    backend_name = "postgres"

    def __init__(self, database_url: str) -> None:
        self._engine: Engine = create_engine(database_url, pool_pre_ping=True, future=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._engine.begin() as conn:
            for ddl in _DDL:
                conn.execute(text(ddl))
        logger.info("postgres_store_schema_ready")

    # ---- 分析报告 ----
    def save_analysis(
        self,
        report: dict,
        conversation: dict,
        client_id: str,
        ttl_seconds: int,
        analysis_id: Optional[str] = None,
    ) -> StoredAnalysis:
        now = utcnow()
        record = StoredAnalysis(
            analysis_id=analysis_id or new_id(),
            client_id=client_id,
            report=deep_copy(report),
            conversation=deep_copy(conversation),
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM crush_analyses WHERE expires_at <= :now"), {"now": now})
            conn.execute(
                text(
                    """
                    INSERT INTO crush_analyses
                        (analysis_id, client_id, report, conversation, created_at, expires_at)
                    VALUES (:analysis_id, :client_id, CAST(:report AS JSONB),
                            CAST(:conversation AS JSONB), :created_at, :expires_at)
                    """
                ),
                {
                    "analysis_id": record.analysis_id,
                    "client_id": record.client_id,
                    "report": json.dumps(record.report, ensure_ascii=False),
                    "conversation": json.dumps(record.conversation, ensure_ascii=False),
                    "created_at": record.created_at,
                    "expires_at": record.expires_at,
                },
            )
        return record

    def get_analysis(self, analysis_id: str, client_id: Optional[str] = None) -> StoredAnalysis:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT analysis_id, client_id, report, conversation, created_at, expires_at "
                    "FROM crush_analyses WHERE analysis_id = :analysis_id"
                ),
                {"analysis_id": analysis_id},
            ).mappings().first()
            if row is None:
                raise RecordNotFound(f"找不到分析报告 {analysis_id}。")

            record = StoredAnalysis(
                analysis_id=row["analysis_id"],
                client_id=row["client_id"],
                report=row["report"],
                conversation=row["conversation"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
            )
            if record.is_expired():
                conn.execute(
                    text("DELETE FROM crush_analyses WHERE analysis_id = :analysis_id"),
                    {"analysis_id": analysis_id},
                )
                raise RecordExpired(f"分析报告 {analysis_id} 已过期，请重新分析。")
            check_access(record.analysis_id, record.client_id, client_id)
            return record

    # ---- 会话 ----
    def get_session(
        self,
        session_id: Optional[str],
        analysis_id: str,
        client_id: str,
        ttl_seconds: int,
    ) -> StoredSession:
        now = utcnow()
        with self._engine.begin() as conn:
            if session_id:
                row = conn.execute(
                    text(
                        "SELECT session_id, analysis_id, client_id, messages, created_at, "
                        "updated_at, expires_at FROM crush_advisor_sessions "
                        "WHERE session_id = :session_id"
                    ),
                    {"session_id": session_id},
                ).mappings().first()
                if row is not None:
                    session = StoredSession(
                        session_id=row["session_id"],
                        analysis_id=row["analysis_id"],
                        client_id=row["client_id"],
                        messages=row["messages"] or [],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        expires_at=row["expires_at"],
                    )
                    if session.is_expired(now):
                        conn.execute(
                            text("DELETE FROM crush_advisor_sessions WHERE session_id = :sid"),
                            {"sid": session_id},
                        )
                        raise RecordExpired(f"会话 {session_id} 已过期，请新建会话。")
                    if session.analysis_id != analysis_id:
                        raise RecordNotFound(
                            f"会话 {session_id} 不属于分析报告 {analysis_id}。"
                        )
                    check_access(session.analysis_id, session.client_id, client_id)
                    return session

                # 显式传入的 session_id 不存在：明确报错，避免静默新建导致上下文丢失或会话固定
                raise RecordNotFound(f"找不到会话 {session_id}，请删除 session_id 后重新开启会话。")

            # 未传 session_id 时由服务端生成，客户端无法指定 ID，天然避免会话固定
            session = StoredSession(
                session_id=new_id(),
                analysis_id=analysis_id,
                client_id=client_id,
                created_at=now,
                updated_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            conn.execute(
                text(
                    "INSERT INTO crush_advisor_sessions "
                    "(session_id, analysis_id, client_id, messages, created_at, updated_at, expires_at) "
                    "VALUES (:session_id, :analysis_id, :client_id, CAST(:messages AS JSONB), "
                    ":created_at, :updated_at, :expires_at)"
                ),
                {
                    "session_id": session.session_id,
                    "analysis_id": session.analysis_id,
                    "client_id": session.client_id,
                    "messages": json.dumps([], ensure_ascii=False),
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "expires_at": session.expires_at,
                },
            )
            return session

    def append_session_messages(
        self,
        session_id: str,
        messages: list[dict],
        ttl_seconds: int,
        client_id: Optional[str] = None,
    ) -> StoredSession:
        now = utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)
        with self._engine.begin() as conn:
            if client_id is not None:
                # 先校验归属再写入，避免无权请求污染他人会话
                owner = conn.execute(
                    text(
                        "SELECT analysis_id, client_id FROM crush_advisor_sessions "
                        "WHERE session_id = :session_id"
                    ),
                    {"session_id": session_id},
                ).mappings().first()
                if owner is None:
                    raise RecordNotFound(f"找不到会话 {session_id}。")
                check_access(owner["analysis_id"], owner["client_id"], client_id)

            row = conn.execute(
                text(
                    "UPDATE crush_advisor_sessions SET "
                    "messages = messages || CAST(:messages AS JSONB), "
                    "updated_at = :now, expires_at = :expires_at "
                    "WHERE session_id = :session_id "
                    "RETURNING session_id, analysis_id, client_id, messages, created_at, "
                    "updated_at, expires_at"
                ),
                {
                    "messages": json.dumps(messages, ensure_ascii=False),
                    "now": now,
                    "expires_at": expires_at,
                    "session_id": session_id,
                },
            ).mappings().first()
            if row is None:
                raise RecordNotFound(f"找不到会话 {session_id}。")
            return StoredSession(
                session_id=row["session_id"],
                analysis_id=row["analysis_id"],
                client_id=row["client_id"],
                messages=row["messages"] or [],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                expires_at=row["expires_at"],
            )
