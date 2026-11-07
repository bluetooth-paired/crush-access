"""FastAPI 应用装配：路由、CORS、错误处理、健康检查、OpenAPI 元信息。

两种用法：
1. 独立部署：`uvicorn api.app:app --host 0.0.0.0 --port 8000`
2. 挂载到已有 FastAPI 应用：`from api.app import register_into; register_into(app)`
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import register_error_handlers
from api.routes_advisor import router as advisor_router
from api.routes_analyze import router as analyze_router
from api.schemas import HealthResponse
from llm.provider import safe_provider_info
from settings import APP_NAME, APP_VERSION, get_settings
from store.factory import get_store

logger = logging.getLogger(__name__)

STARTED_AT = time.time()

DESCRIPTION = """
「申请查看你的好感度」后端服务。分为两个接口：

* **A · 互动信号分析** `POST /api/v1/analyze`：输入微信聊天记录（chat.json Schema 1.0），
  返回 metrics / daily_distribution / signals / portraits 等结构化字段，前端可直接绘图。
* **B · AI 情感军师** `POST /api/v1/advisor/chat`：基于 `analysis_id` 绑定的报告，
  由同一个 Agent 进行多轮自然语言对话，返回 reply / evidence_ids / suggestions / boundary_notes。

数据约定：消息数量、每日分布、各项占比由 Python 计算；追问、邀约、积极表达等语义事件由 LLM 打标后汇总。
`interaction_index` 只是启发式参考，**不代表真实好感概率**。

可选 AI 配置（均为向后兼容的可选字段）：

* `thinking_level`：`auto`(默认) / `low` / `medium` / `high`，按端点真实能力映射，不支持时在 `ai_config.thinking` 明确标注；
* `web_search`：默认 `false`，开启后仅使用清洗过的用户提问联网检索，不上传聊天原文。

完整字段、指标口径、错误码与 CORS 配置见仓库 `docs/api.md`。
"""

OPENAPI_TAGS = [
    {"name": "A · 互动信号分析", "description": "聊天记录的确定性指标 + LLM 语义信号"},
    {"name": "B · AI 情感军师", "description": "绑定分析报告的多轮对话"},
    {"name": "运维", "description": "健康检查与服务信息"},
]


def _configure_cors(app: FastAPI) -> None:
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_origin_regex=settings.cors_allow_origin_regex or None,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Client-Id", "Authorization"],
        expose_headers=["X-Request-Id"],
        max_age=600,
    )


def _feature_info() -> dict:
    """如实反映本部署支持的 AI 能力，不做虚假开关。"""
    from llm.provider import resolve_llm_config
    from llm.thinking import THINKING_LEVELS

    try:
        cfg = resolve_llm_config()
        thinking_supported = bool(cfg.send_thinking_body)
        provider = cfg.provider
    except Exception:  # noqa: BLE001 - 未配置模型时也要能打开健康检查
        thinking_supported = False
        provider = None

    try:
        import coze_coding_dev_sdk  # noqa: F401

        search_sdk = True
    except Exception:  # noqa: BLE001
        search_sdk = False

    return {
        "thinking_levels": list(THINKING_LEVELS),
        "thinking_supported": thinking_supported,
        "thinking_note": (
            "当前端点接受思考强度参数，实际推理深度由上游模型决定。"
            if thinking_supported
            else "当前端点不接受思考强度参数，low/medium/high 会回退到服务端默认配置。"
        ),
        "provider": provider,
        "web_search": {
            "supported": search_sdk,
            "default_enabled": False,
            "privacy": "只使用清洗后的用户提问作为搜索词，不上传聊天原文或人物档案。",
            "note": "搜索执行结果以 ai_config.web_search.performed 为准。",
        },
    }


def register_into(app: FastAPI) -> FastAPI:
    """把本服务的路由与中间件注册到给定 FastAPI 应用（幂等）。"""
    if getattr(app.state, "crush_registered", False):
        return app
    app.state.crush_registered = True

    _configure_cors(app)
    register_error_handlers(app)
    app.include_router(analyze_router, prefix="/api/v1")
    app.include_router(advisor_router, prefix="/api/v1")

    @app.get("/health", tags=["运维"], response_model=HealthResponse, summary="健康检查")
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=APP_VERSION,
            time=datetime.now(timezone.utc).isoformat(),
            store_backend=get_store().backend_name,
            model=safe_provider_info(),
            features=_feature_info(),
        )

    @app.get("/", tags=["运维"], summary="服务信息")
    def index() -> dict:
        return {
            "name": APP_NAME,
            "version": APP_VERSION,
            "uptime_seconds": round(time.time() - STARTED_AT, 1),
            "docs": "/docs",
            "openapi": "/openapi.json",
            "endpoints": {
                "analyze": "POST /api/v1/analyze",
                "advisor_chat": "POST /api/v1/advisor/chat",
                "health": "GET /health",
            },
        }

    logger.info("crush_backend_registered store=%s", get_store().backend_name)
    return app


def create_app() -> FastAPI:
    app = FastAPI(
        title="申请查看你的好感度 · 后端 API",
        version=APP_VERSION,
        description=DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    return register_into(app)


app = create_app()
