"""报告字段转换：把内部分析报告整理成前端易用的图表结构。"""
from __future__ import annotations

from typing import Any, Optional

from api.schemas import PortraitDimension, PortraitGroup

# 中文维度名 → 前端使用的英文 key
DIMENSION_KEYS = {
    "话题主动性": ("topic_initiative", "话题主动性"),
    "对话延续程度": ("conversation_continuity", "对话延续程度"),
    "个人生活分享": ("personal_sharing", "个人生活分享"),
    "情绪表达程度": ("emotion_expression", "情绪表达程度"),
    "关心与回应程度": ("care_and_responsiveness", "关心与回应程度"),
    "邀约与线下互动": ("invitation_and_offline", "邀约与线下互动"),
    "关系边界表达": ("boundary_expression", "关系边界表达"),
}

# 等级 → 0~100 的展示分（仅用于图表，不代表任何概率）
LEVEL_SCORES = {"高": 80, "中": 55, "低": 30, "数据不足": None}


def _score(level: str) -> Optional[int]:
    return LEVEL_SCORES.get(level, 55)


def _profile_to_dimensions(profile: Optional[dict[str, Any]]) -> list[PortraitDimension]:
    if not profile:
        return []
    dimensions: list[PortraitDimension] = []
    for label, (key, cn_label) in DIMENSION_KEYS.items():
        raw = profile.get(label)
        if not isinstance(raw, dict):
            continue
        level = str(raw.get("level") or "数据不足")
        dimensions.append(
            PortraitDimension(
                key=key,
                label=cn_label,
                level=level,
                score=_score(level),
                detail=str(raw.get("detail") or ""),
                evidence_ids=[str(i) for i in (raw.get("evidence_ids") or [])],
                confidence=str(raw.get("confidence") or "low"),
            )
        )
    return dimensions


def build_portraits(report: dict[str, Any]) -> PortraitGroup:
    return PortraitGroup(
        self_portrait=_profile_to_dimensions(report.get("self_profile")),
        other_portrait=_profile_to_dimensions(report.get("other_profile")),
    )
