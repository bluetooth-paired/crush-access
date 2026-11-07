"""API A：互动信号分析 POST /api/v1/analyze"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from agents.service import AgentService, get_agent_service
from api.deps import get_platform_ctx, resolve_client_id
from api.errors import APIError
from api.schemas import AnalyzeRequest, AnalyzeResponse
from api.transformers import build_portraits
from llm.provider import LLMConfigError
from settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["A · 互动信号分析"])


def _validate_conversation(conversation: dict) -> None:
    settings = get_settings()
    if not isinstance(conversation, dict):
        raise APIError(400, "INVALID_CONVERSATION", "conversation 必须是 JSON 对象。")

    messages = conversation.get("messages")
    if not isinstance(messages, list) or not messages:
        raise APIError(400, "EMPTY_CONVERSATION", "messages 不能为空。")

    if len(messages) > settings.max_messages_per_request:
        raise APIError(
            400,
            "CONVERSATION_TOO_LARGE",
            f"单次最多分析 {settings.max_messages_per_request} 条消息，当前 {len(messages)} 条。",
        )

    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise APIError(400, "INVALID_CONVERSATION", f"messages[{index}] 必须是对象。")
        content = str(message.get("content") or "")
        if len(content) > settings.max_message_chars:
            raise APIError(
                400,
                "MESSAGE_TOO_LONG",
                f"messages[{index}] 内容超过 {settings.max_message_chars} 字符上限。",
            )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="分析微信聊天记录，返回结构化互动信号报告",
    description=(
        "输入墨翊 chat.json（Schema 1.0）与可选人物档案，返回 metrics（可直接画圆环图/进度条）、"
        "daily_distribution（柱状图）、signals（证据卡片）、portraits（雷达图）等结构化字段。\n\n"
        "所有数字由 Python 计算，语义事件由 LLM 打标后汇总；interaction_index 只是启发式参考。"
    ),
)
def analyze(
    payload: AnalyzeRequest,
    request: Request,
    service: AgentService = Depends(get_agent_service),
) -> AnalyzeResponse:
    settings = get_settings()
    _validate_conversation(payload.conversation)
    client_id = resolve_client_id(request, payload.client_id)

    try:
        result = service.analyze(
            conversation=payload.conversation,
            user_profile=payload.profile,
            include_advice=payload.options.include_advice,
            ctx=get_platform_ctx(),
            client_id=client_id,
            thinking_level=payload.options.thinking_level,
        )
    except LLMConfigError as e:
        raise APIError(503, "MODEL_NOT_CONFIGURED", str(e)) from e

    report = dict(result["report"])
    if not payload.options.include_evidence:
        report["evidence"] = {}

    payload_out = {
        **report,
        "analysis_id": result["analysis_id"],
        "client_id": result["client_id"],
        "created_at": result["created_at"],
        "expires_at": result["expires_at"],
        "portraits": build_portraits(report).model_dump(),
        "ai_config": result.get("ai_config") or {},
    }

    logger.info(
        "analyze_ok analysis_id=%s status=%s messages=%d ttl=%d",
        result["analysis_id"],
        report.get("status"),
        len(payload.conversation.get("messages") or []),
        settings.analysis_ttl_seconds,
    )
    return AnalyzeResponse.model_validate(payload_out)
