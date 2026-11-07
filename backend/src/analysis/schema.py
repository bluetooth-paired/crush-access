"""统一数据模型：输入 Schema 1.0 与输出 analysis-report/1.0。

设计原则：
- 输入模型（Conversation / Message）保持宽松（extra="allow"），向前兼容导入器字段；
- sender 的严格校验放到 preprocessor 中落地（非 self/other 一律归为 unknown，不擅自猜测归属）；
- 输出模型尽量结构化，避免前端直接依赖大模型临时生成的自然语言格式。
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# 输入：Schema 1.0（与现有导入器输出兼容）
# ---------------------------------------------------------------------------

class Message(BaseModel):
    """单条聊天消息。sender 仅 self / other / unknown；type 允许 unknown / link_or_file 等任意字符串。"""

    model_config = ConfigDict(extra="allow")

    id: str
    timestamp: str
    sender: str  # self / other / unknown，非法值由 preprocessor 归为 unknown
    type: str = "text"
    content: str = ""
    # 导入器可能带原始昵称；仅用于展示与证据卡片，绝不用于推断 sender 归属
    sender_name: Optional[str] = None

    @field_validator("content", mode="before")
    @classmethod
    def _null_content_as_empty(cls, value: Any) -> Any:
        """部分导出器的图片/链接消息 content 为 null，统一按空串处理（不改写文本本身）。"""
        return "" if value is None else value


class ConversationMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_messages: int = 0
    unknown_senders: int = 0
    anonymized: bool = False
    id_origin: str = ""
    timestamp_precision: str = "minute"


class Conversation(BaseModel):
    """导入器产出的完整 chat.json 结构。"""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    source: str = "wechat-cli"
    chat_type: str = "private"
    messages: list[Message] = Field(default_factory=list)
    metadata: ConversationMetadata = Field(default_factory=ConversationMetadata)


# ---------------------------------------------------------------------------
# 输出：analysis-report/1.0
# ---------------------------------------------------------------------------

Level = Literal["高", "中", "低", "数据不足"]
Confidence = Literal["high", "medium", "low"]


class ProfileDimension(BaseModel):
    """画像单个维度，保留 level / detail 字段以减少前端迁移成本。"""

    model_config = ConfigDict(extra="allow")

    level: Level = "数据不足"
    detail: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"


class Profile(BaseModel):
    """双向画像的 7 个维度（self 与 other 各一份）。"""

    model_config = ConfigDict(extra="allow")

    话题主动性: ProfileDimension = Field(default_factory=ProfileDimension)
    对话延续程度: ProfileDimension = Field(default_factory=ProfileDimension)
    个人生活分享: ProfileDimension = Field(default_factory=ProfileDimension)
    情绪表达程度: ProfileDimension = Field(default_factory=ProfileDimension)
    关心与回应程度: ProfileDimension = Field(default_factory=ProfileDimension)
    邀约与线下互动: ProfileDimension = Field(default_factory=ProfileDimension)
    关系边界表达: ProfileDimension = Field(default_factory=ProfileDimension)


class InteractionPattern(BaseModel):
    """从聊天中提取的多方可核查互动事件（对应「事件抽取」）。"""

    model_config = ConfigDict(extra="allow")

    event_id: str
    category: str
    participants: list[str] = Field(default_factory=list)
    message_ids: list[str] = Field(default_factory=list)
    description: str = ""
    certainty: Confidence = "medium"


class Signal(BaseModel):
    """好感信号（四分类），每条必须可回溯到真实消息。"""

    model_config = ConfigDict(extra="allow")

    category: Literal["positive", "negative", "neutral", "ambiguous"]
    name: str
    description: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    positive_interpretation: str = ""
    alternative_interpretation: str = ""
    evidence_strength: Literal["strong", "medium", "weak"] = "medium"
    impact: str = ""
    scope: str = ""


class RelationshipAssessment(BaseModel):
    """关系评估，包含反向验证所需的审慎要素。"""

    model_config = ConfigDict(extra="allow")

    stage: str = "信息不足"
    summary: str = ""
    supporting_facts: list[str] = Field(default_factory=list)
    contradicting_facts: list[str] = Field(default_factory=list)
    neutral_alternatives: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"


class Advisor(BaseModel):
    """AI 情感军师输出。"""

    model_config = ConfigDict(extra="allow")

    relationship_summary: str = ""
    strongest_signals: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class DataQuality(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_messages: int = 0
    confirmed_sender_ratio: float = 0.0
    unknown_sender_ratio: float = 0.0
    time_span: Optional[str] = None
    analyzable_text_ratio: float = 0.0
    time_order_anomalies: int = 0
    duplicate_message_risk: str = "unknown"
    partial_export_possible: bool = False
    coverage: str = ""
    limitations: list[str] = Field(default_factory=list)


class SenderStats(BaseModel):
    model_config = ConfigDict(extra="allow")

    message_count: int = 0
    message_ratio: float = 0.0
    char_count: int = 0


class Statistics(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    self_stats: SenderStats = Field(default_factory=SenderStats, alias="self")
    other_stats: SenderStats = Field(default_factory=SenderStats, alias="other")
    unknown_stats: SenderStats = Field(default_factory=SenderStats, alias="unknown")
    # 在可观察范围内的互动频率（条/天，粗略估计）
    messages_per_day: Optional[float] = None
    avg_interval_seconds: Optional[float] = None
    median_interval_seconds: Optional[float] = None
    # 同发送者连续 ≥2 条消息的片段次数（"连续发送消息"）
    consecutive_message_runs: int = 0
    # 可可靠识别的对话轮次（发送者切换计一次轮次）
    conversation_turns: Optional[int] = None
    # 主动开启聊天比例（仅在对话边界足够可靠时计算，否则为 null）
    self_initiation_ratio: Optional[float] = None
    initiation_note: str = ""


class ErrorInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str
    message: str
    field: str = ""


# ---------------------------------------------------------------------------
# 指标（metrics）：全部由 Python 汇总计算，公式随响应一起返回
# ---------------------------------------------------------------------------

class MessageFlag(BaseModel):
    """LLM 对单条消息的语义标记，用于 Python 汇总为指标。"""

    model_config = ConfigDict(extra="allow")

    id: str
    is_question: bool = False
    shared_activity: bool = False
    positive_tone: bool = False


class MessageCounts(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    self_count: int = Field(default=0, alias="self")
    other_count: int = Field(default=0, alias="other")
    unknown_count: int = Field(default=0, alias="unknown")
    total: int = 0


class MetricComponent(BaseModel):
    """互动参考指数的组成项，便于前端展示拆解。"""

    model_config = ConfigDict(extra="allow")

    key: str
    label: str
    raw_value: Optional[float] = None
    normalized_score: float = 0.0
    weight: float = 0.0
    contribution: float = 0.0
    available: bool = True
    note: str = ""


class MetricFormula(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    label: str
    formula: str
    denominator: str
    note: str = ""


class SemanticDetection(BaseModel):
    model_config = ConfigDict(extra="allow")

    method: Literal["llm", "keyword_fallback"] = "llm"
    text_message_count: int = 0
    flagged_message_count: int = 0
    note: str = ""


class Metrics(BaseModel):
    """API A 的定量指标集合，字段可直接驱动圆环图 / 进度条。"""

    model_config = ConfigDict(extra="allow")

    message_counts: MessageCounts = Field(default_factory=MessageCounts)
    participation_balance: Optional[float] = None
    other_question_ratio: Optional[float] = None
    shared_activity_ratio: Optional[float] = None
    positive_tone_ratio: Optional[float] = None
    interaction_index: float = 0.0
    interaction_index_components: list[MetricComponent] = Field(default_factory=list)
    formulas: list[MetricFormula] = Field(default_factory=list)
    semantic_detection: SemanticDetection = Field(default_factory=SemanticDetection)
    disclaimer: str = (
        "「互动参考指数」是启发式参考值，用于观察互动结构，不代表真实好感概率，"
        "也不能替代真实沟通。"
    )


class DailyPoint(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    date: str
    self_count: int = Field(default=0, alias="self")
    other_count: int = Field(default=0, alias="other")
    unknown_count: int = Field(default=0, alias="unknown")
    total: int = 0


class EvidenceItem(BaseModel):
    """证据原文，供前端渲染证据卡片。"""

    model_config = ConfigDict(extra="allow")

    id: str
    sender: str
    timestamp: str
    type: str = "text"
    content: str = ""
    # 上游导入器提供的原始昵称，仅做展示；缺失时为 None
    sender_name: Optional[str] = None


class AnalysisReport(BaseModel):
    """analysis-report/1.0 顶层输出。"""

    model_config = ConfigDict(extra="allow")

    analysis_version: str = "1.0"
    analysis_id: Optional[str] = None
    status: Literal["completed", "partial", "failed"] = "completed"
    data_quality: DataQuality = Field(default_factory=DataQuality)
    statistics: Statistics = Field(default_factory=Statistics)
    metrics: Optional[Metrics] = None
    daily_distribution: list[DailyPoint] = Field(default_factory=list)
    self_profile: Optional[Profile] = None
    other_profile: Optional[Profile] = None
    interaction_patterns: list[InteractionPattern] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    relationship_assessment: Optional[RelationshipAssessment] = None
    advisor: Optional[Advisor] = None
    evidence: dict[str, EvidenceItem] = Field(default_factory=dict)
    user_profile: Optional[dict] = None
    limitations: list[str] = Field(default_factory=list)
    errors: list[ErrorInfo] = Field(default_factory=list)