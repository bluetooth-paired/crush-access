"""LLM 分析器：负责定性分析，含非法 JSON 容错与超时重试。

确定性统计绝不在这里计算；本模块只把「聊天记录 + 客观统计」交给模型，
拿回观点性 JSON，并对返回结果做解析与校验。
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from analysis.prompts import SYSTEM_PROMPT, build_user_prompt
from analysis.schema import (
    Advisor,
    DataQuality,
    InteractionPattern,
    Message,
    MessageFlag,
    Profile,
    RelationshipAssessment,
    Signal,
    Statistics,
)

logger = logging.getLogger(__name__)

CONFIG_PATH = "config/agent_llm_config.json"
DEFAULT_MAX_RETRIES = 3


class JSONParseError(ValueError):
    """模型输出无法解析为合法 JSON 时抛出。"""


class AnalysisModelError(RuntimeError):
    """模型在多次重试后仍失败时抛出。"""


class QualitativeAnalysis(BaseModel):
    """模型需要返回的定性分析部分。"""

    model_config = ConfigDict(extra="allow")

    self_profile: Optional[Profile] = None
    other_profile: Optional[Profile] = None
    interaction_patterns: list[InteractionPattern] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    relationship_assessment: Optional[RelationshipAssessment] = None
    advisor: Optional[Advisor] = None
    limitations: list[str] = Field(default_factory=list)
    message_flags: list[MessageFlag] = Field(default_factory=list)


def extract_json(text: Any) -> Optional[dict]:
    """从模型输出中稳健地提取 JSON 对象。

    兼容：纯 JSON、```json 代码块、JSON 前后夹带说明文字等情况。
    """
    if isinstance(text, dict):
        return text
    if isinstance(text, list):
        # 取拼接后的文本再尝试
        parts = [t for t in text if isinstance(t, str)]
        text = "\n".join(parts)
    if not isinstance(text, str):
        return None

    s = text.strip()
    if not s:
        return None

    # 1. 直接解析
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. 去掉代码块围栏
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", s, re.DOTALL)
    if fence:
        try:
            obj = json.loads(fence.group(1))
            return obj if isinstance(obj, dict) else None
        except (json.JSONDecodeError, TypeError):
            pass

    # 3. 截取第一个 { 到最后一个 }
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(s[start:end + 1])
            return obj if isinstance(obj, dict) else None
        except (json.JSONDecodeError, TypeError):
            pass

    return None


_LEVELS = {"高", "中", "低", "数据不足"}


def _normalize_level(value: Any) -> str:
    text = str(value or "").strip()
    if text in _LEVELS:
        return text
    lowered = text.lower()
    if any(k in text for k in ("不足", "未知", "无法判断")) or "unknown" in lowered or "insufficient" in lowered:
        return "数据不足"
    if "高" in text or "strong" in lowered or "high" in lowered:
        return "高"
    if "低" in text or "弱" in text or "weak" in lowered or "low" in lowered:
        return "低"
    if "中" in text or "medium" in lowered or "moderate" in lowered:
        return "中"
    return "数据不足"


def _normalize_category(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "pos" in text or "积极" in text or "正面" in text:
        return "positive"
    if "neg" in text or "消极" in text or "负面" in text:
        return "negative"
    if "ambig" in text or "模糊" in text or "暧昧" in text:
        return "ambiguous"
    return "neutral"


def _normalize_strength(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "strong" in text or "强" in text:
        return "strong"
    if "weak" in text or "弱" in text:
        return "weak"
    return "medium"


def _normalize_confidence(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "high" in text or "高" in text:
        return "high"
    if "low" in text or "低" in text:
        return "low"
    return "medium"


def _normalize_profile(profile: Any) -> Any:
    if not isinstance(profile, dict):
        return profile
    normalized = {}
    for key, value in profile.items():
        if isinstance(value, str):
            normalized[key] = {"level": _normalize_level(value)}
        elif isinstance(value, dict):
            item = dict(value)
            item["level"] = _normalize_level(item.get("level"))
            ids = item.get("evidence_ids")
            if not isinstance(ids, list):
                item["evidence_ids"] = []
            normalized[key] = item
        else:
            normalized[key] = value
    return normalized


def _loosen_payload(data: Any) -> Any:
    """把模型常见的「近义表述」收敛到 schema 允许的枚举值。

    只做无损归一（如「较高」→「高」），不编造任何聊天事实；
    结构上不可用的条目直接丢弃，避免一条脏数据拖垮整次分析。
    """
    if not isinstance(data, dict):
        return data
    payload = dict(data)

    payload["self_profile"] = _normalize_profile(payload.get("self_profile"))
    payload["other_profile"] = _normalize_profile(payload.get("other_profile"))

    signals = []
    raw_signals = payload.get("signals")
    if isinstance(raw_signals, list):
        for item in raw_signals:
            if not isinstance(item, dict) or not str(item.get("name") or "").strip():
                continue
            signal = dict(item)
            signal["category"] = _normalize_category(signal.get("category"))
            signal["evidence_strength"] = _normalize_strength(signal.get("evidence_strength"))
            ids = signal.get("evidence_ids")
            signal["evidence_ids"] = [str(i) for i in ids] if isinstance(ids, list) else []
            signals.append(signal)
        payload["signals"] = signals

    patterns = []
    raw_patterns = payload.get("interaction_patterns")
    if isinstance(raw_patterns, list):
        for index, item in enumerate(raw_patterns):
            if not isinstance(item, dict):
                continue
            pattern = dict(item)
            pattern.setdefault("event_id", f"auto-{index + 1}")
            pattern["category"] = str(pattern.get("category") or "other")
            pattern["certainty"] = _normalize_confidence(pattern.get("certainty"))
            ids = pattern.get("message_ids")
            pattern["message_ids"] = [str(i) for i in ids] if isinstance(ids, list) else []
            patterns.append(pattern)
        payload["interaction_patterns"] = patterns

    flags = []
    raw_flags = payload.get("message_flags")
    if isinstance(raw_flags, list):
        for item in raw_flags:
            if not isinstance(item, dict) or not str(item.get("id") or "").strip():
                continue
            flags.append(item)
        payload["message_flags"] = flags

    assessment = payload.get("relationship_assessment")
    if isinstance(assessment, dict):
        assessment = dict(assessment)
        assessment["confidence"] = _normalize_confidence(assessment.get("confidence"))
        payload["relationship_assessment"] = assessment

    return payload


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    return str(content)


def _load_llm(ctx=None, thinking_level: Optional[str] = None) -> ChatOpenAI:
    """按环境变量解析模型配置（DeepSeek / Kimi / 自定义 OpenAI 兼容端点 / 平台网关）。"""
    from llm.provider import build_chat_model

    return build_chat_model(
        ctx=ctx, streaming=True, thinking_level=thinking_level, json_mode=True
    )


class LLMAnalyzer:
    """定性分析器（可注入 mock llm 以便测试）。"""

    def __init__(self, llm: Optional[ChatOpenAI] = None, max_retries: int = DEFAULT_MAX_RETRIES):
        self._injected_llm = llm
        self.max_retries = max_retries

    def _get_llm(self, ctx=None, thinking_level: Optional[str] = None) -> ChatOpenAI:
        if self._injected_llm is not None:
            return self._injected_llm
        return _load_llm(ctx, thinking_level)

    def analyze(
        self,
        messages: list[Message],
        data_quality: DataQuality,
        statistics: Statistics,
        ctx=None,
        user_profile: Optional[dict] = None,
        thinking_level: Optional[str] = None,
    ) -> QualitativeAnalysis:
        """调用模型得到定性分析，带非法 JSON 容错与超时重试。"""
        llm = self._get_llm(ctx, thinking_level)
        user_prompt = build_user_prompt(messages, data_quality, statistics, user_profile)
        payload = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = llm.invoke(payload)
                text = _content_to_text(resp.content)
                data = extract_json(text)
                if data is None:
                    # 只记录结构特征，绝不记录模型原文（可能包含聊天隐私）
                    logger.warning(
                        "llm_analyze_invalid_output attempt=%d output_len=%d has_brace=%s",
                        attempt + 1, len(text or ""), "{" in (text or ""),
                    )
                    raise JSONParseError("模型输出无法解析为 JSON")

                try:
                    result = QualitativeAnalysis.model_validate(_loosen_payload(data))
                except ValidationError as ve:
                    # 只记录字段路径，避免把模型输出中的聊天内容写进日志/错误信息
                    fields = ",".join(
                        ".".join(str(part) for part in err.get("loc") or [])[:60]
                        for err in ve.errors()[:5]
                    )
                    logger.warning(
                        "llm_analyze_schema_mismatch attempt=%d fields=%s",
                        attempt + 1, fields or "unknown",
                    )
                    raise JSONParseError("模型输出字段不符合要求") from ve

                logger.info(
                    "llm_analyze_ok attempt=%d signals=%d patterns=%d",
                    attempt + 1, len(result.signals), len(result.interaction_patterns),
                )
                return result

            except Exception as e:  # noqa: BLE001 - 捕获后重试，最终统一抛出结构化错误
                last_error = e
                logger.warning(
                    "llm_analyze_retry attempt=%d/%d error=%s",
                    attempt + 1, self.max_retries, type(e).__name__,
                )
                # 追加纠错提示后重试（只回传字段级错误，不回传模型原文）
                payload.append(
                    HumanMessage(
                        content=(
                            "上一次输出不符合要求，请严格只输出一个合法 JSON 对象（不要 Markdown 围栏、"
                            "不要额外文字），并确保所有枚举字段使用约定取值。"
                        )
                    )
                )

        raise AnalysisModelError(
            f"模型分析在 {self.max_retries} 次尝试后仍失败（最后错误类型：{type(last_error).__name__}）"
        )