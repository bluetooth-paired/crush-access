"""确定性前处理：数据质量检查 + 客观统计 + 时间/轮次分析。

重要约束：
- 只做可以用代码精确计算的统计，绝不把统计交给大模型。
- 不修改原始消息；不根据少量消息推断人格/心理。
- 私密聊天正文绝不写入日志（只记录聚合数字）。
"""
from __future__ import annotations

import logging
import statistics as _statistics
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from analysis.schema import (
    DataQuality,
    Message,
    SenderStats,
    Statistics,
)

logger = logging.getLogger(__name__)

# 判定「新一段对话」的时间阈值（秒）。仅用于主动开启比例的娱乐化估计。
SESSION_GAP_SECONDS = 6 * 3600
# 判定「可能来自部分导出」的疑似缺失阈值（秒）。
BIG_GAP_SECONDS = 7 * 86400
# 少于该消息数时，主动开启比例视为数据不足。
MIN_MESSAGES_FOR_INITIATION = 10

VALID_SENDERS = {"self", "other", "unknown"}


def normalize_sender(sender: str) -> str:
    """把 sender 归一化为 self / other / unknown；非法值一律归为 unknown（不擅自猜测归属）。"""
    s = (sender or "").strip().lower()
    if s in ("self", "other"):
        return s
    return "unknown"


def to_epoch(timestamp: str) -> Optional[float]:
    """解析时间戳为 UTC epoch 秒；无法解析返回 None。

    时区处理（与文档一致，避免同一份数据两次运行结果不同）：
    - 带时区（`+08:00` / `Z`）：按自身时区解析；
    - 无时区（`2026-11-07T23:30:00`）：视为**本地时间**，用
      `ASSUME_NAIVE_TZ_OFFSET_HOURS`（默认 +8，微信导出常见）补上偏移；
    - 无法解析：返回 None，由数据质量检查记入 limitations，不猜测。
    """
    if timestamp is None:
        return None
    s = str(timestamp).strip()
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone(timedelta(hours=_naive_offset_hours())))
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def _naive_offset_hours() -> int:
    """无时区时间戳的默认偏移小时数（来自配置，读取失败时回退 +8）。"""
    try:
        from settings import get_settings

        return get_settings().naive_tz_offset_hours
    except Exception:  # noqa: BLE001 - 独立测试/无配置环境下的安全默认值
        return 8


