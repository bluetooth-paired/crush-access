"""军师上下文构建与证据检索。

原则：
- 只把「本次 analysis_id 绑定的报告 + 原文」放进上下文，不跨用户；
- 证据按与当前提问的关键词相关性排序，同时保证强信号证据必被带上；
- 注入给模型的原文做截断，避免超长上下文与隐私扩散。
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from analysis.analyzer import extract_json

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_WORD_RE = re.compile(r"[a-zA-Z0-9]{2,}")
_MAX_EVIDENCE_CHARS = 120


def _tokens(text: str) -> set[str]:
    """轻量分词：中文取字二元组，英文/数字取长度 >=2 的片段。"""
    text = text or ""
    tokens: set[str] = set()
    cjk = _CJK_RE.findall(text)
    for i in range(len(cjk) - 1):
        tokens.add(cjk[i] + cjk[i + 1])
    tokens.update(w.lower() for w in _WORD_RE.findall(text))
    return tokens


def _message_ids_from_report(report: dict) -> list[str]:
    ids: list[str] = []
    for signal in report.get("signals") or []:
        for mid in signal.get("evidence_ids") or []:
            if mid not in ids:
                ids.append(mid)
    for pattern in report.get("interaction_patterns") or []:
        for mid in pattern.get("message_ids") or []:
            if mid not in ids:
                ids.append(mid)
    return ids


def _strong_signal_ids(report: dict) -> list[str]:
    """积极/模糊信号优先，作为无关键词命中时的兜底证据。"""
    ordered: list[str] = []
    for category in ("positive", "ambiguous", "negative", "neutral"):
        for signal in report.get("signals") or []:
            if signal.get("category") != category:
                continue
            for mid in signal.get("evidence_ids") or []:
                if mid not in ordered:
                    ordered.append(mid)
    return ordered


def retrieve_evidence(
    conversation: dict,
    report: dict,
    question: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """返回与提问最相关的原文证据（最多 limit 条）。"""
    messages = [m for m in (conversation.get("messages") or []) if isinstance(m, dict)]
    if not messages:
        return []

    question_tokens = _tokens(question)
    referenced = set(_message_ids_from_report(report))
    strong = _strong_signal_ids(report)

    scored: list[tuple[float, int, dict]] = []
    for index, message in enumerate(messages):
        content = str(message.get("content") or "")
        if not content.strip():
            continue
        overlap = len(question_tokens & _tokens(content))
        score = float(overlap) * 2.0
        if message.get("id") in referenced:
            score += 1.0
        if message.get("id") in strong:
            score += 0.5
        # 同分时更靠近对话末尾的稍优先（近期互动通常更相关）
        scored.append((score, index, message))

    scored.sort(key=lambda item: (-item[0], -item[1]))
    selected = [item for item in scored if item[0] > 0][:limit]

    if len(selected) < limit:
        chosen_ids = {item[2].get("id") for item in selected}
        by_id = {m.get("id"): m for m in messages}
        for mid in strong:
            if len(selected) >= limit:
                break
            if mid in chosen_ids or mid not in by_id:
                continue
            selected.append((0.0, 0, by_id[mid]))

    return [
        {
            "id": m.get("id"),
            "sender": m.get("sender"),
            "sender_name": m.get("sender_name"),
            "timestamp": m.get("timestamp"),
            "content": str(m.get("content") or "")[:_MAX_EVIDENCE_CHARS],
        }
        for _, _, m in selected
    ]


def _compact_metrics(metrics: Optional[dict]) -> dict:
    if not metrics:
        return {}
    counts = metrics.get("message_counts") or {}
    return {
        "message_counts": counts,
        "participation_balance": metrics.get("participation_balance"),
        "other_question_ratio": metrics.get("other_question_ratio"),
        "shared_activity_ratio": metrics.get("shared_activity_ratio"),
        "positive_tone_ratio": metrics.get("positive_tone_ratio"),
        "interaction_index": metrics.get("interaction_index"),
        "disclaimer": metrics.get("disclaimer"),
    }


def _compact_portrait(profile: Optional[dict]) -> dict:
    """画像只保留判断所需的最小信息：等级 + 证据 ID（细节容易诱导模型复述）。"""
    if not profile:
        return {}
    compact: dict[str, Any] = {}
    for key, value in profile.items():
        if isinstance(value, dict):
            compact[key] = {
                "level": value.get("level"),
                "evidence_ids": value.get("evidence_ids") or [],
            }
    return compact


def build_advisor_context(
    report: dict,
    conversation: dict,
    question: str,
    evidence_limit: int = 8,
    web_results: Optional[list[dict[str, Any]]] = None,
) -> tuple[str, list[dict[str, Any]]]:
    """构造注入给 Agent 的上下文文本，并返回本次检索到的证据。

    注意：上下文刻意做「瘦身」——画像只给等级、信号只给名称与证据 ID。
    原因是把完整画像/指标灌进上下文时，模型倾向于先复述报告再答题。
    需要细节时 Agent 仍可通过 get_analysis_context 工具按需读取完整报告。
    """
    evidence = retrieve_evidence(conversation, report, question, evidence_limit)

    signals = [
        {
            "category": s.get("category"),
            "name": s.get("name"),
            "evidence_ids": s.get("evidence_ids") or [],
        }
        for s in (report.get("signals") or [])[:6]
    ]

    assessment = report.get("relationship_assessment") or {}
    data_quality = report.get("data_quality") or {}

    context = {
        "usage_rule": "以下内容仅供内部判断，reply 中禁止复述画像、指标清单、关系评估或报告结论。",
        "analysis_id": report.get("analysis_id"),
        "status": report.get("status"),
        "metrics": _compact_metrics(report.get("metrics")),
        "self_profile_levels": _compact_portrait(report.get("self_profile")),
        "other_profile_levels": _compact_portrait(report.get("other_profile")),
        "signals": signals,
        "relationship_stage": assessment.get("stage"),
        "assessment_confidence": assessment.get("confidence"),
        "limitations": (report.get("limitations") or [])[:5],
        "data_coverage": data_quality.get("coverage"),
        "available_evidence": evidence,
    }
    if web_results:
        context["web_search_results"] = web_results

    text = json.dumps(context, ensure_ascii=False, indent=1)
    # 控制上下文长度，避免超长报告挤占对话历史
    if len(text) > 3500:
        text = text[:3500] + "\n…（上下文已截断，可用 get_analysis_context 工具查看更多）"
    return text, evidence


_REPORT_MARKERS = (
    "self_profile",
    "other_profile",
    "interaction_index",
    "relationship_assessment",
    "人物画像",
    "互动指标",
    "关系评估",
    "分析报告",
)
_REPLY_FIELD_RE = re.compile(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)"', re.S)
_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", (text or "").strip()).strip()


def looks_like_report(text: str) -> bool:
    """判断模型是否把整份画像/报告当成了回复。"""
    body = text or ""
    hits = sum(1 for marker in _REPORT_MARKERS if marker in body)
    if hits >= 2:
        return True
    # 表格或多级编号清单同样是「报告体」，而不是一句自然语言建议
    table_rows = sum(1 for line in body.splitlines() if line.strip().startswith("|"))
    numbered_items = len(re.findall(r"(?m)^\s*\d+[.、)]\s+", body))
    return table_rows >= 2 or numbered_items >= 4


def _extract_reply_field(text: str) -> str:
    match = _REPLY_FIELD_RE.search(text or "")
    if not match:
        return ""
    try:
        return json.loads(f'"{match.group(1)}"').strip()
    except Exception:  # noqa: BLE001 - 转义异常时退回原文
        return match.group(1).strip()


def _salvage_paragraph(text: str) -> str:
    """从报告式输出里抢救出「像回答」的最后一段自然语言。"""
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", _strip_fences(text)):
        lines = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # 丢掉标题、表格、代码块、JSON 结构行
            if stripped.startswith(("#", "|", "```", "{", "}", "[", "]")):
                continue
            lines.append(stripped)
        candidate = " ".join(lines).strip()
        if len(candidate) >= 8 and not looks_like_report(candidate):
            paragraphs.append(candidate)
    return paragraphs[-1] if paragraphs else ""


def trim_reply(reply: str, max_chars: int) -> tuple[str, bool]:
    """把回复收敛到 max_chars 以内的完整句子；返回 (文本, 是否被截断)。"""
    text = re.sub(r"[ \t]+", " ", _strip_fences(reply)).strip()
    if len(text) <= max_chars:
        return text, False
    window = text[:max_chars]
    cut = max(window.rfind(mark) for mark in ("。", "！", "？", "\n"))
    if cut <= 0:
        cut = window.rfind("，")
    trimmed = (window if cut <= 0 else window[: cut + 1]).strip()
    return trimmed, True


def parse_advisor_output(text: str, max_reply_chars: int = 500) -> dict[str, Any]:
    """解析军师输出，并做格式校验与降级。

    校验顺序：
    1. 优先取 JSON 契约里的 reply；
    2. JSON 解析失败但正文里能提取 `"reply":"..."` 时按字段提取；
    3. 命中「报告式输出」时只抢救最后一段自然语言，避免整份画像被当作回复；
    4. 仍为空则用一句安全兜底，保证 reply 永不为空；
    5. 最后按句号截断到长度上限，并标记 warnings / truncated，便于前端与排查。
    """
    warnings: list[str] = []
    data = extract_json(text)

    if isinstance(data, dict) and str(data.get("reply") or "").strip():
        reply = str(data.get("reply")).strip()
        structured = True
    else:
        raw = _strip_fences(text)
        extracted = _extract_reply_field(raw)
        if extracted:
            reply, structured = extracted, True
            warnings.append("json_contract_violated_recovered")
        else:
            structured = False
            if looks_like_report(raw):
                salvaged = _salvage_paragraph(raw)
                reply = salvaged or (
                    "我先直接回答你最关心的点：从现有聊天证据看还不足以确定，"
                    "你可以把想确认的问题再具体说一句，我按证据给你分析。"
                )
                warnings.append("report_like_output_suppressed")
            else:
                reply = raw

    def _str_list(value: Any, limit: int) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()][:limit]

    # 即使模型把报告塞进了 JSON 的 reply 字段，也要拦下来，避免整份画像被当作回答
    if looks_like_report(reply):
        salvaged = _salvage_paragraph(reply)
        reply = salvaged or (
            "我先直接回答你最关心的点：从现有聊天证据看还不足以确定，"
            "你可以把想确认的问题再具体说一句，我按证据给你分析。"
        )
        warnings.append("report_like_reply_suppressed")

    reply, truncated = trim_reply(reply, max_reply_chars)
    if not reply:
        reply = "这个问题我暂时没有足够证据回答，可以再具体描述一下你想确认的点吗？"
        warnings.append("empty_reply_fallback")
    if truncated:
        warnings.append("reply_truncated")

    payload = data if isinstance(data, dict) else {}
    return {
        "reply": reply,
        "evidence_ids": _str_list(payload.get("evidence_ids"), 10),
        "suggestions": _str_list(payload.get("suggestions"), 3),
        "boundary_notes": _str_list(payload.get("boundary_notes"), 3),
        "structured": structured,
        "truncated": truncated,
        "warnings": warnings,
    }
