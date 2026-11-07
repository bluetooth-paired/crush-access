"""AI 配置能力测试：思考强度映射、联网搜索隐私约束、军师输出精简、接口向后兼容。

说明：模型调用由 FakeAnalyzer / FakeAgent 替代（仅测试用），
思考强度与搜索隐私逻辑本身走真实实现，真实模型链路见 scripts/smoke_test_api.py。
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from agents.advisor import build_advisor_context
from agents.prompts import ADVISOR_SYSTEM_PROMPT
from agents.service import AgentService, get_agent_service
from agents.web_search import build_search_query, perform_web_search
from analysis.service import AnalysisService
from api.app import create_app
from llm.thinking import plan_thinking
from store.memory_store import MemoryStore
from test_api import FakeAgent, FakeAnalyzer, load_conversation


# ----------------------------------------------------------------------
# 思考强度映射
# ----------------------------------------------------------------------
def test_thinking_auto_keeps_server_default():
    plan = plan_thinking("auto", supports_thinking_body=True)
    assert plan.applied == "server-default"
    assert plan.supported is True
    assert plan.sent_parameters == {}


def test_thinking_levels_map_to_real_parameters():
    assert plan_thinking("low", supports_thinking_body=True).sent_parameters == {
        "thinking": {"type": "disabled"}
    }
    medium = plan_thinking("medium", supports_thinking_body=True)
    assert medium.sent_parameters == {"thinking": {"type": "enabled"}}
    assert medium.applied == "medium"

    high = plan_thinking("high", supports_thinking_body=True)
    assert high.sent_parameters == {
        "thinking": {"type": "enabled", "reasoning_effort": "high"}
    }
    assert high.applied == "high"


def test_thinking_unsupported_endpoint_is_reported_honestly():
    """端点不支持时必须明确标记未生效，不能假装成功。"""
    for level in ("low", "medium", "high"):
        plan = plan_thinking(level, supports_thinking_body=False)
        assert plan.supported is False
        assert plan.applied == "server-default"
        assert plan.sent_parameters == {}
        assert "未生效" in plan.note


def test_thinking_invalid_level_rejected():
    with pytest.raises(ValueError):
        plan_thinking("ultra", supports_thinking_body=True)


# ----------------------------------------------------------------------
# 联网搜索：默认关闭 + 隐私清洗
# ----------------------------------------------------------------------
def test_search_query_strips_message_ids_and_quoted_chat():
    question = 'TA 说「周六下午可以，具体在哪」是不是有戏？引用 m010 那条'
    query = build_search_query(question)
    assert "m010" not in query
    assert "周六下午可以，具体在哪" not in query
    assert "不是" not in query or "是不是" in query  # 保留用户自己的疑问表达
    assert len(query) <= 60


def test_search_query_truncated():
    query = build_search_query("这件事" * 100)
    assert len(query) <= 60


def test_empty_query_skips_search_without_fake_result():
    results, error = perform_web_search("")
    assert results == []
    assert error


def test_web_search_default_off_returns_meta(client: TestClient):
    created = client.post(
        "/api/v1/analyze", json={"conversation": load_conversation()}
    ).json()
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"analysis_id": created["analysis_id"],
                "client_id": created["client_id"], "message": "她是不是有戏？"},
    )
    assert resp.status_code == 200
    search_meta = resp.json()["ai_config"]["web_search"]
    assert search_meta["requested"] is False
    assert search_meta["performed"] is False
    assert search_meta["results_count"] == 0


# ----------------------------------------------------------------------
# 军师上下文瘦身 + 提示词约束
# ----------------------------------------------------------------------
def test_advisor_prompt_forbids_report_repetition():
    prompt = ADVISOR_SYSTEM_PROMPT
    assert "禁止复述" in prompt
    assert "不得复述或罗列双方画像" in prompt
    assert "60~200 字" in prompt
    # 不允许把画像/指标当作 reply 主体
    assert "reply 里不要出现「画像」「指标」「报告」「评估」这些词" in prompt


def test_advisor_context_is_slimmed():
    report = {
        "analysis_id": "a1",
        "status": "completed",
        "metrics": {"message_counts": {"self": 1, "other": 1}, "interaction_index": 50.0},
        "self_profile": {"话题主动性": {"level": "高", "detail": "很长的画像细节" * 20, "evidence_ids": ["m001"]}},
        "other_profile": {"关心与回应程度": {"level": "中", "detail": "另一段很长的细节", "evidence_ids": ["m002"]}},
        "signals": [
            {
                "category": "positive",
                "name": "接受邀约",
                "description": "很长的描述" * 20,
                "evidence_ids": ["m002"],
                "positive_interpretation": "x" * 100,
                "alternative_interpretation": "y" * 100,
            }
        ],
        "relationship_assessment": {"stage": "友好互动期", "summary": "很长的总结" * 30, "confidence": "medium"},
        "advisor": {"suggestions": ["报告里的建议"]},
        "limitations": [],
        "data_quality": {"coverage": "12 条"},
    }
    conversation = {"messages": [{"id": "m002", "sender": "other", "content": "周六下午可以"}]}
    text, evidence = build_advisor_context(report, conversation, "她有戏吗", 8)

    assert "usage_rule" in text
    # 画像只保留等级与证据，不再注入 detail 长文本
    assert "很长的画像细节" not in text
    assert "另一段很长的细节" not in text
    assert "很长的描述" not in text
    # 报告中已给的建议不再喂回，避免模型复述
    assert "报告里的建议" not in text
    assert evidence and evidence[0]["id"] == "m002"


# ----------------------------------------------------------------------
# 接口：新增可选参数 + 向后兼容
# ----------------------------------------------------------------------
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


def test_analyze_backward_compatible_request(client: TestClient):
    """不带任何新增字段的旧请求必须仍然可用。"""
    resp = client.post("/api/v1/analyze", json={"conversation": load_conversation()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ai_config"]["thinking"]["requested"] == "auto"


def test_analyze_accepts_thinking_level(client: TestClient):
    resp = client.post(
        "/api/v1/analyze",
        json={"conversation": load_conversation(), "options": {"thinking_level": "low"}},
    )
    assert resp.status_code == 200
    thinking = resp.json()["ai_config"]["thinking"]
    assert thinking["requested"] == "low"
    assert thinking["applied"] in ("low", "server-default")
    assert "supported" in thinking


def test_analyze_rejects_invalid_thinking_level(client: TestClient):
    resp = client.post(
        "/api/v1/analyze",
        json={"conversation": load_conversation(), "options": {"thinking_level": "ultra"}},
    )
    assert resp.status_code == 422


def test_advisor_backward_compatible_request(client: TestClient):
    created = client.post(
        "/api/v1/analyze", json={"conversation": load_conversation()}
    ).json()
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"analysis_id": created["analysis_id"],
                "client_id": created["client_id"], "message": "下一步怎么办？"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"]
    assert body["ai_config"]["thinking"]["requested"] == "auto"


def test_advisor_accepts_config_params(client: TestClient):
    created = client.post(
        "/api/v1/analyze", json={"conversation": load_conversation()}
    ).json()
    resp = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": created["analysis_id"],
                "client_id": created["client_id"],
            "message": "她问地点是什么意思？",
            "thinking_level": "high",
            "web_search": False,
        },
    )
    assert resp.status_code == 200
    thinking = resp.json()["ai_config"]["thinking"]
    assert thinking["requested"] == "high"
    assert "sent_parameters" in thinking


def test_advisor_rejects_invalid_config(client: TestClient):
    created = client.post(
        "/api/v1/analyze", json={"conversation": load_conversation()}
    ).json()
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"analysis_id": created["analysis_id"],
                "client_id": created["client_id"], "message": "hi", "thinking_level": "max"},
    )
    assert resp.status_code == 422


def test_health_exposes_capabilities_without_secrets(client: TestClient):
    data = client.get("/health").json()
    features = data["features"]
    assert features["thinking_levels"] == ["auto", "low", "medium", "high"]
    assert isinstance(features["thinking_supported"], bool)
    assert features["web_search"]["default_enabled"] is False
    assert "key" not in json.dumps(features).lower()
