"""LLM 分析器的 JSON 容错与重试测试（用 FakeLLM 替代真实模型）。"""

import types

import pytest

from analysis.analyzer import (
    AnalysisModelError,
    LLMAnalyzer,
    extract_json,
)
from analysis.schema import DataQuality, Message, Statistics


def make_resp(content):
    return types.SimpleNamespace(content=content)


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return make_resp(r)


def _ctx():
    return DataQuality(), Statistics(), [Message(id="m1", timestamp="2026-11-07T10:30+08:00", sender="self", content="a")]


# ---------------------------------------------------------------------------
# extract_json
# ---------------------------------------------------------------------------

def test_extract_json_pure():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_prose():
    assert extract_json('这是结果：{"a": 1} 结束') == {"a": 1}


def test_extract_json_dict_passthrough():
    assert extract_json({"a": 1}) == {"a": 1}


def test_extract_json_invalid():
    assert extract_json("not json at all") is None
    assert extract_json("") is None


# ---------------------------------------------------------------------------
# 重试与失败
# ---------------------------------------------------------------------------

def test_analyze_retries_on_invalid_json_then_succeeds():
    fake = FakeLLM(["this is not json", '{"signals": []}'])
    dq, st, msgs = _ctx()
    result = LLMAnalyzer(llm=fake, max_retries=3).analyze(msgs, dq, st)
    assert result.signals == []
    assert len(fake.calls) == 2


def test_analyze_raises_after_retries():
    fake = FakeLLM([TimeoutError("slow"), TimeoutError("slow"), TimeoutError("slow")])
    dq, st, msgs = _ctx()
    with pytest.raises(AnalysisModelError):
        LLMAnalyzer(llm=fake, max_retries=3).analyze(msgs, dq, st)
    assert len(fake.calls) == 3


def test_analyze_rejects_invalid_schema_shape():
    # 返回合法 JSON 但字段类型不对（signals 应为数组）
    fake = FakeLLM(['{"signals": "not-an-array"}'])
    dq, st, msgs = _ctx()
    # 会触发 ValidationError -> JSONParseError -> 重试 -> 最终失败
    with pytest.raises(AnalysisModelError):
        LLMAnalyzer(llm=fake, max_retries=2).analyze(msgs, dq, st)


# ---------------------------------------------------------------------------
# 回归：LLM 构造必须显式开启 streaming
# ---------------------------------------------------------------------------

def test_load_llm_enables_streaming():
    """回归：_load_llm 必须显式 streaming=True。

    否则 invoke() 会走 langchain_openai 非流式 _create_chat_result 路径，
    在当前 openai 版本下对 str 响应调用 .model_dump() 会抛
    "'str' object has no attribute 'model_dump'"。
    """
    from analysis.analyzer import _load_llm

    llm = _load_llm()
    assert getattr(llm, "streaming") is True
    # 必须显式出现在 model_fields_set，_should_stream 才会据此路由到 _stream
    assert "streaming" in llm.model_fields_set