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


def _load_llm(ctx=None) -> ChatOpenAI:
    workspace = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    with open(os.path.join(workspace, CONFIG_PATH), "r", encoding="utf-8") as f:
        cfg = json.load(f)

    model_cfg = cfg.get("config", {})
    from coze_coding_utils.runtime_ctx.context import default_headers

    return ChatOpenAI(
        model=model_cfg.get("model", "doubao-seed-2-0-lite-260215"),
        api_key=os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY"),
        base_url=os.getenv("COZE_INTEGRATION_MODEL_BASE_URL"),
        temperature=model_cfg.get("temperature", 0.7),
        # 必须显式开启 streaming：本环境 openai(2.24.0) 在非流式
        # with_raw_response.parse() 路径会把响应解析成 str，而 langchain_openai
        # 的 _create_chat_result 会对其调用 .model_dump()，导致
        # "'str' object has no attribute 'model_dump'"。
        # streaming=True 时 invoke() 走 _stream -> client.create()，绕开该路径。
        streaming=True,
        timeout=model_cfg.get("timeout", 600),
        extra_body={"thinking": {"type": model_cfg.get("thinking", "disabled")}},
        default_headers=default_headers(ctx) if ctx else {},
    )


class LLMAnalyzer:
    """定性分析器（可注入 mock llm 以便测试）。"""

    def __init__(self, llm: Optional[ChatOpenAI] = None, max_retries: int = DEFAULT_MAX_RETRIES):
        self._injected_llm = llm
        self.max_retries = max_retries

    def _get_llm(self, ctx=None) -> ChatOpenAI:
        if self._injected_llm is not None:
            return self._injected_llm
        return _load_llm(ctx)

    def analyze(
        self,
        messages: list[Message],
        data_quality: DataQuality,
        statistics: Statistics,
        ctx=None,
    ) -> QualitativeAnalysis:
        """调用模型得到定性分析，带非法 JSON 容错与超时重试。"""
        llm = self._get_llm(ctx)
        user_prompt = build_user_prompt(messages, data_quality, statistics)
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
                    raise JSONParseError("模型输出无法解析为 JSON")

                try:
                    result = QualitativeAnalysis.model_validate(data)
                except ValidationError as ve:
                    raise JSONParseError(f"模型输出字段不符合要求: {ve}") from ve

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
                # 追加纠错提示后重试
                payload.append(
                    HumanMessage(
                        content=(
                            "上一次输出不符合要求，请严格只输出一个合法 JSON 对象（不要 Markdown 围栏、"
                            f"不要额外文字）。错误信息：{e}"
                        )
                    )
                )

        raise AnalysisModelError(
            f"模型分析在 {self.max_retries} 次尝试后仍失败，最后错误：{last_error}"
        )