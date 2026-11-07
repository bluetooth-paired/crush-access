"""确定性指标计算：所有数字由 Python 汇总，LLM 只提供单条消息的语义标记。

设计原则：
- 每个指标都给出明确公式与分母，随响应一起返回，前端可直接展示口径；
- 语义类指标（提问 / 共同活动 / 积极语气）由 LLM 打标，Python 汇总；
  LLM 未返回标记时退化为关键词规则，并在 semantic_detection.method 中如实标注；
- 「互动参考指数」是启发式参考，不是好感概率。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Optional

from analysis.preprocessor import normalize_sender
from analysis.schema import (
    DailyPoint,
    Message,
    MessageCounts,
    MessageFlag,
    MetricComponent,
    MetricFormula,
    Metrics,
    SemanticDetection,
    Statistics,
)

# ---- 关键词兜底规则（仅在 LLM 未返回 message_flags 时启用） ----
_QUESTION_RE = re.compile(
    r"[?？]|吗|呢|什么|怎么|为什么|哪|多少|几点|是不是|要不要|好不好|行不行|可以吗|有空"
)
_SHARED_ACTIVITY_RE = re.compile(
    r"一起|一块|陪你|带你|我们去|咱们|约|见面|出来|聚|看电影|看展|展览|吃饭|喝|玩|走走|周末|有空"
)
_POSITIVE_TONE_RE = re.compile(
    r"哈哈|开心|高兴|好呀|太好|喜欢|想你|期待|棒|可爱|谢谢|辛苦|注意身体|别感冒|照顾好|加油|～|~"
)

# 互动参考指数权重（总和 = 1.0）
WEIGHTS = {
    "participation_balance": 0.25,
    "conversation_density": 0.15,
    "other_question_ratio": 0.25,
    "shared_activity_ratio": 0.20,
    "positive_tone_ratio": 0.15,
}

DENSITY_FULL_SCORE_MESSAGES = 100
QUESTION_FULL_SCORE_RATIO = 0.30
SHARED_FULL_SCORE_RATIO = 0.20


def _message_date(timestamp: str) -> Optional[str]:
    """按消息自带时区取“当地日期”，保证每日分布符合用户直觉。"""
    if not timestamp:
        return None
    raw = str(timestamp).strip().replace("Z", "+00:00")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date().isoformat()
    except (ValueError, TypeError):
        return None


def _is_analyzable_text(message: Message) -> bool:
    return message.type == "text" and bool((message.content or "").strip())


def _ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def compute_daily_distribution(messages: Iterable[Message]) -> list[DailyPoint]:
    """每日消息数量（按消息自身时区的日期分组，按日期升序）。"""
    buckets: dict[str, dict[str, int]] = {}
    for message in messages:
        date = _message_date(message.timestamp)
        if date is None:
            continue
        bucket = buckets.setdefault(date, {"self": 0, "other": 0, "unknown": 0})
        bucket[normalize_sender(message.sender)] += 1

    return [
        DailyPoint(
            date=date,
            self_count=bucket["self"],
            other_count=bucket["other"],
            unknown_count=bucket["unknown"],
            total=bucket["self"] + bucket["other"] + bucket["unknown"],
        )
        for date, bucket in sorted(buckets.items())
    ]


def _keyword_flags(messages: Iterable[Message]) -> list[MessageFlag]:
    flags: list[MessageFlag] = []
    for message in messages:
        if not _is_analyzable_text(message):
            continue
        content = message.content or ""
        flags.append(
            MessageFlag(
                id=message.id,
                is_question=bool(_QUESTION_RE.search(content)),
                shared_activity=bool(_SHARED_ACTIVITY_RE.search(content)),
                positive_tone=bool(_POSITIVE_TONE_RE.search(content)),
            )
        )
    return flags


def _normalize_flags(
    messages: list[Message], flags: Optional[list[MessageFlag]]
) -> tuple[dict[str, MessageFlag], SemanticDetection]:
    text_messages = [m for m in messages if _is_analyzable_text(m)]
    valid_ids = {m.id for m in text_messages}

    if flags:
        # 同一条消息可能出现多条标记，必须按「或」合并，避免后出现的标记覆盖前者
        cleaned: dict[str, MessageFlag] = {}
        for flag in flags:
            if flag.id not in valid_ids:
                continue
            prev = cleaned.get(flag.id)
            if prev is None:
                cleaned[flag.id] = flag.model_copy()
                continue
            prev.is_question = prev.is_question or flag.is_question
            prev.shared_activity = prev.shared_activity or flag.shared_activity
            prev.positive_tone = prev.positive_tone or flag.positive_tone
        if cleaned:
            return cleaned, SemanticDetection(
                method="llm",
                text_message_count=len(text_messages),
                flagged_message_count=len(cleaned),
                note="语义标记由 LLM 识别，Python 仅做汇总统计。",
            )

    fallback = {f.id: f for f in _keyword_flags(text_messages)}
    return fallback, SemanticDetection(
        method="keyword_fallback",
        text_message_count=len(text_messages),
        flagged_message_count=len(fallback),
        note="本次未获得 LLM 语义标记，已退化为关键词规则，指标仅供粗略参考。",
    )


def _count_flag(flags: dict[str, MessageFlag], ids: Iterable[str], attr: str) -> int:
    return sum(1 for i in ids if i in flags and bool(getattr(flags[i], attr)))


def compute_metrics(
    messages: list[Message],
    statistics: Statistics,
    flags: Optional[list[MessageFlag]] = None,
) -> Metrics:
    """计算 API A 全部定量指标。"""
    total = len(messages)
    self_count = statistics.self_stats.message_count
    other_count = statistics.other_stats.message_count
    unknown_count = statistics.unknown_stats.message_count

    text_messages = [m for m in messages if _is_analyzable_text(m)]
    other_text_ids = [m.id for m in text_messages if normalize_sender(m.sender) == "other"]
    all_text_ids = [m.id for m in text_messages]

    flag_map, detection = _normalize_flags(messages, flags)

    # 参与平衡：2*min(self, other) / (self + other)，未知发送者不计入分子分母
    known_total = self_count + other_count
    participation_balance = (
        round(2 * min(self_count, other_count) / known_total, 4) if known_total > 0 else None
    )

    # TA 提问占比：分母 = TA 的可分析文本消息数
    other_questions = _count_flag(flag_map, other_text_ids, "is_question")
    other_question_ratio = _ratio(other_questions, len(other_text_ids))

    # 共同活动表达占比：分母 = 全部可分析文本消息数
    shared_count = _count_flag(flag_map, all_text_ids, "shared_activity")
    shared_activity_ratio = _ratio(shared_count, len(all_text_ids))

    # 积极语气占比：分母 = 全部可分析文本消息数
    positive_count = _count_flag(flag_map, all_text_ids, "positive_tone")
    positive_tone_ratio = _ratio(positive_count, len(all_text_ids))

    components = [
        MetricComponent(
            key="participation_balance",
            label="参与平衡度",
            raw_value=participation_balance,
            normalized_score=participation_balance or 0.0,
            weight=WEIGHTS["participation_balance"],
            available=participation_balance is not None,
            note="双方消息量越接近 1.0，说明对话越双向。",
        ),
        MetricComponent(
            key="conversation_density",
            label="对话密度",
            raw_value=float(total),
            normalized_score=min(1.0, total / DENSITY_FULL_SCORE_MESSAGES),
            weight=WEIGHTS["conversation_density"],
            note=f"消息总数达到 {DENSITY_FULL_SCORE_MESSAGES} 条即视为满分。",
        ),
        MetricComponent(
            key="other_question_ratio",
            label="TA 提问占比",
            raw_value=other_question_ratio,
            normalized_score=min(1.0, (other_question_ratio or 0.0) / QUESTION_FULL_SCORE_RATIO),
            weight=WEIGHTS["other_question_ratio"],
            available=other_question_ratio is not None,
            note=f"达到 {int(QUESTION_FULL_SCORE_RATIO * 100)}% 即视为满分。",
        ),
        MetricComponent(
            key="shared_activity_ratio",
            label="共同活动表达占比",
            raw_value=shared_activity_ratio,
            normalized_score=min(1.0, (shared_activity_ratio or 0.0) / SHARED_FULL_SCORE_RATIO),
            weight=WEIGHTS["shared_activity_ratio"],
            available=shared_activity_ratio is not None,
            note=f"达到 {int(SHARED_FULL_SCORE_RATIO * 100)}% 即视为满分。",
        ),
        MetricComponent(
            key="positive_tone_ratio",
            label="积极语气占比",
            raw_value=positive_tone_ratio,
            normalized_score=min(1.0, positive_tone_ratio or 0.0),
            weight=WEIGHTS["positive_tone_ratio"],
            available=positive_tone_ratio is not None,
            note="直接使用积极语气消息占比作为得分。",
        ),
    ]

    for component in components:
        component.contribution = round(component.normalized_score * component.weight, 4)

    index = round(100 * sum(c.contribution for c in components), 1)

    formulas = [
        MetricFormula(
            key="message_counts",
            label="双方消息数量",
            formula="self / other / unknown 分别计数；total = self + other + unknown",
            denominator="无（绝对数量）",
        ),
        MetricFormula(
            key="participation_balance",
            label="参与平衡",
            formula="2 × min(self, other) / (self + other)",
            denominator="self + other（不含 unknown）",
            note="取值 0~1，1 表示双方消息量完全相同；无已被确认的发送者时为 null。",
        ),
        MetricFormula(
            key="other_question_ratio",
            label="TA 提问占比",
            formula="TA 中含疑问/追问的消息数 / TA 的可分析文本消息数",
            denominator="TA 的可分析文本消息数（type=text 且内容非空）",
        ),
        MetricFormula(
            key="shared_activity_ratio",
            label="共同活动表达占比",
            formula="含共同活动表达的消息数 / 全部可分析文本消息数",
            denominator="全部可分析文本消息数",
            note="共同活动指「一起 / 见面 / 约 / 看电影」等双方共同参与的表述。",
        ),
        MetricFormula(
            key="positive_tone_ratio",
            label="积极语气占比",
            formula="含积极语气（开心、期待、致谢、关心等）的消息数 / 全部可分析文本消息数",
            denominator="全部可分析文本消息数",
        ),
        MetricFormula(
            key="interaction_index",
            label="互动参考指数",
            formula=(
                "100 × (0.25×参与平衡 + 0.15×min(1, 消息数/100) "
                "+ 0.25×min(1, TA提问占比/0.30) "
                "+ 0.20×min(1, 共同活动占比/0.20) + 0.15×积极语气占比)"
            ),
            denominator="各子项先归一化到 0~1 再加权",
            note="启发式参考值，不是好感概率；数据不足的子项按 0 计入并在 available 标记。",
        ),
    ]

    return Metrics(
        message_counts=MessageCounts(
            self_count=self_count,
            other_count=other_count,
            unknown_count=unknown_count,
            total=total,
        ),
        participation_balance=participation_balance,
        other_question_ratio=other_question_ratio,
        shared_activity_ratio=shared_activity_ratio,
        positive_tone_ratio=positive_tone_ratio,
        interaction_index=index,
        interaction_index_components=components,
        formulas=formulas,
        semantic_detection=detection,
    )
