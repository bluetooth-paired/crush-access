"""编排服务测试（用 FakeAnalyzer 替代真实 LLM）。"""

import pytest

from analysis.analyzer import AnalysisModelError, QualitativeAnalysis
from analysis.schema import (
    Advisor,
    InteractionPattern,
    Message,
    Profile,
    ProfileDimension,
    RelationshipAssessment,
    Signal,
)
from analysis.service import (
    AnalysisService,
    ConversationValidationError,
    analyze_conversation,
)


def msg(id, sender, ts, content="hi"):
    return Message(id=id, timestamp=ts, sender=sender, type="text", content=content)


def make_qa(evidence="m001"):
    dim = ProfileDimension(level="中", detail="依据", evidence_ids=[evidence], confidence="medium")
    return QualitativeAnalysis(
        self_profile=Profile(话题主动性=dim),
        other_profile=Profile(话题主动性=ProfileDimension(evidence_ids=[evidence])),
        signals=[Signal(category="positive", name="主动", description="d", evidence_ids=[evidence])],
        interaction_patterns=[InteractionPattern(event_id="e1", category="邀请见面", message_ids=[evidence])],
        relationship_assessment=RelationshipAssessment(stage="友好互动期"),
        advisor=Advisor(relationship_summary="s"),
    )


class FakeAnalyzer:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def analyze(self, messages, data_quality, statistics, ctx=None, user_profile=None):
        self.calls.append((messages, data_quality, statistics, ctx))
        if self.error is not None:
            raise self.error
        return self.result


def test_empty_conversation_raises():
    with pytest.raises(ConversationValidationError) as e:
        analyze_conversation({"schema_version": "1.0", "messages": []}, )
    assert e.value.code == "EMPTY_CONVERSATION"


def test_missing_conversation_raises():
    with pytest.raises(ConversationValidationError) as e:
        analyze_conversation(None)
    assert e.value.code == "INVALID_CONVERSATION"


def test_non_dict_conversation_raises():
    with pytest.raises(ConversationValidationError) as e:
        analyze_conversation("not an object")
    assert e.value.code == "INVALID_CONVERSATION"


def test_unsupported_schema_version_raises():
    with pytest.raises(ConversationValidationError) as e:
        analyze_conversation(
            {
                "schema_version": "2.0",
                "messages": [{"id": "m1", "timestamp": "2026-11-07T10:30+08:00", "sender": "self"}],
            }
        )
    assert e.value.code == "UNSUPPORTED_SCHEMA_VERSION"


def test_invalid_message_shape_raises():
    # 缺 id，无法回溯证据
    with pytest.raises(ConversationValidationError) as e:
        analyze_conversation(
            {
                "schema_version": "1.0",
                "messages": [{"timestamp": "2026-11-07T10:30+08:00", "sender": "self", "content": "x"}],
            }
        )
    assert e.value.code == "INVALID_CONVERSATION"


def test_evidence_id_not_exist_is_dropped():
    fake = FakeAnalyzer(result=make_qa(evidence="ghost_id"))
    service = AnalysisService(analyzer=fake)
    conv = {
        "schema_version": "1.0",
        "messages": [
            {"id": "m001", "timestamp": "2026-11-07T10:30+08:00", "sender": "self", "content": "a"},
            {"id": "m002", "timestamp": "2026-11-07T10:31+08:00", "sender": "other", "content": "b"},
        ],
    }
    report = service.analyze(conv)
    # 不存在的证据 ID 被剔除
    assert report.signals[0].evidence_ids == []
    assert report.interaction_patterns[0].message_ids == []
    assert any("证据 ID" in x for x in report.limitations)


def test_model_error_returns_failed_report():
    fake = FakeAnalyzer(error=AnalysisModelError("boom"))
    service = AnalysisService(analyzer=fake)
    conv = {
        "schema_version": "1.0",
        "messages": [
            {"id": "m001", "timestamp": "2026-11-07T10:30+08:00", "sender": "self", "content": "a"},
            {"id": "m002", "timestamp": "2026-11-07T10:31+08:00", "sender": "other", "content": "b"},
        ],
    }
    report = service.analyze(conv)
    assert report.status == "failed"
    assert any(e.code == "MODEL_ERROR" for e in report.errors)


def test_all_unknown_profiles_null_and_partial():
    fake = FakeAnalyzer(result=make_qa(evidence="m001"))
    service = AnalysisService(analyzer=fake)
    conv = {
        "schema_version": "1.0",
        "messages": [
            {"id": "m001", "timestamp": "2026-11-07T10:30+08:00", "sender": "unknown", "content": "a"},
        ],
    }
    report = service.analyze(conv)
    assert report.self_profile is None
    assert report.other_profile is None
    assert report.status == "partial"


def test_include_advice_false():
    fake = FakeAnalyzer(result=make_qa())
    service = AnalysisService(analyzer=fake)
    conv = {
        "schema_version": "1.0",
        "messages": [
            {"id": "m001", "timestamp": "2026-11-07T10:30+08:00", "sender": "self", "content": "a"},
            {"id": "m002", "timestamp": "2026-11-07T10:31+08:00", "sender": "other", "content": "b"},
        ],
    }
    report = service.analyze(conv, include_advice=False)
    assert report.advisor is None


def test_end_to_end_with_fake_analyzer():
    fake = FakeAnalyzer(result=make_qa())
    service = AnalysisService(analyzer=fake)
    report = service.analyze(
        {
            "schema_version": "1.0",
            "messages": [
                {"id": "m001", "timestamp": "2026-11-07T10:30+08:00", "sender": "self", "content": "a"},
                {"id": "m002", "timestamp": "2026-11-07T10:31+08:00", "sender": "other", "content": "b"},
            ],
        }
    )
    assert report.analysis_version == "1.0"
    assert report.data_quality.total_messages == 2
    assert report.status == "completed"
    assert report.self_profile is not None
    assert report.other_profile is not None