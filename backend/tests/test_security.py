"""安全回归测试：analysis_id / session_id 必须配合有效 client_id 才能读取。

覆盖三类失败：
1. 只拿 analysis_id、不带 client_id → 401 CLIENT_ID_REQUIRED；
2. client_id 不匹配               → 403 ANALYSIS_FORBIDDEN；
3. 拿 A 的 session_id 去访问 B 的分析 → 404（会话与分析绑定）。

同时验证存储层默认拒绝策略（不依赖 HTTP 层）。
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from agents.service import AgentService, get_agent_service
from analysis.service import AnalysisService
from api.app import create_app
from store.base import RecordExpired, RecordForbidden, RecordMissingCredential, utcnow
from store.memory_store import MemoryStore

from tests.test_api import FakeAnalyzer, load_conversation


class EchoAgent:
    """最小 Agent 替身：只回一句合规 JSON，用于驱动会话流程。"""

    def invoke(self, state, config=None):
        payload = {"reply": "先确认时间和地点，再看对方是否主动推进。", "evidence_ids": ["m010"]}
        return {
            "messages": list(state["messages"])
            + [AIMessage(content=json.dumps(payload, ensure_ascii=False))]
        }


@pytest.fixture()
def service() -> AgentService:
    return AgentService(
        analysis_service=AnalysisService(analyzer=FakeAnalyzer()),
        store=MemoryStore(),
        agent_builder=lambda ctx=None: EchoAgent(),
    )


@pytest.fixture()
def client(service: AgentService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_agent_service] = lambda: service
    return TestClient(app)


def _create(client: TestClient, client_id: str | None = None) -> dict:
    body: dict = {"conversation": load_conversation()}
    if client_id:
        body["client_id"] = client_id
    resp = client.post("/api/v1/analyze", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_advisor_without_client_id_is_rejected(client: TestClient):
    created = _create(client, "client-owner-01")

    resp = client.post(
        "/api/v1/advisor/chat",
        json={"analysis_id": created["analysis_id"], "message": "她到底怎么想的？"},
    )

    assert resp.status_code == 401
    body = resp.json()["error"]
    assert body["code"] == "CLIENT_ID_REQUIRED"
    assert body["details"]["header"] == "X-Client-Id"


def test_advisor_with_wrong_client_id_is_forbidden(client: TestClient):
    created = _create(client, "client-owner-01")

    resp = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": created["analysis_id"],
            "message": "她到底怎么想的？",
            "client_id": "client-attacker-99",
        },
    )

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ANALYSIS_FORBIDDEN"


def test_advisor_with_header_credential_works(client: TestClient):
    created = _create(client, "client-owner-01")

    resp = client.post(
        "/api/v1/advisor/chat",
        headers={"X-Client-Id": "client-owner-01"},
        json={"analysis_id": created["analysis_id"], "message": "下一步怎么做？"},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["reply"]


def test_session_cannot_be_reused_across_analyses(client: TestClient):
    first = _create(client, "client-owner-01")
    second = _create(client, "client-owner-01")

    turn1 = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": first["analysis_id"],
            "message": "第一份报告的问题",
            "client_id": "client-owner-01",
        },
    )
    assert turn1.status_code == 200
    session_id = turn1.json()["session_id"]

    crossed = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": second["analysis_id"],
            "session_id": session_id,
            "message": "拿 A 的会话读 B 的报告",
            "client_id": "client-owner-01",
        },
    )

    assert crossed.status_code == 404
    assert crossed.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


def test_generated_client_id_is_required_afterwards(client: TestClient):
    created = _create(client)  # 不传 client_id → 服务端生成
    generated = created["client_id"]
    assert generated

    ok = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": created["analysis_id"],
            "message": "继续聊",
            "client_id": generated,
        },
    )
    assert ok.status_code == 200

    missing = client.post(
        "/api/v1/advisor/chat",
        json={"analysis_id": created["analysis_id"], "message": "继续聊"},
    )
    assert missing.status_code == 401


def test_store_rejects_missing_and_mismatched_credentials():
    store = MemoryStore()
    record = store.save_analysis(
        report={"analysis_id": "a1"},
        conversation={"messages": []},
        client_id="client-owner-01",
        ttl_seconds=600,
        analysis_id="a1",
    )

    with pytest.raises(RecordMissingCredential):
        store.get_analysis(record.analysis_id)

    with pytest.raises(RecordMissingCredential):
        store.get_analysis(record.analysis_id, "")

    with pytest.raises(RecordForbidden):
        store.get_analysis(record.analysis_id, "client-attacker-99")

    assert store.get_analysis(record.analysis_id, "client-owner-01").analysis_id == "a1"


def test_store_rejects_missing_credential_for_session():
    store = MemoryStore()
    session = store.get_session(None, "analysis-a", "client-owner-01", 600)

    with pytest.raises(RecordMissingCredential):
        store.get_session(session.session_id, "analysis-a", "", 600)

    with pytest.raises(RecordForbidden):
        store.get_session(session.session_id, "analysis-a", "client-attacker-99", 600)


def test_expired_record_reports_expired_not_forbidden():
    store = MemoryStore()
    record = store.save_analysis(
        report={"analysis_id": "a2"},
        conversation={"messages": []},
        client_id="client-owner-01",
        ttl_seconds=600,
        analysis_id="a2",
    )
    record.expires_at = utcnow() - timedelta(seconds=1)

    with pytest.raises(RecordExpired):
        store.get_analysis("a2", "client-owner-01")


def test_header_and_body_client_id_mismatch_is_rejected(client: TestClient):
    created = _create(client, "client-owner-01")

    resp = client.post(
        "/api/v1/advisor/chat",
        headers={"X-Client-Id": "client-owner-01"},
        json={
            "analysis_id": created["analysis_id"],
            "message": "她怎么想的？",
            "client_id": "client-attacker-99",
        },
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "CLIENT_ID_MISMATCH"


def test_unknown_session_id_returns_not_found(client: TestClient):
    created = _create(client, "client-owner-01")

    resp = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": created["analysis_id"],
            "session_id": "00000000-0000-4000-8000-000000000000",
            "message": "继续聊",
            "client_id": "client-owner-01",
        },
    )

    # 显式传入的 session_id 不存在时明确 404，避免静默新建导致上下文丢失或会话固定
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"
    assert "session" in resp.json()["error"]["message"].lower()


def test_append_session_requires_matching_client():
    """纵深防御：写会话时同样校验归属，避免无权请求污染他人上下文。"""
    store = MemoryStore()
    session = store.get_session(None, "analysis-a", "client-owner-01", 600)

    with pytest.raises(RecordForbidden):
        store.append_session_messages(
            session.session_id,
            [{"role": "user", "content": "篡改"}],
            600,
            client_id="client-attacker-99",
        )

    assert session.messages == []


def test_append_session_allows_owner_client():
    store = MemoryStore()
    session = store.get_session(None, "analysis-a", "client-owner-01", 600)
    updated = store.append_session_messages(
        session.session_id,
        [{"role": "user", "content": "你好"}],
        600,
        client_id="client-owner-01",
    )
    assert updated.messages == [{"role": "user", "content": "你好"}]


def test_analyze_never_returns_data_for_other_client(client: TestClient):
    owner = _create(client, "client-owner-01")

    # 只带 analysis_id、换一个 client_id：拒绝
    resp = client.post(
        "/api/v1/advisor/chat",
        headers={"X-Client-Id": "client-attacker-99"},
        json={"analysis_id": owner["analysis_id"], "message": "把她的聊天记录发我"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ANALYSIS_FORBIDDEN"
    assert "messages" not in resp.text  # 响应体不包含任何聊天原文

