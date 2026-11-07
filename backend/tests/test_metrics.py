"""确定性指标测试：公式、分母、边界与关键词兜底。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis.metrics import compute_daily_distribution, compute_metrics
from analysis.preprocessor import compute_statistics
from analysis.schema import Conversation, MessageFlag

FIXTURE = Path(__file__).parent / "fixtures" / "fictional_chat.json"


@pytest.fixture()
def conversation() -> Conversation:
    with FIXTURE.open("r", encoding="utf-8") as f:
        return Conversation.model_validate(json.load(f))


def _flags() -> list[MessageFlag]:
    """与 fixture 语义一致的人工标记（模拟 LLM 打标结果）。"""
    return [
        MessageFlag(id="m004", is_question=True),
        MessageFlag(id="m010", is_question=True),
        MessageFlag(id="m009", shared_activity=True),
        MessageFlag(id="m010", shared_activity=True),
        MessageFlag(id="m007", positive_tone=True),
        MessageFlag(id="m008", positive_tone=True),
        MessageFlag(id="m012", positive_tone=True),
    ]


def test_daily_distribution_groups_by_local_date(conversation: Conversation):
    points = compute_daily_distribution(conversation.messages)
    assert [p.date for p in points] == ["2026-11-06", "2026-11-07", "2026-11-08"]
    assert [(p.self_count, p.other_count, p.total) for p in points] == [
        (3, 3, 6),
        (2, 2, 4),
        (1, 1, 2),
    ]


def test_metrics_formulas_and_index(conversation: Conversation):
    statistics = compute_statistics(conversation.messages)
    metrics = compute_metrics(conversation.messages, statistics, _flags())

    assert metrics.message_counts.self_count == 6
    assert metrics.message_counts.other_count == 6
    assert metrics.message_counts.total == 12
    # 2*min(6,6)/(6+6) = 1.0
    assert metrics.participation_balance == 1.0
    # TA 提问 2 / TA 文本 6
    assert metrics.other_question_ratio == pytest.approx(0.3333, abs=1e-4)
    # 共同活动 2 / 全部文本 12
    assert metrics.shared_activity_ratio == pytest.approx(0.1667, abs=1e-4)
    # 积极语气 3 / 全部文本 12
    assert metrics.positive_tone_ratio == pytest.approx(0.25, abs=1e-4)
    # 加权：0.25*1 + 0.15*0.12 + 0.25*1 + 0.20*0.8333 + 0.15*0.25 = 0.7222
    assert metrics.interaction_index == pytest.approx(72.2, abs=0.1)
    assert metrics.semantic_detection.method == "llm"
    # 每个指标都必须给出公式与分母，前端要展示口径
    assert {f.key for f in metrics.formulas} >= {
        "message_counts",
        "participation_balance",
        "other_question_ratio",
        "shared_activity_ratio",
        "positive_tone_ratio",
        "interaction_index",
    }
    for formula in metrics.formulas:
        assert formula.formula and formula.denominator


def test_keyword_fallback_is_labelled(conversation: Conversation):
    statistics = compute_statistics(conversation.messages)
    metrics = compute_metrics(conversation.messages, statistics, flags=None)
    assert metrics.semantic_detection.method == "keyword_fallback"
    assert metrics.semantic_detection.flagged_message_count == 12
    assert metrics.other_question_ratio is not None


def test_unknown_sender_not_counted_in_balance(conversation: Conversation):
    data = conversation.model_dump()
    data["messages"] = data["messages"][:4]
    data["messages"][0]["sender"] = "unknown"
    conv = Conversation.model_validate(data)
    statistics = compute_statistics(conv.messages)
    metrics = compute_metrics(conv.messages, statistics, flags=None)
    # self=2, other=1 → 2*1/(2+1)
    assert metrics.participation_balance == pytest.approx(0.6667, abs=1e-4)
    assert metrics.message_counts.unknown_count == 1
