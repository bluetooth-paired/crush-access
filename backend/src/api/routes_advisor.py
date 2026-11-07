"""API B：AI 情感军师多轮对话 POST /api/v1/advisor/chat"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from agents.service import AdvisorError, AgentService, get_agent_service
from api.deps import get_platform_ctx, resolve_client_id
from api.errors import APIError
from api.schemas import AdvisorChatRequest, AdvisorChatResponse
from llm.provider import LLMConfigError
from settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["B · AI 情感军师"])


@router.post(
    "/advisor/chat",
    response_model=AdvisorChatResponse,
    summary="基于已有分析报告进行多轮情感军师对话",
    description=(
        "传入 analysis_id 与用户提问，服务端读取该报告与必要原文证据，"
        "由同一个 Agent 生成自然语言回复，并返回引用的 evidence_ids / 沟通建议 / 边界提醒。\n\n"
        "首次调用不传 session_id，服务端会创建并返回；后续对话带上同一个 session_id 即可延续上下文。"
    ),
)
def advisor_chat(
    payload: AdvisorChatRequest,
    request: Request,
    service: AgentService = Depends(get_agent_service),
) -> AdvisorChatResponse:
    settings = get_settings()
    if len(payload.message) > settings.max_advisor_message_chars:
        raise APIError(
            400,
            "MESSAGE_TOO_LONG",
            f"message 超过 {settings.max_advisor_message_chars} 字符上限。",
        )

    client_id = resolve_client_id(request, payload.client_id)

    try:
        result = service.advisor_chat(
            analysis_id=payload.analysis_id,
            message=payload.message,
            session_id=payload.session_id,
            client_id=client_id,
            ctx=get_platform_ctx(),
            thinking_level=payload.thinking_level,
            web_search=payload.web_search,
        )
    except AdvisorError as e:
        raise APIError(e.status_code, e.code, e.message) from e
    except LLMConfigError as e:
        raise APIError(503, "MODEL_NOT_CONFIGURED", str(e)) from e

    logger.info(
        "advisor_ok analysis_id=%s session_id=%s turn=%d",
        result["analysis_id"], result["session_id"], result["turn"],
    )
    return AdvisorChatResponse.model_validate(result)
