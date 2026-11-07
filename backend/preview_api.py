"""Loopback-only integration preview using the upstream API and local model substitutes."""

import importlib
import json
import os
import sys
from pathlib import Path


class PreviewAnalyzer:
    def analyze(self, messages, *_args, **_kwargs):
        from analysis.analyzer import QualitativeAnalysis

        evidence_ids = [message.id for message in messages[-2:]]
        return QualitativeAnalysis.model_validate({
            "self_profile": {},
            "other_profile": {},
            "signals": [{
                "category": "neutral",
                "name": "预览证据示例",
                "description": "这里只用于展示报告和原文证据如何衔接。",
                "evidence_ids": evidence_ids,
            }],
            "relationship_assessment": {
                "summary": "本地模拟输出，用于验证报告与军师对话的流程。",
            },
            "limitations": ["预览使用固定模型替身。"],
        })


class PreviewAdvisor:
    def invoke(self, state, config=None):
        from langchain_core.messages import AIMessage

        question = state["messages"][-1].content
        reply = (
            "可以先确认对方是否方便，并给对方留出拒绝或改期的空间。"
            if "方便" in question
            else "可以先问对方哪一天有空，再提一个具体、轻松的安排。"
        )
        answer = AIMessage(content=json.dumps({"reply": f"【本地预览】{reply}"}, ensure_ascii=False))
        return {"messages": [*state["messages"], answer]}


def create_preview():
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "src"))
    if (root / ".preview-deps").is_dir():
        sys.path.insert(0, str(root / ".preview-deps"))

    import env_loader

    env_loader.load_project_env = lambda: None
    os.environ.update(
        STORE_BACKEND="memory",
        CORS_ALLOW_ORIGIN_REGEX=r"(?!)",
        LANGCHAIN_TRACING_V2="false",
        LANGSMITH_TRACING="false",
    )
    from agents.service import AgentService, get_agent_service
    from analysis.service import AnalysisService
    from store.memory_store import MemoryStore

    app_module = importlib.import_module("api.app")
    service_module = importlib.import_module("agents.service")
    service_module.perform_web_search = lambda *_args, **_kwargs: ([], "本地预览未启用联网搜索。")
    app_module.safe_provider_info = lambda: {
        "configured": True,
        "provider": "local-preview",
        "model": "simulated-fixture",
    }
    app_module._feature_info = lambda: {
        "thinking_levels": ["auto"],
        "thinking_supported": False,
        "provider": "local-preview",
        "web_search": {"supported": False, "default_enabled": False},
    }
    service = AgentService(
        analysis_service=AnalysisService(analyzer=PreviewAnalyzer()),
        store=MemoryStore(),
        agent_builder=lambda _ctx: PreviewAdvisor(),
    )
    app_module.app.dependency_overrides[get_agent_service] = lambda: service
    return app_module.app


if __name__ == "__main__":
    application = create_preview()
    import uvicorn

    uvicorn.run(application, host="127.0.0.1", port=8010)
