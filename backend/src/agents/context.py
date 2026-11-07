"""Agent 运行期上下文：用 ContextVar 在「同一次请求」内区分能力模式。

同一个 Agent 实例承担两种能力：
- analysis：对话式分析（用户直接贴聊天记录，调用 analyze_conversation 工具）
- advisor：情感军师（读取已存在的分析报告，多轮自然语言交流）

模式与报告上下文通过 ContextVar 传递，避免为两种能力各建一个 Agent。
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

MODE: ContextVar[str] = ContextVar("agent_mode", default="analysis")
ADVISOR_CONTEXT: ContextVar[str] = ContextVar("advisor_context", default="")
ADVISOR_REPORT: ContextVar[Optional[dict]] = ContextVar("advisor_report", default=None)


def set_advisor_mode(context_text: str, report: dict):
    """切换到军师模式，返回 tokens 供 finally 中重置。"""
    return (
        MODE.set("advisor"),
        ADVISOR_CONTEXT.set(context_text),
        ADVISOR_REPORT.set(report),
    )


def reset_mode(tokens) -> None:
    mode_token, context_token, report_token = tokens
    MODE.reset(mode_token)
    ADVISOR_CONTEXT.reset(context_token)
    ADVISOR_REPORT.reset(report_token)