def _format_epoch(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def assess_data_quality(messages: list[Message]) -> DataQuality:
    """数据质量检查，产出 Deterministic DataQuality。"""
    total = len(messages)

    confirmed = sum(1 for m in messages if normalize_sender(m.sender) in ("self", "other"))
    unknown = total - confirmed
    analyzable = sum(
        1 for m in messages if m.type == "text" and (m.content or "").strip()
    )

    epochs = [to_epoch(m.timestamp) for m in messages]

    # 时间顺序异常：原始顺序中相邻两条时间倒退
    order_anomalies = 0
    for i in range(1, len(epochs)):
        if epochs[i - 1] is not None and epochs[i] is not None and epochs[i] < epochs[i - 1]:
            order_anomalies += 1

    # 时间跨度
    valid_epochs = sorted(e for e in epochs if e is not None)
    time_span = None
    if valid_epochs:
        time_span = f"{_format_epoch(valid_epochs[0])} ~ {_format_epoch(valid_epochs[-1])}"

    # 重复消息风险
    pair_counts = Counter((m.id, m.content) for m in messages)
    exact_dups = sum(1 for c in pair_counts.values() if c > 1)
    id_dups = len(messages) - len({m.id for m in messages})
    if exact_dups > 0:
        dup_risk = "high"
    elif id_dups > 0:
        dup_risk = "medium"
    else:
        dup_risk = "low"

    # 是否可能来自部分导出（启发式）
    gaps = [b - a for a, b in zip(valid_epochs, valid_epochs[1:])]
    big_gap = any(g > BIG_GAP_SECONDS for g in gaps)
    partial_export_possible = (total < MIN_MESSAGES_FOR_INITIATION) or big_gap

    limitations: list[str] = []
    if order_anomalies > 0:
        limitations.append("消息时间戳存在乱序，时间间隔统计已按时间排序后计算。")
    if dup_risk in ("high", "medium"):
        limitations.append("存在重复消息或重复 ID，可能来自重复导出。")
    if partial_export_possible:
        limitations.append("样本疑似不完整或有较大时间空洞，结论适用范围有限。")
    if total == 0:
        limitations.append("无任何可分析消息。")

    coverage = (
        f"共 {total} 条消息；已确认发送者 {confirmed}/{total}（{_ratio(confirmed, total)}）；"
        f"未知发送者 {unknown}/{total}（{_ratio(unknown, total)}）；"
        f"可分析文本 {analyzable}/{total}（{_ratio(analyzable, total)}）。"
    )

    # 聚合日志，避免写入聊天正文
    logger.info(
        "data_quality total=%d confirmed=%d unknown=%d analyzable=%d anomalies=%d dup_risk=%s",
        total, confirmed, unknown, analyzable, order_anomalies, dup_risk,
    )

    return DataQuality(
        total_messages=total,
        confirmed_sender_ratio=_ratio(confirmed, total),
        unknown_sender_ratio=_ratio(unknown, total),
        time_span=time_span,
        analyzable_text_ratio=_ratio(analyzable, total),
        time_order_anomalies=order_anomalies,
        duplicate_message_risk=dup_risk,
        partial_export_possible=partial_export_possible,
        coverage=coverage,
        limitations=limitations,
    )


def compute_statistics(messages: list[Message]) -> Statistics:
    """确定性客观统计。"""
    total = len(messages)
    msg_by: dict[str, list[Message]] = {"self": [], "other": [], "unknown": []}
    for m in messages:
        msg_by[normalize_sender(m.sender)].append(m)

    def _stats(msgs: list[Message]) -> SenderStats:
        return SenderStats(
            message_count=len(msgs),
            message_ratio=_ratio(len(msgs), total),
            char_count=sum(len(m.content or "") for m in msgs),
        )

    # 对话轮次与连续发送
    runs: list[list] = []  # [sender, count]
    for m in messages:
        s = normalize_sender(m.sender)
        if runs and runs[-1][0] == s:
            runs[-1][1] += 1
        else:
            runs.append([s, 1])
    conversation_turns = len(runs) if runs else None
    consecutive_runs = sum(1 for _, c in runs if c >= 2)

    # 时间间隔（按时间排序后计算）
    epochs = [to_epoch(m.timestamp) for m in messages]
    valid_epochs = sorted(e for e in epochs if e is not None)
    intervals = [b - a for a, b in zip(valid_epochs, valid_epochs[1:]) if b >= a]

    messages_per_day: Optional[float] = None
    if len(valid_epochs) >= 2:
        span_days = (valid_epochs[-1] - valid_epochs[0]) / 86400
        if span_days > 0:
            messages_per_day = total / span_days

    avg_interval = _mean(intervals)
    median_interval = _statistics.median(intervals) if intervals else None

    # 主动开启比例：只在会话边界足够可靠时计算
    self_initiation_ratio, initiation_note = _compute_initiation(
        messages, valid_epochs, conversation_turns
    )

    logger.info(
        "stats total=%d turns=%s consecutive_runs=%d self_init=%s",
        total, conversation_turns, consecutive_runs,
        self_initiation_ratio if self_initiation_ratio is not None else "insufficient",
    )

    return Statistics(
        self_stats=_stats(msg_by["self"]),
        other_stats=_stats(msg_by["other"]),
        unknown_stats=_stats(msg_by["unknown"]),
        messages_per_day=round(messages_per_day, 3) if messages_per_day is not None else None,
        avg_interval_seconds=round(avg_interval, 1) if avg_interval is not None else None,
        median_interval_seconds=round(median_interval, 1) if median_interval is not None else None,
        consecutive_message_runs=consecutive_runs,
        conversation_turns=conversation_turns,
        self_initiation_ratio=self_initiation_ratio,
        initiation_note=initiation_note,
    )


def _compute_initiation(
    messages: list[Message],
    valid_epochs: list[float],
    conversation_turns: Optional[int],
) -> tuple[Optional[float], str]:
    """计算「主动开启聊天」比例。

    规则：
    - 消息过少或会话边界不可靠时返回 (None, 说明)，即数据不足；
    - 只用时间间隔切分会话，不假设「每天第一条」。
    """
    total = len(messages)
    if total < MIN_MESSAGES_FOR_INITIATION:
        return None, f"消息数不足 {MIN_MESSAGES_FOR_INITIATION} 条，主动开启比例无法可靠计算。"

    # 按时间排序后切分会话
    indexed = sorted(
        [(to_epoch(m.timestamp), normalize_sender(m.sender)) for m in messages],
        key=lambda x: x[0] if x[0] is not None else -1,
    )
    sessions: list[list[tuple[Optional[float], str]]] = []
    for item in indexed:
        if item[0] is None:
            continue
        if not sessions or (item[0] - sessions[-1][-1][0] > SESSION_GAP_SECONDS):
            sessions.append([item])
        else:
            sessions[-1].append(item)

    reliable_sessions = [s for s in sessions if len(s) >= 1]
    if len(reliable_sessions) < 2:
        return None, "可识别的独立会话少于 2 段，主动开启比例视为数据不足。"

    known_initiated = 0
    initiated_by_self = 0
    for session in reliable_sessions:
        first_sender = session[0][1]
        if first_sender == "unknown":
            # 首个发送者未知则不计入任一方（分子分母都排除）
            continue
        known_initiated += 1
        if first_sender == "self":
            initiated_by_self += 1

    if known_initiated == 0:
        return None, "所有会话起始发送者均未知，主动开启比例无法计算。"

    ratio = initiated_by_self / known_initiated
    note = (
        f"基于 {SESSION_GAP_SECONDS // 3600} 小时以上时间间隔切分出 {known_initiated} 段会话。"
        "该比例为娱乐化参考，不等于真实主动性。"
    )
    return round(ratio, 3), note


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _mean(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)