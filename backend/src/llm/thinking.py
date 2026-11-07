"""思考强度（thinking_level）映射。

设计原则：
- 只把「确实会下发给模型端点」的参数算作生效；
- 端点不支持时返回 supported=False，并说明已回退到服务端默认配置，
  绝不返回「已生效」的假象；
- 上游模型是否真的按强度推理由模型厂商决定，网关不返回 reasoning token 明细，
  服务端不做结果伪造。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

THINKING_LEVELS = ("auto", "low", "medium", "high")
DEFAULT_THINKING_LEVEL = "auto"


@dataclass(frozen=True)
class ThinkingPlan:
    """一次请求的思考强度执行计划。"""

    requested: str
    applied: str
    supported: bool
    sent_parameters: dict[str, Any] = field(default_factory=dict)
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "requested": self.requested,
            "applied": self.applied,
            "supported": self.supported,
            "sent_parameters": self.sent_parameters,
            "note": self.note,
        }


def normalize_level(level: Optional[str]) -> str:
    value = (level or DEFAULT_THINKING_LEVEL).strip().lower()
    if value not in THINKING_LEVELS:
        raise ValueError(f"thinking_level 只支持 {', '.join(THINKING_LEVELS)}")
    return value


def plan_thinking(
    level: Optional[str],
    *,
    supports_thinking_body: bool,
) -> ThinkingPlan:
    """把 low/medium/high 映射为真实下发的请求参数。

    supports_thinking_body 表示当前模型端点是否接受 `thinking` 扩展参数
    （由 provider 配置决定：平台网关为 True，DeepSeek / Kimi / 自定义端点默认 False）。
    """
    requested = normalize_level(level)

    if requested == "auto":
        return ThinkingPlan(
            requested=requested,
            applied="server-default",
            supported=True,
            sent_parameters={},
            note="使用服务端默认思考配置（环境变量 LLM_THINKING），本次请求不覆盖。",
        )

    if not supports_thinking_body:
        return ThinkingPlan(
            requested=requested,
            applied="server-default",
            supported=False,
            sent_parameters={},
            note=(
                "当前模型端点不支持思考强度参数，已按服务端默认配置执行；"
                "该档位未生效（不会伪造为已生效）。"
            ),
        )

    mapping: dict[str, tuple[dict[str, Any], str]] = {
        "low": (
            {"thinking": {"type": "disabled"}},
            "已下发 thinking=disabled：关闭深度思考，优先响应速度与成本。",
        ),
        "medium": (
            {"thinking": {"type": "enabled"}},
            "已下发 thinking=enabled：使用模型默认思考预算。",
        ),
        "high": (
            {"thinking": {"type": "enabled", "reasoning_effort": "high"}},
            "已下发 thinking=enabled + reasoning_effort=high：请求更高推理强度；"
            "实际推理深度由上游模型决定，网关不返回 reasoning token 明细。",
        ),
    }
    sent, note = mapping[requested]
    return ThinkingPlan(
        requested=requested,
        applied=requested,
        supported=True,
        sent_parameters=sent,
        note=note,
    )
