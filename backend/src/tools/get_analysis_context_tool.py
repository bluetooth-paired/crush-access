"""军师上下文工具：让 Agent 在需要时按需读取分析报告的某个部分。

报告本身通过 ContextVar 注入（见 agents/context.py），因此工具无需再接收
analysis_id，也不会让模型有机会访问其他用户的分析。
"""
from __future__ import annotations

import json

from langchain.tools import tool

from agents.context import ADVISOR_REPORT

_SECTION_ALIASES = {
    "metrics": "metrics",
    "指标": "metrics",
    "signals": "signals",
    "信号": "signals",
    "portraits": "portraits",
    "profile": "portraits",
    "画像": "portraits",
    "assessment": "relationship_assessment",
    "关系评估": "relationship_assessment",
    "evidence": "evidence",
    "证据": "evidence",
    "statistics": "statistics",
    "统计": "statistics",
    "advisor": "advisor",
    "建议": "advisor",
}


@tool
def get_analysis_context(section: str, limit: int = 10) -> str:
    """读取当前分析报告中的指定部分（仅限本次会话绑定的报告）。

    参数 section：metrics / signals / portraits / assessment / evidence / statistics / advisor
    参数 limit：最多返回多少条列表项，默认 10。
    返回：该部分的 JSON 字符串；section 不存在时返回 error。
    """
    report = ADVISOR_REPORT.get()
    if not report:
        return json.dumps(
            {"error": {"code": "NO_ANALYSIS_CONTEXT", "message": "当前会话没有绑定分析报告。"}},
            ensure_ascii=False,
        )

    key = _SECTION_ALIASES.get((section or "").strip().lower(), (section or "").strip())
    if key not in report or report.get(key) in (None, {}, []):
        return json.dumps(
            {
                "error": {
                    "code": "SECTION_NOT_FOUND",
                    "message": f"报告中没有 {section}，可用部分：metrics/signals/portraits/"
                    "assessment/evidence/statistics/advisor",
                }
            },
            ensure_ascii=False,
        )

    payload = report[key]
    if isinstance(payload, list) and limit and limit > 0:
        payload = payload[:limit]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        payload = {**payload, "items": payload["items"][:limit]}

    return json.dumps(payload, ensure_ascii=False)
