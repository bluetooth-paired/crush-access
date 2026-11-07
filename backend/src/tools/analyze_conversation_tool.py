"""分析工具：让 Agent 调用完整分析流水线（确定性前处理 + LLM 定性分析）。

注意：@tool 装饰后函数变为 StructuredTool 对象，禁止以普通函数方式直接调用。
"""
from __future__ import annotations

import json

from langchain.tools import tool

from analysis.analyzer import extract_json
from analysis.service import (
    ConversationValidationError,
    analyze_conversation as run_conversation_analysis,
)
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


@tool
def analyze_conversation(conversation_json: str) -> str:
    """分析一段微信聊天记录并返回结构化分析报告。

    当用户粘贴微信聊天记录（chat.json，符合 Schema 1.0：含 schema_version、source、
    chat_type、messages、metadata 字段）或请求分析聊天记录时，调用本工具。

    参数 conversation_json：聊天记录 JSON 字符串。
    返回：analysis-report 1.0 结构的 JSON 字符串（含数据质量、客观统计、双向画像、
    互动事件、好感信号、关系评估与军师建议）。
    """
    data = extract_json(conversation_json)
    if data is None:
        return json.dumps(
            {"error": {"code": "INVALID_CONVERSATION", "message": "无法解析聊天记录 JSON。"}},
            ensure_ascii=False,
        )

    ctx = request_context.get() or new_context(method="analyze_conversation")
    try:
        report = run_conversation_analysis(data, ctx=ctx)
    except ConversationValidationError as e:
        return json.dumps({"error": {"code": e.code, "message": e.message}}, ensure_ascii=False)

    return json.dumps(report.model_dump(by_alias=True), ensure_ascii=False)