"""数据兼容性测试：无时区时间戳、sender_name、metadata 透传。

约束验证：
1. 无时区时间戳按 ASSUME_NAIVE_TZ_OFFSET_HOURS（默认 +8）解析，不被当成 UTC；
2. sender_name 只做展示透传，不参与 sender 归属判断；
3. metadata 与消息里的未知字段原样保留，不被删除或改写。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from agents.service import AgentService, get_agent_service
from analysis.preprocessor import to_epoch
from analysis.service import AnalysisService
from api.app import create_app
from store.memory_store import MemoryStore

from tests.test_api import FakeAnalyzer


class SilentAgent:
    def invoke(self, state, config=None):
        payload = {"reply": "先约时间地点，再观察主动性。"}
        return {
            "messages": list(state["messages"])
            + [AIMessage(content=json.dumps(payload, ensure_ascii=False))]
        }


NAIVE_CONVERSATION = {
    "schema_version": "1.0",
    "source": "wechat-cli",
    "chat_type": "private",
    "messages": [
        {
            "id": "n001",
            "timestamp": "2026-11-07T23:30:00",
            "sender": "self",
            "sender_name": "小 A",
            "type": "text",
            "content": "今天加班到很晚，你早点休息",
            "extra_field": "导入器自定义字段",
        },
        {
            "id": "n002",
            "timestamp": "2026-11-07T23:40:00",
            "sender": "other",
            "sender_name": "小 B",
            "type": "text",
            "content": "你也是，注意别熬太晚",
        },
        {
            "id": "n003",
            "timestamp": "2026-11-08T09:00:00",
            "sender": "self",
            "sender_name": "小 A",
            "type": "text",
            "content": "早呀，昨天谢谢关心",
        },
        {
            "id": "n004",
            "timestamp": "2026-11-08T09:05:00",
            "sender": "other",
            "sender_name": "小 B",
            "type": "text",
            "content": "早，今天有空一起吃饭吗？",
        },
    ],
    "metadata": {
        "total_messages": 4,
        "unknown_senders": 0,
        "anonymized": False,
        "id_origin": "export",
        "timestamp_precision": "second",
        "importer_version": "wechat-cli@0.9.3",
    },
}


@pytest.fixture()
def service() -> AgentService:
    return AgentService(
        analysis_service=AnalysisService(analyzer=FakeAnalyzer()),
        store=MemoryStore(),
        agent_builder=lambda ctx=None: SilentAgent(),
    )


@pytest.fixture()
def client(service: AgentService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_agent_service] = lambda: service
    return TestClient(app)


def test_naive_timestamp_uses_configured_offset():
    epoch = to_epoch("2026-11-07T23:30:00")
    expected = datetime(2026, 11, 7, 23, 30, tzinfo=timezone(timedelta(hours=8))).timestamp()
    utc_assumption = datetime(2026, 11, 7, 23, 30, tzinfo=timezone.utc).timestamp()

    assert epoch == expected
    assert epoch != utc_assumption
    # 带时区的时间戳保持自身语义
    assert to_epoch("2026-11-07T23:30:00+08:00") == expected


def test_invalid_timestamp_is_not_guessed():
    assert to_epoch("昨天下午") is None
    assert to_epoch("") is None


def test_analyze_accepts_naive_timestamps_and_sender_name(client: TestClient):
    resp = client.post("/api/v1/analyze", json={"conversation": NAIVE_CONVERSATION})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # 无时区时间戳仍能分日统计，跨零点消息落在各自本地日期
    dates = [point["date"] for point in data["daily_distribution"]]
    assert dates == ["2026-11-07", "2026-11-08"]
    assert data["metrics"]["message_counts"]["total"] == 4

    # 证据卡片保留原始昵称
    evidence = data["evidence"]
    assert evidence["n001"]["sender_name"] == "小 A"
    assert evidence["n001"]["content"] == "今天加班到很晚，你早点休息"
    assert evidence["n004"]["sender_name"] == "小 B"


def test_metadata_and_unknown_fields_are_preserved(service: AgentService, client: TestClient):
    resp = client.post("/api/v1/analyze", json={"conversation": NAIVE_CONVERSATION})
    analysis_id = resp.json()["analysis_id"]

    stored = service.store.get_analysis(analysis_id, resp.json()["client_id"])
    conversation = stored.conversation

    # metadata 原样保留（含导入器自定义字段）
    assert conversation["metadata"]["importer_version"] == "wechat-cli@0.9.3"
    assert conversation["metadata"]["timestamp_precision"] == "second"
    # 消息里的未知字段不被删除
    assert conversation["messages"][0]["extra_field"] == "导入器自定义字段"
    # 原始时间戳字符串不被改写
    assert conversation["messages"][0]["timestamp"] == "2026-11-07T23:30:00"


def test_unknown_sender_is_not_guessed(client: TestClient):
    conversation = {
        "schema_version": "1.0",
        "messages": [
            {"id": "u1", "timestamp": "2026-11-07T10:00:00", "sender": "someone", "type": "text", "content": "你好"},
            {"id": "u2", "timestamp": "2026-11-07T10:01:00", "sender": "other", "type": "text", "content": "你好呀"},
        ],
        "metadata": {},
    }
    resp = client.post("/api/v1/analyze", json={"conversation": conversation})
    assert resp.status_code == 200
    counts = resp.json()["metrics"]["message_counts"]
    assert counts["unknown"] == 1
    assert counts["other"] == 1


def test_null_content_message_is_accepted_and_kept(service: AgentService, client: TestClient):
    """部分导出器把图片/链接消息的 content 写成 null，不能因此 400，也不能改写原文。"""
    conversation = {
        "schema_version": "1.0",
        "messages": [
            {"id": "n1", "timestamp": "2026-11-07T10:00:00", "sender": "self", "type": "image", "content": None},
            {"id": "n2", "timestamp": "2026-11-07T10:01:00", "sender": "other", "type": "text", "content": "好看"},
        ],
        "metadata": {"timestamp_precision": "second"},
    }
    resp = client.post("/api/v1/analyze", json={"conversation": conversation})
    assert resp.status_code == 200, resp.text
    assert resp.json()["metrics"]["message_counts"]["total"] == 2

    stored = service.store.get_analysis(resp.json()["analysis_id"], resp.json()["client_id"])
    assert stored.conversation["messages"][0]["content"] is None
