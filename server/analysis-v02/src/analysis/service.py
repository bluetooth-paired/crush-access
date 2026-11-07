"""编排服务：确定性前处理 + LLM 定性分析，合并为 analysis-report/1.0。

职责：
- 输入校验（Schema 1.0），不合法时抛出结构化 ConversationValidationError；
- 确定性统计（数据质量 + 客观统计）；
- 调用 LLM 得到定性部分；
- 合并结果、校验证据 ID、处理数据不足、统一输出。
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Union

from pydantic import ValidationError

from analysis.analyzer import AnalysisModelError, LLMAnalyzer
from analysis.preprocessor import assess_data_quality, compute_statistics
from analysis.schema import (
    AnalysisReport,
    Conversation,
    DataQuality,
    ErrorInfo,
    InteractionPattern,
    Message,
    Profile,
    Signal,
    Statistics,
)

logger = logging.getLogger(__name__)

PROFILE_DIMENSIONS = [
    "话题主动性",
    "对话延续程度",
    "个人生活分享",
    "情绪表达程度",
    "关心与回应程度",
    "邀约与线下互动",
    "关系边界表达",
]


class ConversationValidationError(Exception):
    """输入会话不合法时抛出，由 API 层转为 HTTP 400。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _coerce_conversation(conversation: Any) -> Conversation:
    if conversation is None:
        raise ConversationValidationError("INVALID_CONVERSATION", "缺少 conversation 字段。")

    if isinstance(conversation, Conversation):
        conv = conversation
    elif isinstance(conversation, dict):
        try:
            conv = Conversation.model_validate(conversation)
        except ValidationError as e:
            raise ConversationValidationError("INVALID_CONVERSATION", f"聊天记录格式不符合要求：{e}") from e
    else:
        raise ConversationValidationError("INVALID_CONVERSATION", "conversation 必须是 JSON 对象。")

    if conv.schema_version != "1.0":
        raise ConversationValidationError(
            "UNSUPPORTED_SCHEMA_VERSION",
            f"仅支持 schema_version 1.0，收到 {conv.schema_version}。",
        )
    if not conv.messages:
        raise ConversationValidationError("EMPTY_CONVERSATION", "聊天记录为空，无法分析。")

    return conv


def _clean_ids(ids: list[str], valid_ids: set[str]) -> tuple[list[str], int]:
    kept = [i for i in ids if i in valid_ids]
    return kept, len(ids) - len(kept)


def _clean_profile(profile: Optional[Profile], valid_ids: set[str]) -> tuple[Optional[Profile], int]:
    if profile is None:
        return None, 0
    dropped = 0
    for key in PROFILE_DIMENSIONS:
        dim = getattr(profile, key, None)
        if dim is None:
            continue
        dim.evidence_ids, d = _clean_ids(dim.evidence_ids, valid_ids)
        dropped += d
    return profile, dropped


def _clean_signals(signals: list[Signal], valid_ids: set[str]) -> tuple[list[Signal], int]:
    dropped = 0
    for s in signals:
        s.evidence_ids, d = _clean_ids(s.evidence_ids, valid_ids)
        dropped += d
    return signals, dropped


def _clean_patterns(patterns: list[InteractionPattern], valid_ids: set[str]) -> tuple[list[InteractionPattern], int]:
    dropped = 0
    for p in patterns:
        p.message_ids, d = _clean_ids(p.message_ids, valid_ids)
        dropped += d
    return patterns, dropped


class AnalysisService:
    """分析服务。可注入 mock analyzer 以便测试。"""

    def __init__(self, analyzer: Optional[LLMAnalyzer] = None):
        self.analyzer = analyzer or LLMAnalyzer()

    def analyze(
        self,
        conversation: Union[dict, Conversation],
        ctx=None,
        include_advice: bool = True,
    ) -> AnalysisReport:
        conv = _coerce_conversation(conversation)
        messages = conv.messages
        valid_ids = {m.id for m in messages}

        data_quality = assess_data_quality(messages)
        statistics = compute_statistics(messages)

        report = AnalysisReport(
            data_quality=data_quality,
            statistics=statistics,
        )
        report.limitations = list(data_quality.limitations)

        # 调用 LLM 定性分析
        try:
            qa = self.analyzer.analyze(messages, data_quality, statistics, ctx)
        except AnalysisModelError as e:
            logger.error("analysis model error: %s", e)
            report.status = "failed"
            report.errors.append(ErrorInfo(code="MODEL_ERROR", message=str(e)))
            return report

        # 合并定性结果
        report.self_profile = qa.self_profile
        report.other_profile = qa.other_profile
        report.interaction_patterns = qa.interaction_patterns
        report.signals = qa.signals
        report.relationship_assessment = qa.relationship_assessment
        report.advisor = qa.advisor if include_advice else None

        # 证据 ID 校验：剔除不存在的 ID
        dropped = 0
        report.self_profile, d1 = _clean_profile(report.self_profile, valid_ids)
        report.other_profile, d2 = _clean_profile(report.other_profile, valid_ids)
        report.signals, d3 = _clean_signals(report.signals, valid_ids)
        report.interaction_patterns, d4 = _clean_patterns(report.interaction_patterns, valid_ids)
        dropped = d1 + d2 + d3 + d4
        if dropped > 0:
            report.limitations.append(f"模型生成了 {dropped} 个无法回溯到原始消息的证据 ID，已剔除。")

        # 数据不足守卫：某一方完全无消息时，不保留其画像（避免由 unknown 擅自归属）
        if statistics.self_stats.message_count == 0:
            report.self_profile = None
            report.limitations.append("无法识别「用户本人」的消息，self_profile 置空。")
        if statistics.other_stats.message_count == 0:
            report.other_profile = None
            report.limitations.append("无法识别「对方(TA)」的消息，other_profile 置空。")

        # 合并 LLM 补充的信息缺口
        for item in qa.limitations or []:
            if item not in report.limitations:
                report.limitations.append(item)

        # 状态判定
        has_data_gap = (
            report.self_profile is None
            or report.other_profile is None
            or data_quality.unknown_sender_ratio >= 1.0
            or statistics.self_stats.message_count == 0
            or statistics.other_stats.message_count == 0
        )
        report.status = "partial" if has_data_gap else "completed"

        logger.info(
            "analysis_report status=%s signals=%d patterns=%d dropped_ids=%d",
            report.status, len(report.signals), len(report.interaction_patterns), dropped,
        )
        return report


def analyze_conversation(
    conversation: Union[dict, Conversation],
    ctx=None,
    include_advice: bool = True,
) -> AnalysisReport:
    """模块级入口，供 API 与 Agent 复用。"""
    return AnalysisService().analyze(conversation, ctx=ctx, include_advice=include_advice)