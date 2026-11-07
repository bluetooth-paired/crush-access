"""统一 Agent 服务：两个 API 路由调用同一个 Agent 实例的不同能力。

- analyze()       → 分析能力（复用 analyze_conversation 工具背后的同一条流水线）
- advisor_chat()  → 军师能力（同一 Agent + 绑定本次分析的上下文 + 多轮记忆）

服务本身不持有用户数据：报告与会话都在 store 中，按 analysis_id / session_id 索引，
并按 client_id 做归属校验。
"""
from __future__ import annotations

import inspect
import logging
from typing import Any, Optional

from langchain_core.messages import HumanMessage

from agents.advisor import build_advisor_context, parse_advisor_output
from agents.agent import build_agent
from agents.context import reset_mode, set_advisor_mode
from agents.web_search import build_search_query, perform_web_search
from analysis.analyzer import _content_to_text
from analysis.service import AnalysisService, ConversationValidationError
from llm.provider import thinking_plan
from settings import get_settings
from store.base import AnalysisStore, new_id
from store.factory import get_store

logger = logging.getLogger(__name__)


class AdvisorError(RuntimeError):
    """军师对话过程中的可预期错误。"""

    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class AgentService:
    """唯一 Agent 的统一服务入口。"""

    def __init__(
        self,
        analysis_service: Optional[AnalysisService] = None,
        store: Optional[AnalysisStore] = None,
        agent_builder=build_agent,
    ) -> None:
        self.analysis_service = analysis_service or AnalysisService()
        self._store = store
        self._agent_builder = agent_builder

    @property
    def store(self) -> AnalysisStore:
        return self._store or get_store()

    def _build_agent(self, ctx, thinking_level: str):
        """兼容注入的简化 agent_builder（只接受 ctx）与真实 build_agent。"""
        try:
            params = inspect.signature(self._agent_builder).parameters
            accepts_level = "thinking_level" in params or any(
                p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
            )
        except (TypeError, ValueError):
            accepts_level = False
        if accepts_level:
            return self._agent_builder(ctx, thinking_level=thinking_level)
        return self._agent_builder(ctx)

    # ------------------------------------------------------------------
    # 能力一：互动信号分析
    # ------------------------------------------------------------------
    def analyze(
        self,
        conversation: dict,
        user_profile: Optional[dict] = None,
        include_advice: bool = True,
        ctx=None,
        client_id: Optional[str] = None,
        thinking_level: Optional[str] = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        client_id = client_id or new_id()
        plan = thinking_plan(thinking_level)

        report = self.analysis_service.analyze(
            conversation,
            ctx=ctx,
            include_advice=include_advice,
            user_profile=user_profile,
            thinking_level=thinking_level,
        )
        report_dict = report.model_dump(by_alias=True)

        record = self.store.save_analysis(
            report=report_dict,
            conversation=conversation,
            client_id=client_id,
            ttl_seconds=settings.analysis_ttl_seconds,
            analysis_id=report.analysis_id,
        )

        return {
            "analysis_id": record.analysis_id,
            "client_id": record.client_id,
            "created_at": record.created_at.isoformat(),
            "expires_at": record.expires_at.isoformat(),
            "report": report_dict,
            "ai_config": {"thinking": plan.as_dict()},
        }

    # ------------------------------------------------------------------
    # 能力二：情感军师多轮对话
    # ------------------------------------------------------------------
    def advisor_chat(
        self,
        analysis_id: str,
        message: str,
        session_id: Optional[str] = None,
        client_id: Optional[str] = None,
        ctx=None,
        thinking_level: Optional[str] = None,
        web_search: bool = False,
    ) -> dict[str, Any]:
        settings = get_settings()
        record = self.store.get_analysis(analysis_id, client_id)
        session = self.store.get_session(
            session_id=session_id,
            analysis_id=analysis_id,
            client_id=record.client_id,
            ttl_seconds=settings.session_ttl_seconds,
        )

        turn = len(session.messages) // 2 + 1
        if turn > settings.max_advisor_turns:
            raise AdvisorError(
                "SESSION_TURN_LIMIT",
                f"会话已达 {settings.max_advisor_turns} 轮上限，请新建会话。",
                status_code=429,
            )

        # 思考强度：只在端点真实支持时按档位构建模型，否则沿用服务端默认
        plan = thinking_plan(thinking_level)
        agent_level = plan.applied if plan.supported and plan.applied != "server-default" else "auto"

        # 联网搜索：默认关闭；开启时只用「用户当前提问」清洗后的词，绝不上传聊天原文
        search_meta: dict[str, Any] = {
            "requested": bool(web_search),
            "performed": False,
            "results_count": 0,
            "query_used": None,
            "note": "未开启联网搜索（默认关闭）。",
        }
        web_results: list[dict[str, Any]] = []
        if web_search:
            query = build_search_query(message)
            web_results, search_error = perform_web_search(query, ctx=ctx)
            search_meta.update(
                {
                    "performed": search_error is None,
                    "results_count": len(web_results),
                    "query_used": query or None,
                    "note": search_error
                    or "已使用清洗后的用户提问执行搜索，未上传任何聊天原文。",
                }
            )

        context_text, retrieved = build_advisor_context(
            record.report,
            record.conversation,
            message,
            settings.evidence_limit,
            web_results=web_results or None,
        )

        tokens = set_advisor_mode(context_text, record.report)
        try:
            agent = self._build_agent(ctx, agent_level)
            result = agent.invoke(
                {"messages": [HumanMessage(content=message)]},
                config={"configurable": {"thread_id": session.session_id}},
            )
        except Exception as e:  # noqa: BLE001 - 统一转成结构化错误
            logger.error("advisor_agent_error analysis_id=%s error=%s", analysis_id, type(e).__name__)
            raise AdvisorError(
                "MODEL_ERROR", f"情感军师暂时不可用：{type(e).__name__}", status_code=502
            ) from e
        finally:
            reset_mode(tokens)

        messages = (result or {}).get("messages") or []
        raw_text = _content_to_text(messages[-1].content) if messages else ""
        parsed = parse_advisor_output(raw_text, settings.max_advisor_reply_chars)

        # 证据 ID 只保留真实存在于本次会话原文中的 id
        valid_ids = {
            str(m.get("id"))
            for m in (record.conversation.get("messages") or [])
            if isinstance(m, dict) and m.get("id")
        }
        evidence_ids = [mid for mid in parsed["evidence_ids"] if mid in valid_ids]
        if not evidence_ids and retrieved:
            evidence_ids = [item["id"] for item in retrieved[:3]]

        evidence_items = [
            item for item in retrieved if item["id"] in set(evidence_ids)
        ]

        self.store.append_session_messages(
            session.session_id,
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": parsed["reply"]},
            ],
            settings.session_ttl_seconds,
            client_id=record.client_id,
        )

        logger.info(
            "advisor_chat analysis_id=%s session_id=%s turn=%d evidence=%d structured=%s",
            analysis_id, session.session_id, turn, len(evidence_ids), parsed["structured"],
        )

        return {
            "analysis_id": analysis_id,
            "session_id": session.session_id,
            "turn": turn,
            "reply": parsed["reply"],
            "evidence_ids": evidence_ids,
            "evidence": evidence_items,
            "suggestions": parsed["suggestions"],
            "boundary_notes": parsed["boundary_notes"],
            "ai_config": {
                "thinking": plan.as_dict(),
                "web_search": search_meta,
                "output_format": {
                    "structured": parsed["structured"],
                    "truncated": parsed["truncated"],
                    "warnings": parsed["warnings"],
                    "max_reply_chars": settings.max_advisor_reply_chars,
                },
            },
        }


_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """FastAPI 依赖：进程内唯一 Agent 服务。"""
    global _service
    if _service is None:
        _service = AgentService()
    return _service


def set_agent_service(service: Optional[AgentService]) -> None:
    """测试用：替换全局服务实例。"""
    global _service
    _service = service


__all__ = [
    "AgentService",
    "AdvisorError",
    "ConversationValidationError",
    "get_agent_service",
    "set_agent_service",
]
