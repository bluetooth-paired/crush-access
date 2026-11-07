"""唯一 Agent：同一实例承担「对话式关系分析」与「情感军师多轮交流」两种能力。

- 分析能力：通过 analyze_conversation 工具调用完整分析流水线；
- 军师能力：由上层把分析报告注入上下文（ContextVar），Agent 读取 get_analysis_context
  工具可进一步查看报告细节；
- 两种模式的系统提示由 dynamic_prompt 中间件在每次模型调用前动态决定，
  因此只需要一个 Agent 实例、一个 checkpointer、一套对话记忆。
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Annotated

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain_core.messages import AnyMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages

from agents.context import ADVISOR_CONTEXT, MODE
from agents.prompts import ADVISOR_SYSTEM_PROMPT, ANALYSIS_FALLBACK_PROMPT
from llm.provider import build_chat_model
from tools.analyze_conversation_tool import analyze_conversation
from tools.get_analysis_context_tool import get_analysis_context

logger = logging.getLogger(__name__)

LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 20 轮对话（40 条消息），防止上下文过长
MAX_MESSAGES = 40


def _windowed_messages(old, new):
    """滑动窗口：只保留最近 MAX_MESSAGES 条消息。"""
    return add_messages(old, new)[-MAX_MESSAGES:]  # type: ignore


class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]


def _load_analysis_prompt() -> str:
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            sp = (json.load(f) or {}).get("sp") or ""
        return sp or ANALYSIS_FALLBACK_PROMPT
    except (OSError, json.JSONDecodeError):
        return ANALYSIS_FALLBACK_PROMPT


@lru_cache(maxsize=1)
def _analysis_prompt() -> str:
    return _load_analysis_prompt()


@dynamic_prompt
def _system_prompt(request: ModelRequest) -> str:
    """每次模型调用前决定系统提示：军师模式带报告上下文，否则用分析助手提示。"""
    if MODE.get() == "advisor":
        return ADVISOR_SYSTEM_PROMPT.format(context=ADVISOR_CONTEXT.get() or "（暂无上下文）")
    return _analysis_prompt()


@lru_cache(maxsize=1)
def _checkpointer():
    """全局单例 checkpointer：保证多轮对话记忆在请求之间延续。"""
    try:
        from storage.memory.memory_saver import get_memory_saver

        return get_memory_saver()
    except Exception as e:  # noqa: BLE001 - 独立部署时无平台存储，退回内存
        logger.warning("get_memory_saver 不可用，退回 MemorySaver：%s", type(e).__name__)
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()


@lru_cache(maxsize=4)
def _build_agent_cached(thinking_level: str = "auto"):
    llm = build_chat_model(ctx=None, streaming=True, thinking_level=thinking_level)
    return create_agent(
        model=llm,
        tools=[analyze_conversation, get_analysis_context],
        middleware=[_system_prompt],
        checkpointer=_checkpointer(),
        state_schema=AgentState,
    )


def build_agent(ctx=None, thinking_level: str = "auto"):
    """返回唯一 Agent 实例（按 thinking_level 复用，进程内缓存）。

    说明：思考强度是模型客户端构造参数，因此按档位缓存同一个 Agent 定义；
    工具、检查点、系统提示与对话记忆在所有档位间共享，仍是同一个 Agent。
    """
    if ctx is not None:
        logger.debug("build_agent called with request ctx; 复用缓存 Agent")
    return _build_agent_cached(thinking_level or "auto")


def reset_agent() -> None:
    """测试用：清空 Agent 单例缓存。"""
    _build_agent_cached.cache_clear()
    _analysis_prompt.cache_clear()
    _checkpointer.cache_clear()
