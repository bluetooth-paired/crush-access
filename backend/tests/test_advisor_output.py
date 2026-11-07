"""军师输出格式校验测试：report 式输出必须被抑制，reply 保持简洁可用。"""
from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage

from agents.advisor import looks_like_report, parse_advisor_output
from agents.service import AgentService
from analysis.service import AnalysisService
from store.memory_store import MemoryStore

from tests.test_api import FakeAnalyzer, load_conversation


# ---------------------------------------------------------------------------
# 纯解析函数
# ---------------------------------------------------------------------------
def test_valid_json_contract_is_parsed():
    payload = {
        "reply": "她愿意赴约，说明至少不排斥，可以先把时间地点定下来。",
        "evidence_ids": ["m009", "m010"],
        "suggestions": ["确认时间地点"],
        "boundary_notes": ["不要连续追问"],
    }
    parsed = parse_advisor_output(json.dumps(payload, ensure_ascii=False), max_reply_chars=500)

    assert parsed["structured"] is True
    assert parsed["reply"] == payload["reply"]
    assert parsed["evidence_ids"] == ["m009", "m010"]
    assert parsed["suggestions"] == ["确认时间地点"]
    assert parsed["truncated"] is False


def test_fenced_json_is_accepted():
    text = "```json\n" + json.dumps({"reply": "可以自然推进。"}, ensure_ascii=False) + "\n```"
    parsed = parse_advisor_output(text, max_reply_chars=500)
    assert parsed["structured"] is True
    assert parsed["reply"] == "可以自然推进。"


def test_broken_json_still_recovers_reply_field():
    text = '{"reply": "先观察她是否主动找你，再决定推进节奏。", "evidence_ids": ['
    parsed = parse_advisor_output(text, max_reply_chars=500)
    assert "先观察她是否主动找你" in parsed["reply"]
    assert "json_contract_violated_recovered" in parsed["warnings"]


def test_report_like_output_is_suppressed():
    text = (
        "# 人物画像\n"
        "## 用户本人\n- 话题主动性: 高\n- 个人生活分享: 中\n\n"
        "## 关系评估\n互动指标 interaction_index = 79.7\n\n"
        "她愿意赴约，可以先定时间地点。"
    )
    assert looks_like_report(text) is True

    parsed = parse_advisor_output(text, max_reply_chars=500)

    assert "report_like_output_suppressed" in parsed["warnings"]
    assert "#" not in parsed["reply"]
    assert "互动指标" not in parsed["reply"]
    assert "先定时间地点" in parsed["reply"]
    assert parsed["truncated"] is False


def test_report_hidden_inside_json_reply_is_suppressed():
    """JSON 契约合法但 reply 塞满报告时，仍然要收敛成一句建议。"""
    payload = {
        "reply": (
            "# 人物画像\n- 话题主动性：高\n- 情绪表达：中\n\n"
            "# 互动指标\ninteraction_index=79.7\n\n"
            "# 关系评估\n当前处于友好互动期。\n\n"
            "对方愿意赴约，先把时间地点定下来就好。"
        ),
        "evidence_ids": ["m009"],
    }
    parsed = parse_advisor_output(json.dumps(payload, ensure_ascii=False), max_reply_chars=500)

    assert parsed["structured"] is True
    assert "report_like_reply_suppressed" in parsed["warnings"]
    assert "#" not in parsed["reply"]
    assert "interaction_index" not in parsed["reply"]
    assert "先" in parsed["reply"]


def test_over_long_reply_is_truncated_at_sentence_boundary():
    long_reply = "先确认时间地点。" * 200
    parsed = parse_advisor_output(long_reply, max_reply_chars=120)

    assert parsed["truncated"] is True
    assert len(parsed["reply"]) <= 130  # 句子边界截断的微小余量
    assert "reply_truncated" in parsed["warnings"]


def test_empty_output_gets_safe_fallback():
    parsed = parse_advisor_output("   ", max_reply_chars=500)
    assert parsed["reply"]
    assert parsed["structured"] is False
    assert parsed["warnings"]


# ---------------------------------------------------------------------------
# 服务级：Agent 抛回整份报告时，reply 仍然简洁
# ---------------------------------------------------------------------------
class ReportLikeAgent:
    """模拟最坏情况：Agent 把完整画像与分析报告当成了回复。"""

    def invoke(self, state, config=None):
        report = (
            "# 人物画像\n"
            "## 用户本人\n- 话题主动性：高（证据 m009）\n- 情绪表达：中\n\n"
            "## 对方\n- 关心与回应：中\n\n"
            "# 互动指标\n"
            "participation_balance=1.0, interaction_index=79.7\n\n"
            "# 关系评估\n"
            "当前处于友好互动期，置信度 medium。\n\n"
            "对方愿意赴约，先把时间地点定下来就好。"
        ) * 6
        return {"messages": [AIMessage(content=report)]}


@pytest.fixture()
def report_service() -> AgentService:
    return AgentService(
        analysis_service=AnalysisService(analyzer=FakeAnalyzer()),
        store=MemoryStore(),
        agent_builder=lambda ctx=None, thinking_level=None: ReportLikeAgent(),
    )


def test_service_suppresses_report_like_reply(report_service: AgentService):
    created = report_service.analyze(load_conversation(), client_id="client-owner-01")

    result = report_service.advisor_chat(
        analysis_id=created["analysis_id"],
        message="她答应看展了，下一步怎么做？",
        client_id="client-owner-01",
    )

    reply = result["reply"]
    assert reply
    assert len(reply) <= 520
    assert "#" not in reply
    assert "interaction_index" not in reply
    assert "人物画像" not in reply
    assert result["ai_config"]["output_format"]["warnings"]
    assert result["ai_config"]["output_format"]["structured"] is False


def test_service_keeps_json_contract_reply(report_service: AgentService):
    class JsonAgent:
        def invoke(self, state, config=None):
            payload = {"reply": "可以先把展览时间地点定下来。"}
            return {"messages": [AIMessage(content=json.dumps(payload, ensure_ascii=False))]}

    report_service._build_agent = lambda ctx=None, thinking_level=None: JsonAgent()  # type: ignore[attr-defined]
    created = report_service.analyze(load_conversation(), client_id="client-owner-01")
    result = report_service.advisor_chat(
        analysis_id=created["analysis_id"],
        message="下一步？",
        client_id="client-owner-01",
    )

    assert result["reply"] == "可以先把展览时间地点定下来。"
    assert result["ai_config"]["output_format"]["structured"] is True
