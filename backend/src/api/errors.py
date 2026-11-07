"""统一错误响应格式。

所有错误都返回同一种结构，方便前端统一处理：

```json
{"error": {"code": "ANALYSIS_NOT_FOUND", "message": "找不到分析报告 ...", "details": null}}
```
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from analysis.service import ConversationValidationError
from store.base import (
    RecordExpired,
    RecordForbidden,
    RecordMissingCredential,
    RecordNotFound,
)


class APIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api_error(request: Request, exc: APIError):
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(ConversationValidationError)
    async def _conversation_error(request: Request, exc: ConversationValidationError):
        return error_response(400, exc.code, exc.message)

    @app.exception_handler(RecordNotFound)
    async def _not_found(request: Request, exc: RecordNotFound):
        return error_response(404, "ANALYSIS_NOT_FOUND", str(exc))

    @app.exception_handler(RecordExpired)
    async def _expired(request: Request, exc: RecordExpired):
        return error_response(410, "ANALYSIS_EXPIRED", str(exc))

    @app.exception_handler(RecordForbidden)
    async def _forbidden(request: Request, exc: RecordForbidden):
        return error_response(403, "ANALYSIS_FORBIDDEN", str(exc))

    @app.exception_handler(RecordMissingCredential)
    async def _missing_credential(request: Request, exc: RecordMissingCredential):
        # 缺少身份凭据：401，提示前端补 X-Client-Id（分析响应里已返回 client_id）
        return error_response(
            401,
            "CLIENT_ID_REQUIRED",
            str(exc),
            details={"header": "X-Client-Id", "body_field": "client_id"},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        return error_response(
            422,
            "INVALID_REQUEST",
            "请求参数校验失败。",
            details=[{"loc": list(e.get("loc", [])), "msg": e.get("msg")} for e in exc.errors()],
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        return error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))
