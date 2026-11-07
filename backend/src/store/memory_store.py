"""内存存储：默认后端，适合单进程部署与本地联调。"""
from __future__ import annotations

import logging
import threading
from datetime import timedelta
from typing import Optional

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

MAX_ANALYSES = 500
MAX_SESSIONS = 2000


class MemoryStore(AnalysisStore):
    backend_name = "memory"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._analyses: dict[str, StoredAnalysis] = {}
        self._sessions: dict[str, StoredSession] = {}

    # ---- 内部清理 ----
    def _purge(self, now) -> None:
        for key in [k for k, v in self._analyses.items() if v.is_expired(now)]:
            self._analyses.pop(key, None)
        for key in [k for k, v in self._sessions.items() if v.is_expired(now)]:
            self._sessions.pop(key, None)

    def _evict_if_needed(self) -> None:
        while len(self._analyses) > MAX_ANALYSES:
            oldest = min(self._analyses.values(), key=lambda r: r.created_at)
            self._analyses.pop(oldest.analysis_id, None)
        while len(self._sessions) > MAX_SESSIONS:
            oldest = min(self._sessions.values(), key=lambda s: s.updated_at)
            self._sessions.pop(oldest.session_id, None)

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
        with self._lock:
            self._purge(now)
            record = StoredAnalysis(
                analysis_id=analysis_id or new_id(),
                client_id=client_id,
                report=deep_copy(report),
                conversation=deep_copy(conversation),
                created_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            self._analyses[record.analysis_id] = record
            self._evict_if_needed()
            return record

    def get_analysis(self, analysis_id: str, client_id: Optional[str] = None) -> StoredAnalysis:
        now = utcnow()
        with self._lock:
            record = self._analyses.get(analysis_id)
            if record is None:
                raise RecordNotFound(f"找不到分析报告 {analysis_id}。")
            if record.is_expired(now):
                self._analyses.pop(analysis_id, None)
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
        with self._lock:
            self._purge(now)
            if session_id:
                session = self._sessions.get(session_id)
                if session is not None:
                    if session.is_expired(now):
                        self._sessions.pop(session_id, None)
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
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            self._sessions[session.session_id] = session
            self._evict_if_needed()
            return session

    def append_session_messages(
        self,
        session_id: str,
        messages: list[dict],
        ttl_seconds: int,
        client_id: Optional[str] = None,
    ) -> StoredSession:
        now = utcnow()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise RecordNotFound(f"找不到会话 {session_id}。")
            if client_id is not None:
                check_access(session.analysis_id, session.client_id, client_id)
            session.messages.extend(deep_copy({"items": messages})["items"])
            session.updated_at = now
            session.expires_at = now + timedelta(seconds=ttl_seconds)
            return session
