"""请求相关的通用依赖：客户端标识解析、平台运行上下文。"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request

from api.errors import APIError
from api.schemas import CLIENT_ID_RE

logger = logging.getLogger(__name__)

CLIENT_ID_HEADER = "X-Client-Id"


def resolve_client_id(request: Request, body_client_id: Optional[str]) -> Optional[str]:
    """优先使用请求头 X-Client-Id；与请求体不一致时拒绝，避免身份混淆。"""
    header_value = (request.headers.get(CLIENT_ID_HEADER) or "").strip() or None
    if header_value and not CLIENT_ID_RE.match(header_value):
        raise APIError(400, "INVALID_CLIENT_ID", "X-Client-Id 必须为 8-64 位字母、数字、下划线或短横线。")
    if header_value and body_client_id and header_value != body_client_id:
        raise APIError(400, "CLIENT_ID_MISMATCH", "请求头 X-Client-Id 与请求体 client_id 不一致。")
    return header_value or body_client_id


def get_platform_ctx():
    """获取平台请求上下文（独立部署时返回 None，不影响功能）。"""
    try:
        from coze_coding_utils.log.write_log import request_context

        ctx = request_context.get()
        if ctx is not None:
            return ctx
        from coze_coding_utils.runtime_ctx.context import new_context

        return new_context(method="http_api")
    except Exception as e:  # noqa: BLE001 - 非平台环境属于正常情况
        logger.debug("platform ctx unavailable: %s", type(e).__name__)
        return None
