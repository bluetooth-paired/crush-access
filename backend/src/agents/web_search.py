"""联网搜索（按需开启，默认关闭）。

隐私约束（硬性）：
- 只把「用户当前这一句提问」清洗后作为搜索词；
- **绝不**把聊天原文、证据 message、人物档案、分析报告放进搜索请求；
- 返回给前端的 search 元信息也只包含检索状态与结果条数，不含原始聊天内容。

说明：搜索能力来自平台搜索集成（coze-coding-dev-sdk.SearchClient）。
不可用时返回 performed=False 与错误说明，不会伪造搜索结果。
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

MAX_QUERY_CHARS = 60
MAX_RESULTS = 3

# 消息 ID（m001）与长引用片段（可能是聊天原文）：从搜索词中剔除
_MSG_ID_RE = re.compile(r"\bm\d{1,6}\b")
_QUOTED_RE = re.compile(r"[「“\"'《]([^」”\"'》]{8,})[」”\"'》]")
# 去掉「引用那条」这类指向聊天原文的残句，避免搜索词里出现对话指代
_DANGLING_REF_RE = re.compile(r"(引用|参考|根据)\s*(这|那|该)?\s*(条|句|段|几)?\s*(消息|话|原文|记录)?")
_WS_RE = re.compile(r"\s+")


def build_search_query(question: str, max_chars: int = MAX_QUERY_CHARS) -> str:
    """把用户提问清洗成隐私安全的搜索词。

    规则：去掉消息 ID 引用、去掉引号内长片段（可能粘贴了聊天原文）、压缩空白、截断。
    """
    text = question or ""
    text = _MSG_ID_RE.sub(" ", text)
    text = _QUOTED_RE.sub(" ", text)
    text = _DANGLING_REF_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].strip()
    return text


def perform_web_search(
    query: str,
    ctx=None,
    max_results: int = MAX_RESULTS,
) -> tuple[list[dict[str, Any]], Optional[str]]:
    """执行真实联网搜索。

    返回 (results, error)。error 非空表示未成功执行（不会返回伪造结果）。
    """
    if not query:
        return [], "搜索词为空，已跳过联网搜索。"

    try:
        from coze_coding_dev_sdk import SearchClient
    except Exception as e:  # noqa: BLE001 - 独立部署时可能未安装 SDK
        logger.warning("web_search_unavailable error=%s", type(e).__name__)
        return [], "当前部署未提供搜索集成，联网搜索未执行。"

    try:
        if ctx is None:
            try:
                from coze_coding_utils.runtime_ctx.context import new_context

                ctx = new_context(method="advisor.web_search")
            except Exception:  # noqa: BLE001
                ctx = None

        client = SearchClient(ctx=ctx) if ctx is not None else SearchClient()
        response = client.web_search(query=query, count=max_results, need_summary=True)
        items = getattr(response, "web_items", None) or []
        results = [
            {
                "title": (getattr(item, "title", "") or "")[:120],
                "url": getattr(item, "url", "") or "",
                "snippet": (getattr(item, "snippet", "") or "")[:240],
                "summary": (getattr(item, "summary", "") or "")[:300],
            }
            for item in items[:max_results]
        ]
        if not results:
            return [], "搜索已执行，但没有返回结果。"
        return results, None
    except Exception as e:  # noqa: BLE001 - 搜索失败不能阻断军师回复
        logger.warning("web_search_failed error=%s", type(e).__name__)
        return [], f"联网搜索执行失败：{type(e).__name__}。"
