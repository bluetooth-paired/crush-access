"""API 请求 / 响应模型（同时用于 OpenAPI 文档与运行时校验）。"""
from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from analysis.schema import (
    Advisor,
    AnalysisReport,
    DailyPoint,
    DataQuality,
    InteractionPattern,
    Profile,
    RelationshipAssessment,
    Signal,
    Statistics,
)

CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

# 思考强度：auto 表示沿用服务端默认配置
ThinkingLevel = Literal["auto", "low", "medium", "high"]


class AiConfigApplied(BaseModel):
    """本次请求的 AI 配置实际生效情况（不伪造未支持的开关）。"""

    thinking: dict[str, Any] = Field(
        default_factory=dict,
        description="思考强度：requested / applied / supported / sent_parameters / note",
    )
    web_search: Optional[dict[str, Any]] = Field(
        default=None,
        description="联网搜索：requested / performed / results_count / query_used / note",
    )


class AnalyzeOptions(BaseModel):
    """分析选项。"""

    model_config = ConfigDict(extra="forbid")

    include_advice: bool = Field(default=True, description="是否生成军师建议（advisor 字段）")
    include_evidence: bool = Field(default=True, description="是否回传证据原文（evidence 字段）")
    thinking_level: ThinkingLevel = Field(
        default="auto",
        description="思考强度 auto/low/medium/high；仅在模型端点支持时生效，实际生效情况见响应 ai_config",
    )


class AnalyzeRequest(BaseModel):
    """API A 请求体。"""

    model_config = ConfigDict(extra="forbid")

    conversation: dict[str, Any] = Field(description="墨翊 chat.json Schema 1.0")
    profile: Optional[dict[str, Any]] = Field(
        default=None,
        description="可选人物档案（补充上下文，不能替代聊天证据）",
    )
    client_id: Optional[str] = Field(
        default=None,
        description="可选客户端标识（8-64 位字母数字_-）；不传则服务端生成并返回",
        examples=["auria-frontend-7f3a91"],
    )
    options: AnalyzeOptions = Field(default_factory=AnalyzeOptions)

    @field_validator("client_id")
    @classmethod
    def _check_client_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not CLIENT_ID_RE.match(value):
            raise ValueError("client_id 必须是 8-64 位字母、数字、下划线或短横线")
        return value


class MetricsSummary(BaseModel):
    """前端绘制图表所需的指标集合（与 analysis.schema.Metrics 对齐）。"""

    model_config = ConfigDict(extra="allow")

    message_counts: dict[str, int] = Field(default_factory=dict)
    participation_balance: Optional[float] = None
    other_question_ratio: Optional[float] = None
    shared_activity_ratio: Optional[float] = None
    positive_tone_ratio: Optional[float] = None
    interaction_index: float = 0.0
    interaction_index_components: list[dict[str, Any]] = Field(default_factory=list)
    formulas: list[dict[str, Any]] = Field(default_factory=list)
    semantic_detection: dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = ""


class PortraitDimension(BaseModel):
    """画像维度：同时提供中文标签与英文 key，方便前端画雷达图 / 进度条。"""

    key: str
    label: str
    level: str
    score: Optional[int] = Field(default=None, description="高=80 / 中=55 / 低=30 / 数据不足=null")
    detail: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: str = "low"


class PortraitGroup(BaseModel):
    self_portrait: list[PortraitDimension] = Field(default_factory=list)
    other_portrait: list[PortraitDimension] = Field(default_factory=list)


class AnalyzeMeta(BaseModel):
    analysis_id: str
    client_id: str
    created_at: str
    expires_at: str


class AnalyzeResponse(AnalyzeMeta):
    """API A 响应体：报告字段 + 生命周期元信息。"""

    model_config = ConfigDict(extra="allow")

    status: str = "completed"
    data_quality: DataQuality = Field(default_factory=DataQuality)
    statistics: Statistics = Field(default_factory=Statistics)
    metrics: MetricsSummary = Field(default_factory=MetricsSummary)
    daily_distribution: list[DailyPoint] = Field(default_factory=list)
    portraits: PortraitGroup = Field(default_factory=PortraitGroup)
    signals: list[Signal] = Field(default_factory=list)
    interaction_patterns: list[InteractionPattern] = Field(default_factory=list)
    relationship_assessment: Optional[RelationshipAssessment] = None
    advisor: Optional[Advisor] = None
    self_profile: Optional[Profile] = None
    other_profile: Optional[Profile] = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    ai_config: dict[str, Any] = Field(
        default_factory=dict, description="本次分析的 AI 配置生效情况（thinking）"
    )


class AdvisorChatRequest(BaseModel):
    """API B 请求体。"""

    model_config = ConfigDict(extra="forbid")

    analysis_id: str = Field(description="API A 返回的 analysis_id")
    message: str = Field(min_length=1, description="用户当前提问")
    session_id: Optional[str] = Field(default=None, description="会话 ID；不传则新建会话")
    client_id: Optional[str] = Field(default=None, description="与创建分析时一致的客户端标识")
    thinking_level: ThinkingLevel = Field(
        default="auto",
        description="思考强度 auto/low/medium/high；不支持时按服务端默认执行，见响应 ai_config",
    )
    web_search: bool = Field(
        default=False,
        description="是否开启联网搜索（默认关闭）；仅使用清洗后的用户提问作为搜索词，不上传聊天原文",
    )

    @field_validator("client_id")
    @classmethod
    def _check_client_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not CLIENT_ID_RE.match(value):
            raise ValueError("client_id 必须是 8-64 位字母、数字、下划线或短横线")
        return value

    @field_validator("message")
    @classmethod
    def _strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message 不能为空")
        return value


class AdvisorChatResponse(BaseModel):
    """API B 响应体。"""

    analysis_id: str
    session_id: str
    turn: int
    reply: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    boundary_notes: list[str] = Field(default_factory=list)
    ai_config: AiConfigApplied = Field(
        default_factory=AiConfigApplied, description="思考强度 / 联网搜索的实际生效情况"
    )


class HealthResponse(BaseModel):
    status: str
    version: str
    time: str
    store_backend: str
    model: dict[str, Any]
    features: dict[str, Any] = Field(
        default_factory=dict,
        description="本部署实际支持的 AI 能力（思考强度档位、联网搜索可用性等）",
    )
