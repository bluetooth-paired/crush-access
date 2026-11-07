# AI 关系分析 API（analysis-report / 1.0）

本文档说明「申请查看你的好感度」机器人 V0.2 的统一下游分析接口，供前端与其他模块集成。

## 1. 概述

分析服务采用「确定性前处理 + LLM 定性分析」混合架构：

- **确定性代码**：数据质量检查、客观统计（消息数、字数、时间间隔、连续发送、对话轮次、主动开启比例）。绝不交给大模型计算。
- **LLM 定性分析**：双向人物画像、互动事件、好感信号（四分类）、反向验证的关系评估、AI 军师建议。

调用大模型前，程序先完成本地解析与统计；聊天正文只用于分析，不写入普通日志。

模型 API Key 仅保存在后端，前端不接触。

## 2. 接口

```
POST /api/v1/analyze
Content-Type: application/json
```

### 请求体

```json
{
  "conversation": {
    "schema_version": "1.0",
    "source": "wechat-cli",
    "chat_type": "private",
    "messages": [
      {
        "id": "m001",
        "timestamp": "2026-11-07T10:30+08:00",
        "sender": "self",
        "type": "text",
        "content": "周末有空吗？"
      }
    ],
    "metadata": {
      "total_messages": 1,
      "unknown_senders": 0,
      "anonymized": false,
      "id_origin": "export",
      "timestamp_precision": "minute"
    }
  },
  "options": {
    "include_advice": true,
    "language": "zh-CN"
  }
}
```

字段约定：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `conversation` | 是 | 导入器产出的完整 chat.json（Schema 1.0），字段名不得改动 |
| `conversation.schema_version` | 是 | 必须为 `"1.0"`，否则返回 `UNSUPPORTED_SCHEMA_VERSION` |
| `conversation.messages[].id` | 是 | 导出批次内编号，证据引用依据；缺失会导致 `INVALID_CONVERSATION` |
| `conversation.messages[].sender` | 是 | 仅 `self` / `other` / `unknown`；非法值归为 `unknown`（不猜测归属） |
| `options.include_advice` | 否 | 是否返回军师建议，默认 `true` |

### 成功响应（200）

返回 `analysis-report/1.0` 对象：

```json
{
  "analysis_version": "1.0",
  "status": "completed",
  "data_quality": {
    "total_messages": 6,
    "confirmed_sender_ratio": 1.0,
    "unknown_sender_ratio": 0.0,
    "time_span": "2026-11-07T02:30:00+00:00 ~ 2026-11-07T02:40:00+00:00",
    "analyzable_text_ratio": 1.0,
    "time_order_anomalies": 0,
    "duplicate_message_risk": "low",
    "partial_export_possible": true,
    "coverage": "共 6 条消息；已确认发送者 6/6（100.0%）；…",
    "limitations": ["样本疑似不完整或有较大时间空洞，结论适用范围有限。"]
  },
  "statistics": {
    "self": {"message_count": 3, "message_ratio": 0.5, "char_count": 12},
    "other": {"message_count": 3, "message_ratio": 0.5, "char_count": 10},
    "unknown": {"message_count": 0, "message_ratio": 0.0, "char_count": 0},
    "messages_per_day": 2160.0,
    "avg_interval_seconds": 60.0,
    "median_interval_seconds": 60.0,
    "consecutive_message_runs": 0,
    "conversation_turns": 6,
    "self_initiation_ratio": null,
    "initiation_note": "消息数不足 10 条，主动开启比例无法可靠计算。"
  },
  "self_profile": {
    "话题主动性": {"level": "中", "detail": "…", "evidence_ids": ["m001"], "confidence": "medium"},
    "对话延续程度": {"level": "中", "detail": "…", "evidence_ids": [], "confidence": "medium"},
    "个人生活分享": {"level": "中", "detail": "…", "evidence_ids": [], "confidence": "medium"},
    "情绪表达程度": {"level": "中", "detail": "…", "evidence_ids": [], "confidence": "medium"},
    "关心与回应程度": {"level": "中", "detail": "…", "evidence_ids": [], "confidence": "medium"},
    "邀约与线下互动": {"level": "中", "detail": "…", "evidence_ids": [], "confidence": "medium"},
    "关系边界表达": {"level": "中", "detail": "…", "evidence_ids": [], "confidence": "medium"}
  },
  "other_profile": { "（七个维度结构同 self_profile）": "…" },
  "interaction_patterns": [
    {
      "event_id": "evt_1",
      "category": "邀请见面",
      "participants": ["self"],
      "message_ids": ["m001"],
      "description": "用户询问周末是否有空",
      "certainty": "medium"
    }
  ],
  "signals": [
    {
      "category": "positive",
      "name": "主动发起",
      "description": "…",
      "evidence_ids": ["m001"],
      "positive_interpretation": "…",
      "alternative_interpretation": "…",
      "evidence_strength": "medium",
      "impact": "…",
      "scope": "…"
    }
  ],
  "relationship_assessment": {
    "stage": "友好互动期",
    "summary": "…",
    "supporting_facts": ["…"],
    "contradicting_facts": ["…"],
    "neutral_alternatives": ["…"],
    "confidence": "low"
  },
  "advisor": {
    "relationship_summary": "…",
    "strongest_signals": ["…"],
    "uncertainties": ["…"],
    "suggestions": ["…"]
  },
  "limitations": ["…"],
  "errors": []
}
```

