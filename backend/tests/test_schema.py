"""输入/输出 Schema 校验与序列化测试。"""

from analysis.schema import (
    AnalysisReport,
    Conversation,
    Message,
    Profile,
    ProfileDimension,
    Statistics,
)


def test_conversation_parse_valid():
    conv = Conversation.model_validate(
        {
            "schema_version": "1.0",
            "source": "wechat-cli",
            "chat_type": "private",
            "messages": [
                {
                    "id": "m001",
                    "timestamp": "2026-11-07T10:30+08:00",
                    "sender": "self",
                    "type": "text",
                    "content": "在吗",
                }
            ],
            "metadata": {"total_messages": 1},
        }
    )
    assert conv.messages[0].id == "m001"


def test_conversation_forward_compatible_extra_fields():
    # 导入器未来新增字段不应导致解析失败
    conv = Conversation.model_validate(
        {
            "schema_version": "1.0",
            "messages": [{"id": "m1", "timestamp": "2026-11-07T10:30+08:00", "sender": "self", "future_field": 1}],
            "future_top": "x",
        }
    )
    assert conv.messages[0].id == "m1"


def test_message_type_allows_unknown():
    m = Message(id="m1", timestamp="2026-11-07T10:30+08:00", sender="other", type="link_or_file", content="")
    assert m.type == "link_or_file"


def test_profile_dimension_defaults():
    d = ProfileDimension()
    assert d.level == "数据不足"
    assert d.confidence == "low"
    assert d.evidence_ids == []


def test_profile_has_seven_dimensions():
    p = Profile()
    for key in ["话题主动性", "对话延续程度", "个人生活分享", "情绪表达程度", "关心与回应程度", "邀约与线下互动", "关系边界表达"]:
        assert getattr(p, key) is not None


def test_statistics_alias_dump():
    st = Statistics()
    data = st.model_dump(by_alias=True)
    assert "self" in data
    assert "other" in data
    assert "unknown" in data


def test_analysis_report_defaults():
    report = AnalysisReport()
    assert report.analysis_version == "1.0"
    assert report.status == "completed"
    assert report.signals == []
    assert report.interaction_patterns == []