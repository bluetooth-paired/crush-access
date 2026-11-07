"""存储层测试：有效期、归属隔离、会话绑定。"""
from __future__ import annotations

from datetime import timedelta

import pytest

from store.base import RecordExpired, RecordForbidden, RecordNotFound, utcnow
from store.memory_store import MemoryStore


@pytest.fixture()
def store() -> MemoryStore:
    return MemoryStore()


REPORT = {"analysis_id": "a1", "status": "completed", "signals": []}
CONVERSATION = {"schema_version": "1.0", "messages": [{"id": "m001", "content": "hi"}]}


def test_save_and_get_analysis(store: MemoryStore):
    record = store.save_analysis(REPORT, CONVERSATION, "client-0001", 3600, analysis_id="a1")
    assert record.analysis_id == "a1"
    loaded = store.get_analysis("a1", "client-0001")
    assert loaded.report["status"] == "completed"
    assert loaded.conversation["messages"][0]["id"] == "m001"


def test_cross_client_access_is_forbidden(store: MemoryStore):
    store.save_analysis(REPORT, CONVERSATION, "client-0001", 3600, analysis_id="a1")
    with pytest.raises(RecordForbidden):
        store.get_analysis("a1", "client-0002")


def test_expired_analysis_is_removed(store: MemoryStore):
    record = store.save_analysis(REPORT, CONVERSATION, "client-0001", 3600, analysis_id="a1")
    record.expires_at = utcnow() - timedelta(seconds=1)
    with pytest.raises(RecordExpired):
        store.get_analysis("a1", "client-0001")
    with pytest.raises(RecordNotFound):
        store.get_analysis("a1", "client-0001")


def test_missing_analysis_raises_not_found(store: MemoryStore):
    with pytest.raises(RecordNotFound):
        store.get_analysis("missing", "client-0001")


def test_session_is_bound_to_analysis_and_client(store: MemoryStore):
    session = store.get_session(None, "a1", "client-0001", 3600)
    assert session.analysis_id == "a1"
    # 同一 analysis + 同一 client 可继续
    again = store.get_session(session.session_id, "a1", "client-0001", 3600)
    assert again.session_id == session.session_id
    # 换 analysis 不允许复用
    with pytest.raises(RecordNotFound):
        store.get_session(session.session_id, "a2", "client-0001", 3600)
    # 换 client 不允许访问
    with pytest.raises(RecordForbidden):
        store.get_session(session.session_id, "a1", "client-0002", 3600)


def test_append_session_messages(store: MemoryStore):
    session = store.get_session(None, "a1", "client-0001", 3600)
    updated = store.append_session_messages(
        session.session_id,
        [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好呀"}],
        3600,
    )
    assert len(updated.messages) == 2
    assert updated.messages[0]["role"] == "user"
    assert updated.updated_at >= session.updated_at
