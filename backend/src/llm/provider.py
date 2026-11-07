"""模型接入层：统一解析环境变量，构造 OpenAI 兼容的 ChatModel。

支持三种真实模型来源（优先级从高到低）：
1. LLM_API_KEY / LLM_BASE_URL / LLM_MODEL      任意 OpenAI 兼容服务
2. DEEPSEEK_API_KEY                             DeepSeek 官方
3. MOONSHOT_API_KEY                             Kimi / Moonshot 官方
4. 平台模型网关（COZE_INTEGRATION_MODEL_BASE_URL + COZE_WORKLOAD_IDENTITY_API_KEY）

API Key 只从环境变量读取，绝不写入源码或日志。
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

from langchain_openai import ChatOpenAI

from env_loader import load_project_env

# 保证独立部署（未经过 settings）时也能读到项目 .env
load_project_env()

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(
    os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "config/agent_llm_config.json"
)

DEFAULT_MODEL = "doubao-seed-2-0-pro-260215"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
# Kimi 的模型 ID 会随平台迭代轮换（例如 kimi-k2 / kimi-k2.5 已在 2026 年逐步下线）。
# 这里取官方当前主推的 kimi-k3；如账号可用模型不同，请用 MOONSHOT_MODEL 显式覆盖。
MOONSHOT_DEFAULT_MODEL = "kimi-k3"

# 各端点允许的输出上限。配置文件里的 10000 只适用于平台网关，
# 直接发给 DeepSeek / Moonshot 会因为超过 max_tokens 上限返回 400。
PLATFORM_MAX_COMPLETION_TOKENS = 10000
DEEPSEEK_MAX_COMPLETION_TOKENS = 8192
MOONSHOT_MAX_COMPLETION_TOKENS = 8192


def _clamp_tokens(value: int, limit: Optional[int]) -> int:
    """把输出 token 上限收敛到端点允许的范围，避免直接 400。"""
    if limit is None or limit <= 0:
        return value
    return min(value, limit)


def _infer_model_from_base_url(base_url: str) -> str:
    """根据显式指定的 OpenAI 兼容端点推导厂商默认模型名。"""
    lowered = (base_url or "").lower()
    if "deepseek" in lowered:
        return DEEPSEEK_DEFAULT_MODEL
    if "moonshot" in lowered:
        return MOONSHOT_DEFAULT_MODEL
    return ""


class LLMConfigError(RuntimeError):
    """模型配置缺失或不可用。"""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_completion_tokens: int = 4096
    timeout: int = 120
    thinking: str = "disabled"
    send_thinking_body: bool = False


def _load_file_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("config") or {}
    except Exception:  # 配置文件缺失时使用内置默认值
        return {}


def resolve_llm_config() -> LLMConfig:
    """解析模型配置，返回不可变配置对象。"""
    file_cfg = _load_file_config()

    temperature = float(os.getenv("LLM_TEMPERATURE") or file_cfg.get("temperature", 0.7))
    top_p = float(os.getenv("LLM_TOP_P") or file_cfg.get("top_p", 0.9))
    max_tokens = int(
        os.getenv("LLM_MAX_COMPLETION_TOKENS")
        or file_cfg.get("max_completion_tokens", 4096)
    )
    timeout = int(os.getenv("LLM_TIMEOUT_SECONDS") or file_cfg.get("timeout", 120))
    thinking = (os.getenv("LLM_THINKING") or file_cfg.get("thinking") or "disabled").lower()
    file_model = (file_cfg.get("model") or DEFAULT_MODEL).strip()
    explicit_model = (os.getenv("LLM_MODEL") or "").strip()
    default_model = explicit_model or file_model
    explicit_base = (os.getenv("LLM_BASE_URL") or "").strip()

    # 1) 显式 OpenAI 兼容配置
    explicit_key = (os.getenv("LLM_API_KEY") or "").strip()
    if explicit_key:
        # 未显式给模型名时，按端点推导，避免把平台的豆包模型名发给 DeepSeek/Kimi。
        model = explicit_model or _infer_model_from_base_url(explicit_base)
        if not model:
            if not explicit_base:
                raise LLMConfigError(
                    "已配置 LLM_API_KEY，但未设置 LLM_BASE_URL / LLM_MODEL。"
                    "请同时指定 OpenAI 兼容端点与模型名后重试。"
                )
            # 自建网关：允许沿用配置文件中的模型名，但要求调用方明确知晓
            model = file_model
        limit = None
        lowered = explicit_base.lower()
        if "deepseek" in lowered:
            limit = int(os.getenv("DEEPSEEK_MAX_OUTPUT_TOKENS") or DEEPSEEK_MAX_COMPLETION_TOKENS)
        elif "moonshot" in lowered:
            limit = int(os.getenv("MOONSHOT_MAX_OUTPUT_TOKENS") or MOONSHOT_MAX_COMPLETION_TOKENS)
        return LLMConfig(
            provider="openai-compatible",
            model=model,
            api_key=explicit_key,
            base_url=explicit_base,
            temperature=temperature,
            top_p=top_p,
            max_completion_tokens=_clamp_tokens(max_tokens, limit),
            timeout=timeout,
            thinking=thinking,
            send_thinking_body=False,
        )

    # 2) DeepSeek
    deepseek_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if deepseek_key:
        return LLMConfig(
            provider="deepseek",
            # 注意：不能用配置文件里的默认模型（那通常是豆包/平台模型 ID），
            # 否则会把豆包模型名发给 DeepSeek 端点导致 400。
            model=(os.getenv("DEEPSEEK_MODEL") or DEEPSEEK_DEFAULT_MODEL),
            api_key=deepseek_key,
            base_url=(os.getenv("DEEPSEEK_BASE_URL") or DEEPSEEK_BASE_URL).strip(),
            temperature=temperature,
            top_p=top_p,
            max_completion_tokens=_clamp_tokens(
                max_tokens,
                int(os.getenv("DEEPSEEK_MAX_OUTPUT_TOKENS") or DEEPSEEK_MAX_COMPLETION_TOKENS),
            ),
            timeout=timeout,
            thinking=thinking,
            send_thinking_body=False,
        )

    # 3) Kimi / Moonshot
    moonshot_key = (os.getenv("MOONSHOT_API_KEY") or "").strip()
    if moonshot_key:
        return LLMConfig(
            provider="moonshot",
            model=(os.getenv("MOONSHOT_MODEL") or MOONSHOT_DEFAULT_MODEL),
            api_key=moonshot_key,
            base_url=(os.getenv("MOONSHOT_BASE_URL") or MOONSHOT_BASE_URL).strip(),
            temperature=temperature,
            top_p=top_p,
            max_completion_tokens=_clamp_tokens(
                max_tokens,
                int(os.getenv("MOONSHOT_MAX_OUTPUT_TOKENS") or MOONSHOT_MAX_COMPLETION_TOKENS),
            ),
            timeout=timeout,
            thinking=thinking,
            send_thinking_body=False,
        )

    # 4) 平台模型网关
    platform_key = (os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY") or "").strip()
    platform_base = (os.getenv("COZE_INTEGRATION_MODEL_BASE_URL") or "").strip()
    if platform_key and platform_base:
        return LLMConfig(
            provider="platform-gateway",
            model=default_model,
            api_key=platform_key,
            base_url=platform_base,
            temperature=temperature,
            top_p=top_p,
            max_completion_tokens=max_tokens,
            timeout=timeout,
            thinking=thinking,
            send_thinking_body=True,
        )

    raise LLMConfigError(
        "未配置模型 API Key。请设置 LLM_API_KEY（或 DEEPSEEK_API_KEY / MOONSHOT_API_KEY）后重试。"
    )


def is_model_configured() -> bool:
    try:
        resolve_llm_config()
        return True
    except LLMConfigError:
        return False


def thinking_plan(level: Optional[str] = None):
    """返回本次请求的思考强度执行计划（不发起模型调用）。"""
    from llm.thinking import plan_thinking

    try:
        cfg = resolve_llm_config()
        supports = cfg.send_thinking_body
    except LLMConfigError:
        supports = False
    return plan_thinking(level, supports_thinking_body=supports)


def build_chat_model(
    ctx=None,
    *,
    streaming: bool = False,
    temperature: Optional[float] = None,
    max_completion_tokens: Optional[int] = None,
    thinking_level: Optional[str] = None,
    json_mode: bool = False,
) -> ChatOpenAI:
    """构造 ChatOpenAI 实例（真实模型调用，不做任何 mock）。

    thinking_level: auto / low / medium / high。仅在模型端点支持时下发对应参数，
    不支持时按服务端默认配置执行（详见 llm.thinking）。
    """
    cfg = resolve_llm_config()

    headers = {}
    if ctx is not None and cfg.provider == "platform-gateway":
        try:
            from coze_coding_utils.runtime_ctx.context import default_headers

            headers = default_headers(ctx) or {}
        except Exception:  # 独立部署时无平台上下文
            headers = {}

    kwargs = dict(
        model=cfg.model,
        api_key=cfg.api_key,
        base_url=cfg.base_url or None,
        temperature=cfg.temperature if temperature is None else temperature,
        top_p=cfg.top_p,
        max_tokens=cfg.max_completion_tokens
        if max_completion_tokens is None
        else max_completion_tokens,
        timeout=cfg.timeout,
        streaming=streaming,
        default_headers=headers,
    )
    if cfg.send_thinking_body:
        kwargs["extra_body"] = {"thinking": {"type": cfg.thinking}}

    # 结构化输出模式：显著降低「模型夹带说明文字导致 JSON 解析失败」的概率。
    # 少数自建网关不支持 response_format，可通过 LLM_JSON_MODE=false 关闭。
    json_mode_enabled = (os.getenv("LLM_JSON_MODE") or "true").strip().lower() not in {
        "0", "false", "off", "no",
    }
    if json_mode and json_mode_enabled:
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}

    # 按请求覆盖思考强度：只在端点支持时下发，绝不假装生效
    if thinking_level is not None:
        from llm.thinking import plan_thinking

        plan = plan_thinking(thinking_level, supports_thinking_body=cfg.send_thinking_body)
        if plan.sent_parameters:
            kwargs["extra_body"] = plan.sent_parameters

    return ChatOpenAI(**kwargs)


def safe_provider_info() -> dict:
    """健康检查用：只暴露 provider / model，不暴露 Key。"""
    try:
        cfg = resolve_llm_config()
        return {"configured": True, "provider": cfg.provider, "model": cfg.model}
    except LLMConfigError as e:
        return {"configured": False, "provider": None, "model": None, "detail": str(e)}