关键语义：

- `status`：`completed` / `partial` / `failed`。数据不足、单方消息缺失、全部 unknown 时为 `partial`；模型失败时为 `failed`。
- `self_profile` / `other_profile`：无法识别对应一方消息时为 `null`。
- `signals` 四分类：`positive` / `negative` / `neutral` / `ambiguous`。
- `self_initiation_ratio`：数据不足时为 `null`（不做「每天第一条=主动」的武断判定）。
- 所有 `evidence_ids` / `message_ids` 均保证存在于输入消息中；不存在的会被剔除并记入 `limitations`。

## 3. 错误响应

| HTTP | code | 含义 |
| --- | --- | --- |
| 400 | `INVALID_REQUEST` | 请求体不是合法 JSON |
| 400 | `INVALID_CONVERSATION` | conversation 缺失/结构不合法 |
| 400 | `UNSUPPORTED_SCHEMA_VERSION` | schema_version 非 1.0 |
| 400 | `EMPTY_CONVERSATION` | 消息列表为空 |
| 500 | `ANALYSIS_ERROR` | 分析过程其他异常 |

错误体固定结构：

```json
{
  "error": {
    "code": "INVALID_CONVERSATION",
    "message": "聊天记录格式不符合要求"
  }
}
```

## 4. 数据流向与隐私

1. 前端把导入器产出的 `chat.json` 放入 `conversation` 字段发到后端。
2. 后端本地解析并执行确定性统计（不落盘聊天正文）。
3. 调用大模型时，聊天记录作为待分析数据提交；**上传第三方模型前应在产品层明确告知用户数据流向并征得同意**。
4. 普通日志只记录聚合数字（消息数、比例、信号数），不记录完整私密聊天内容。
5. 建议提供「删除数据」能力：可在产品侧实现按用户/会话删除已存记录。

## 5. 前端对接建议

- 直接消费 `POST /api/v1/analyze` 的 `200` 响应，渲染 `self_profile` / `other_profile` / `signals` / `relationship_assessment` / `advisor`。
- 用 `status` 做降级展示：`partial` 时提示「样本有限，结论仅供参考」；`failed` 时展示 `errors`。
- `evidence_ids` 用于点击「查看原文」时定位消息；不要直接依赖大模型临时生成的自然语言作为字段协议。
- 调用前校验 `schema_version === "1.0"`，避免前端把不兼容数据发给后端。