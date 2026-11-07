"""API 端到端测试（不调用真实模型）。

用一个确定性的 FakeAnalyzer 和一个 FakeAgent 驱动真实的服务编排与路由，
覆盖：健康检查、分析响应字段、参数校验、归属隔离、过期、会话延续、CORS、OpenAPI。
真实模型链路由 scripts/smoke_test_api.py 单独验证。
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from agents.service import AgentService, get_agent_service
from analysis.analyzer import QualitativeAnalysis
from analysis.service import AnalysisService
from api.app import create_app
from store.base import utcnow
from store.memory_store import MemoryStore

FIXTURE = Path(__file__).parent / "fixtures" / "fictional_chat.json"

DIMENSIONS = [
    "话题主动性",
    "对话延续程度",
    "个人生活分享",
    "情绪表达程度",
    "关心与回应程度",
    "邀约与线下互动",
    "关系边界表达",
]


def _dim(level: str, evidence: list[str]) -> dict:
    return {"level": level, "detail": "虚构测试画像", "evidence_ids": evidence, "confidence": "medium"}


class FakeAnalyzer:
    """确定性定性分析替身：只替代模型调用，其余编排全部走真实代码。"""

    def analyze(self, messages, data_quality, statistics, ctx=None, user_profile=None):
        return QualitativeAnalysis.model_validate(
            {
                "self_profile": {d: _dim("中", ["m009"]) for d in DIMENSIONS},
                "other_profile": {d: _dim("高", ["m010"]) for d in DIMENSIONS},
                "interaction_patterns": [
                    {
                        "event_id": "evt_1",
                        "category": "邀请见面",
                        "participants": ["self"],
                        "message_ids": ["m009"],
                        "description": "用户邀请对方周末看展",
                        "certainty": "high",
                    }
                ],
                "signals": [
                    {
                        "category": "positive",
                        "name": "接受线下邀约",
                        "description": "对方同意周六下午一起看展并询问地点",
                        "evidence_ids": ["m010"],
                        "positive_interpretation": "对方愿意线下见面",
                        "alternative_interpretation": "也可能只是对展览本身感兴趣",
                        "evidence_strength": "strong",
                        "impact": "提升关系发展可能性",
                        "scope": "仅覆盖本次邀约",
                    }
                ],
                "relationship_assessment": {
                    "stage": "友好互动期",
                    "summary": "互动友好，存在线下见面的实际机会",
                    "supporting_facts": ["对方接受邀约"],
                    "contradicting_facts": ["对方未主动发起话题"],
                    "neutral_alternatives": ["普通朋友也会接受展览邀约"],
                    "confidence": "medium",
                },
                "advisor": {
                    "relationship_summary": "互动友好，可以自然推进线下见面",
                    "suggestions": ["先确认时间地点", "见面时多聊双方兴趣"],
                },
                "limitations": ["样本仅 12 条消息"],
                "message_flags": [
                    {"id": "m004", "is_question": True},
                    {"id": "m010", "is_question": True, "shared_activity": True},
                    {"id": "m009", "shared_activity": True},
                    {"id": "m007", "positive_tone": True},
                    {"id": "m008", "positive_tone": True},
                    {"id": "m012", "positive_tone": True},
                ],
            }
        )


def load_conversation() -> dict:
    with FIXTURE.open("r", encoding="utf-8") as f:
        return json.load(f)


class FakeAgent:
    """确定性 Agent 替身：返回符合军师 JSON 契约的内容（含一个非法证据 ID 用于校验）。"""

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, state, config=None):
        self.calls += 1
        payload = {
            "reply": "从报告看，对方接受了线下邀约，这是比较明确的积极信号。建议先把时间地点定下来。",
            "evidence_ids": ["m010", "m999"],
            "suggestions": ["先确认周六下午的具体时间与地点"],
            "boundary_notes": ["不要连续追问，给对方留出回应空间"],
        }
        return {"messages": list(state["messages"]) + [AIMessage(content=json.dumps(payload, ensure_ascii=False))]}


@pytest.fixture()
def service() -> AgentService:
    return AgentService(
        analysis_service=AnalysisService(analyzer=FakeAnalyzer()),
        store=MemoryStore(),
        agent_builder=lambda ctx=None: FakeAgent(),
    )


@pytest.fixture()
def client(service: AgentService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_agent_service] = lambda: service
    return TestClient(app)


def _analyze(client: TestClient, **overrides):
    body = {"conversation": load_conversation(), "options": {"include_evidence": True}}
    body.update(overrides)
    return client.post("/api/v1/analyze", json=body)


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["store_backend"] == "memory"
    assert "configured" in data["model"]
    # 不得暴露任何密钥字段
    assert "api_key" not in json.dumps(data).lower()


def test_analyze_returns_chart_ready_fields(client: TestClient):
    resp = _analyze(client)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["analysis_id"]
    assert data["client_id"]
    assert data["expires_at"]

    metrics = data["metrics"]
    assert metrics["message_counts"]["total"] == 12
    assert metrics["participation_balance"] == 1.0
    assert metrics["interaction_index"] > 0
    assert metrics["disclaimer"]
    assert len(metrics["formulas"]) >= 6
    assert metrics["interaction_index_components"]

    assert len(data["daily_distribution"]) == 3
    assert data["portraits"]["self_portrait"]
    assert data["portraits"]["other_portrait"]
    assert data["portraits"]["self_portrait"][0]["key"]
    assert data["portraits"]["self_portrait"][0]["score"] is not None

    assert data["signals"]
    assert data["signals"][0]["evidence_ids"]
    # 证据原文按引用回传，供前端渲染证据卡片
    assert data["evidence"]
    for evidence_id, item in data["evidence"].items():
        assert item["id"] == evidence_id
        assert item["content"]


def test_analyze_rejects_unsupported_schema(client: TestClient):
    conversation = load_conversation()
    conversation["schema_version"] = "2.0"
    resp = _analyze(client, conversation=conversation)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "UNSUPPORTED_SCHEMA_VERSION"


def test_analyze_rejects_empty_messages(client: TestClient):
    resp = _analyze(client, conversation={"schema_version": "1.0", "messages": []})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "EMPTY_CONVERSATION"


def test_analyze_rejects_too_many_messages(client: TestClient):
    conversation = load_conversation()
    conversation["messages"] = conversation["messages"] * 400  # 4800 > 3000
    resp = _analyze(client, conversation=conversation)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "CONVERSATION_TOO_LARGE"


def test_advisor_chat_returns_reply_and_validated_evidence(client: TestClient):
    created = _analyze(client).json()
    resp = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": created["analysis_id"],
            "message": "她答应看展是不是说明有戏？",
            "client_id": created["client_id"],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["session_id"]
    assert data["turn"] == 1
    assert data["reply"]
    # 非法证据 ID（m999）必须被剔除
    assert "m999" not in data["evidence_ids"]
    assert "m010" in data["evidence_ids"]
    assert data["suggestions"]
    assert data["boundary_notes"]

    # 第二轮：带同一个 session_id，turn 递增
    second = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": created["analysis_id"],
            "session_id": data["session_id"],
            "message": "那我下一步该说什么？",
            "client_id": created["client_id"],
        },
    ).json()
    assert second["session_id"] == data["session_id"]
    assert second["turn"] == 2


def test_advisor_rejects_cross_client(client: TestClient):
    created = _analyze(client).json()
    resp = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": created["analysis_id"],
            "message": "你好",
            "client_id": "another-client-0001",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ANALYSIS_FORBIDDEN"


def test_advisor_unknown_analysis(client: TestClient):
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"analysis_id": "not-exist", "message": "你好"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


def test_advisor_expired_analysis(client: TestClient, service: AgentService):
    created = _analyze(client).json()
    record = service.store._analyses[created["analysis_id"]]  # type: ignore[attr-defined]
    record.expires_at = utcnow() - timedelta(seconds=1)

    resp = client.post(
        "/api/v1/advisor/chat",
        json={"analysis_id": created["analysis_id"], "message": "你好"},
    )
    assert resp.status_code == 410
    assert resp.json()["error"]["code"] == "ANALYSIS_EXPIRED"


def test_advisor_rejects_empty_message(client: TestClient):
    created = _analyze(client).json()
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"analysis_id": created["analysis_id"], "message": "   "},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_REQUEST"


def test_cors_allows_github_pages(client: TestClient):
    resp = client.options(
        "/api/v1/analyze",
        headers={
            "Origin": "https://auria.github.io",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code in (200, 204)
    assert resp.headers.get("access-control-allow-origin") in ("https://auria.github.io", "*")


def test_openapi_documents_both_endpoints(client: TestClient):
    spec = client.get("/openapi.json").json()
    assert "/api/v1/analyze" in spec["paths"]
    assert "/api/v1/advisor/chat" in spec["paths"]
    assert "/health" in spec["paths"]
