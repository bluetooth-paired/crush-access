"""分析报告与会话的存储抽象。

安全设计：
- 每条分析报告绑定创建者 `client_id`，读取时必须携带同一个 `client_id`，
  否则抛出 `RecordForbidden`，避免通过猜 analysis_id 跨用户读取；
- 所有记录都带 `expires_at`，过期后返回 `RecordExpired`（HTTP 410）；
- 存储层只保存报告本身与原始会话，不保存任何模型 Key。
"""
from __future__ import annotations

import copy
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


class StoreError(Exception):
    """存储层异常基类。"""

    code = "STORE_ERROR"


class RecordNotFound(StoreError):
    code = "RECORD_NOT_FOUND"


class RecordExpired(StoreError):
    code = "RECORD_EXPIRED"


class RecordForbidden(StoreError):
    code = "RECORD_FORBIDDEN"


class RecordMissingCredential(StoreError):
    """缺少身份凭据：禁止读取任何分析报告或会话。"""

    code = "RECORD_MISSING_CREDENTIAL"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class StoredAnalysis:
    analysis_id: str
    client_id: str
    report: dict
    conversation: dict
    created_at: datetime
    expires_at: datetime

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        return (now or utcnow()) >= self.expires_at


@dataclass
class StoredSession:
    session_id: str
    analysis_id: str
    client_id: str
    messages: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    expires_at: datetime = field(default_factory=lambda: utcnow() + timedelta(days=7))

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        return (now or utcnow()) >= self.expires_at


class AnalysisStore(ABC):
    """报告 + 会话存储接口。"""

    backend_name = "unknown"

    # ---- 分析报告 ----
    @abstractmethod
    def save_analysis(
        self,
        report: dict,
        conversation: dict,
        client_id: str,
        ttl_seconds: int,
        analysis_id: Optional[str] = None,
    ) -> StoredAnalysis:
        """保存分析报告，返回带有效期的记录。"""

    @abstractmethod
    def get_analysis(self, analysis_id: str, client_id: Optional[str] = None) -> StoredAnalysis:
        """按 ID 读取报告；校验归属与有效期。"""

    # ---- 军师会话 ----
    @abstractmethod
    def get_session(
        self,
        session_id: Optional[str],
        analysis_id: str,
        client_id: str,
        ttl_seconds: int,
    ) -> StoredSession:
        """读取会话；session_id 为空时创建新会话，非空但不存在时抛 RecordNotFound。"""

    @abstractmethod
    def append_session_messages(
        self,
        session_id: str,
        messages: list[dict],
        ttl_seconds: int,
        client_id: Optional[str] = None,
    ) -> StoredSession:
        """追加多轮对话消息并刷新有效期；client_id 非空时做归属校验。"""


def check_access(record_analysis_id: str, record_client_id: str, client_id: Optional[str]) -> None:
    """归属校验：**必须**携带与创建时一致的 client_id 才能读取。

    安全策略（默认拒绝）：
    - 缺少 client_id / 空白字符串 → RecordMissingCredential（HTTP 401）
    - client_id 不匹配         → RecordForbidden（HTTP 403）
    - 仅有 analysis_id 而无凭据，不允许读取他人报告，避免凭据泄漏后被横向读取。
    """
    normalized = (client_id or "").strip()
    if not normalized:
        raise RecordMissingCredential(
            "缺少身份凭据 client_id，拒绝读取分析报告；请在请求头 X-Client-Id 或请求体 client_id 中携带。"
        )
    if normalized != record_client_id:
        raise RecordForbidden(
            f"分析报告 {record_analysis_id} 不属于当前客户端，拒绝访问。"
        )


def deep_copy(payload: dict) -> dict:
    return copy.deepcopy(payload)
