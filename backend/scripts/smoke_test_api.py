"""真实模型端到端冒烟测试（会调用真实 LLM，产生费用）。

用法：
    PYTHONPATH=src python scripts/smoke_test_api.py

前置条件：环境变量中已配置模型凭据（LLM_API_KEY，或平台托管模型的
COZE_WORKLOAD_IDENTITY_API_KEY + COZE_INTEGRATION_MODEL_BASE_URL）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 允许直接 `python scripts/smoke_test_api.py`（无需手动设置 PYTHONPATH）
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from api.app import create_app  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "fictional_chat.json"


def main() -> int:
    conversation = json.loads(FIXTURE.read_text(encoding="utf-8"))
    client = TestClient(create_app())

    print("== GET /health ==")
    health = client.get("/health")
    print(health.status_code, json.dumps(health.json(), ensure_ascii=False))

    print("\n== POST /api/v1/analyze ==")
    resp = client.post(
        "/api/v1/analyze",
        json={"conversation": conversation, "options": {"include_evidence": True}},
    )
    print("status:", resp.status_code)
    if resp.status_code != 200:
        print(resp.text[:2000])
        return 1

    report = resp.json()
    print("analysis_id:", report["analysis_id"])
    print("status:", report["status"])
    print("metrics:", json.dumps(report["metrics"], ensure_ascii=False)[:900])
    print("daily_distribution:", json.dumps(report["daily_distribution"], ensure_ascii=False))
    print("signal_count:", len(report["signals"]), "evidence_count:", len(report["evidence"]))
    print("relationship_stage:", report["relationship_assessment"]["stage"])

    print("\n== POST /api/v1/advisor/chat (turn 1) ==")
    chat = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": report["analysis_id"],
            "message": "她答应看展，是不是说明有戏？我下一步该怎么做？",
            "client_id": report["client_id"],
        },
    )
    print("status:", chat.status_code)
    if chat.status_code != 200:
        print(chat.text[:2000])
        return 1
    data = chat.json()
    print("session_id:", data["session_id"], "turn:", data["turn"])
    print("evidence_ids:", data["evidence_ids"])
    print("suggestions:", data["suggestions"])
    print("boundary_notes:", data["boundary_notes"])
    print("reply:\n", data["reply"][:800])

    print("\n== POST /api/v1/advisor/chat (turn 2，验证多轮) ==")
    chat2 = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": report["analysis_id"],
            "session_id": data["session_id"],
            "message": "那我聊天时应该注意什么？",
            "client_id": report["client_id"],
        },
    )
    print("status:", chat2.status_code, "turn:", chat2.json().get("turn"))
    print("reply:\n", chat2.json().get("reply", "")[:400])

    print("\n== POST /api/v1/advisor/chat (thinking_level=high + web_search=true) ==")
    chat3 = client.post(
        "/api/v1/advisor/chat",
        json={
            "analysis_id": report["analysis_id"],
            "session_id": data["session_id"],
            "message": "周末想找摄影展，有什么推荐的展览类型吗？",
            "client_id": report["client_id"],
            "thinking_level": "high",
            "web_search": True,
        },
    )
    print("status:", chat3.status_code)
    body3 = chat3.json()
    print("ai_config:", json.dumps(body3.get("ai_config"), ensure_ascii=False))
    print("reply_len:", len(body3.get("reply", "")))
    print("reply:\n", body3.get("reply", "")[:400])

    print("\n真实模型链路冒烟测试完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
