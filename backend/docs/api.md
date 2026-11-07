# 「申请查看你的好感度」后端 API 文档 v1.0.0

面向 Auria（GitHub Pages 前端）的联调文档。服务端只负责分析与军师对话，不做前端渲染。

- Base URL：`http://<host>:8000`
- 在线交互文档：`GET /docs`（Swagger UI）、`GET /openapi.json`（OpenAPI 3.1）
- 健康检查：`GET /health`
- 所有响应均为 `application/json; charset=utf-8`
- 金额/耗时类字段均为整数秒或浮点比例，比例统一保留 4 位小数

---

## 0. 通用约定

### 0.1 客户端标识 `client_id`

前端是纯静态站点，没有登录体系，因此用 `client_id` 做**报告归属校验**：

1. 调用 `POST /api/v1/analyze` 时可不传 `client_id`，服务端生成一个并随响应返回；
2. 前端把 `client_id` 存 `localStorage`，后续调用军师接口时通过请求体或请求头 `X-Client-Id` 传回；
3. 服务端会校验 `client_id` 是否与该 `analysis_id` 的创建者一致，不一致返回 `403 ANALYSIS_FORBIDDEN`；
4. `analysis_id` 本身是 UUID v4（不可枚举），与 `client_id` 构成双重隔离。

> 建议：前端首次访问生成 `client_id`（8–64 位字母/数字/`_`/`-`），之后固定复用。

### 0.2 CORS

已开启 CORS：

- 默认放行 `https://*.github.io`（正则 `https://([a-zA-Z0-9-]+\.)*github\.io`）
- 默认放行本地开发来源 `http://localhost:3000 / 5173 / 8080`、`http://127.0.0.1:5500`
- 可通过 `CORS_ALLOW_ORIGINS` 追加来源
- 不使用 Cookie/凭证，`CORS_ALLOW_CREDENTIALS=false`

### 0.3 有效期与隔离

| 项目 | 默认 | 环境变量 |
|---|---|---|
| 报告有效期 | 7 天 | `ANALYSIS_TTL_SECONDS` |
| 会话有效期 | 7 天 | `SESSION_TTL_SECONDS` |
| 单请求消息上限 | 3000 条 | `MAX_MESSAGES_PER_REQUEST` |
| 单条消息字符上限 | 4000 | `MAX_MESSAGE_CHARS` |
| 军师单条提问上限 | 2000 | `MAX_ADVISOR_MESSAGE_CHARS` |
| 单会话最大轮数 | 60 | `MAX_ADVISOR_TURNS` |

过期后访问返回 `410 ANALYSIS_EXPIRED`；不存在的 `analysis_id` 返回 `404 ANALYSIS_NOT_FOUND`。

### 0.4 错误响应统一格式

```json
{
  "error": {
    "code": "ANALYSIS_NOT_FOUND",
    "message": "找不到分析报告：46a5084a-...",
    "details": null
  }
}
```

| HTTP | code | 含义 |
|---|---|---|
| 400 | `INVALID_CONVERSATION` | conversation 结构非法 |
| 400 | `UNSUPPORTED_SCHEMA_VERSION` | 仅支持 `schema_version = "1.0"` |
| 400 | `EMPTY_CONVERSATION` | messages 为空 |
| 400 | `CONVERSATION_TOO_LARGE` | 消息条数超限 |
| 400 | `MESSAGE_TOO_LONG` | 单条消息/提问超长 |
| 403 | `ANALYSIS_FORBIDDEN` | client_id 与报告归属不符 |
| 404 | `ANALYSIS_NOT_FOUND` | analysis_id / session_id 不存在 |
| 410 | `ANALYSIS_EXPIRED` | 报告或会话已过期 |
| 422 | `INVALID_REQUEST` | 请求体字段校验失败（details 含字段定位） |
| 429 | `SESSION_TURN_LIMIT` | 会话轮数达上限 |
| 502 | `MODEL_ERROR` | 模型调用失败 |
| 503 | `MODEL_NOT_CONFIGURED` | 未配置模型凭据 |

---

### 0.5 输入数据格式（chat.json Schema 1.0）

两个接口都以 `chat.json` Schema 1.0 为输入基础（`/advisor/chat` 不直接收聊天记录，只用分析时保存的那一份）。

#### 顶层字段

| 字段 | 必填 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `schema_version` | 否 | string | `"1.0"` | 仅支持 `"1.0"`，其它值返回 400 `UNSUPPORTED_SCHEMA_VERSION` |
| `source` | 否 | string | `"wechat-cli"` | 数据来源标识，仅记录，不参与计算 |
| `chat_type` | 否 | string | `"private"` | `private` / `group`，仅记录 |
| `messages` | **是** | array | — | 不能为空；默认上限 3000 条（`MAX_MESSAGES_PER_REQUEST`） |
| `metadata` | 否 | object | `{}` | 导入器元信息，见下表；**以 `messages` 实际内容为准**，metadata 不参与指标计算 |
| 其它字段 | 否 | any | — | 允许额外字段（`extra=allow`），不会报错 |

#### `messages[]` 字段

| 字段 | 必填 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `id` | **是** | string | — | 消息唯一标识，报告里的 `evidence_ids` / `evidence` 用它回溯原文。建议 `m001` 递增 |
| `timestamp` | **是** | string | — | ISO 8601，建议带时区偏移（如 `2026-11-07T10:30:00+08:00` 或 `...Z`）。**无时区时按 `ASSUME_NAIVE_TZ_OFFSET_HOURS`（默认 `+8`，微信导出为本地时间）解析**；无法解析时不报错，但该消息不参与时间相关统计 |
| `sender` | **是** | string | — | `self`（用户本人）/ `other`（对方 TA）/ `unknown`（无法确定）。非法值一律按 `unknown` 处理，**绝不猜测归属** |
| `type` | 否 | string | `"text"` | `text` 参与语义与计数；`image` / `voice` / `video` / `sticker` / `system` 等不计入「可分析文本」比例 |
| `content` | 否 | string | `""` | 文本内容，单条上限 4000 字符（`MAX_MESSAGE_CHARS`），超限返回 400 `MESSAGE_TOO_LONG` |
| 其它字段 | 否 | any | — | 允许额外字段，原样保留在存储的会话中 |

#### `metadata` 字段（全部可选，仅作记录）

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `total_messages` | int | `0` | 导入器自报条数，与 `messages` 实际长度不一致时以实际为准 |
| `unknown_senders` | int | `0` | 导入器自报的未知发送者条数 |
| `anonymized` | bool | `false` | 是否已匿名化（仅提示，不做内容检测） |
| `id_origin` | string | `""` | 如 `export`（导出原始 ID）/ `generated`（生成 ID） |
| `timestamp_precision` | string | `"minute"` | 时间精度提示，如 `minute` / `second` |

#### 处理规则

- `sender=unknown` 的消息计入总数与 `metrics.message_counts.unknown`，但**不归入任何一方**，也不参与 `participation_balance` 分母。
- 时间乱序不报错，会在 `data_quality.time_order_anomalies` 中记录条数。
- 重复消息（同 id / 同内容同时间）会在 `data_quality.duplicate_message_risk` 中提示。
- 未提供人物档案（`profile`）时，画像仅基于聊天证据；提供了 `profile` 也只作为上下文，不会替代证据。

#### 完整有效示例（可直接用于联调）

```json
{
  "schema_version": "1.0",
  "source": "wechat-cli",
  "chat_type": "private",
  "messages": [
    {
      "id": "m001",
      "timestamp": "2026-11-06T20:00+08:00",
      "sender": "self",
      "type": "text",
      "content": "今天降温了，你那边冷不冷？"
    },
    {
      "id": "m002",
      "timestamp": "2026-11-06T20:05+08:00",
      "sender": "other",
      "type": "text",
      "content": "还行，穿了外套。你注意别感冒"
    },
    {
      "id": "m003",
      "timestamp": "2026-11-06T20:07+08:00",
      "sender": "self",
      "type": "text",
      "content": "我今天加班到八点，刚到家"
    },
    {
      "id": "m004",
      "timestamp": "2026-11-06T20:10+08:00",
      "sender": "other",
      "type": "text",
      "content": "这么晚啊，吃饭了吗？"
    },
    {
      "id": "m005",
      "timestamp": "2026-11-07T09:30+08:00",
      "sender": "self",
      "type": "text",
      "content": "早，昨天谢谢你的关心"
    },
    {
      "id": "m006",
      "timestamp": "2026-11-07T09:45+08:00",
      "sender": "other",
      "type": "text",
      "content": "早呀～今天也要好好吃饭"
    },
    {
      "id": "m007",
      "timestamp": "2026-11-07T09:46+08:00",
      "sender": "self",
      "type": "text",
      "content": "周末有个摄影展，你有兴趣一起去看看吗？"
    },
    {
      "id": "m008",
      "timestamp": "2026-11-07T10:20+08:00",
      "sender": "other",
      "type": "text",
      "content": "周六下午可以，具体在哪？"
    },
    {
      "id": "m009",
      "timestamp": "2026-11-08T18:00+08:00",
      "sender": "self",
      "type": "text",
      "content": "今天把展看完啦，拍了几张照片"
    },
    {
      "id": "m010",
      "timestamp": "2026-11-08T18:12+08:00",
      "sender": "other",
      "type": "text",
      "content": "哈哈发我看看，我很期待"
    }
  ],
  "metadata": {
    "total_messages": 10,
    "unknown_senders": 0,
    "anonymized": true,
    "id_origin": "export",
    "timestamp_precision": "minute"
  }
}
```

> 以上为**虚构数据**，可直接复制为 `chat.json` 联调用；请勿提交真实私人聊天记录。

---

## A. 互动信号分析

### A.1 请求

`POST /api/v1/analyze`

请求头（可选）：`X-Client-Id: auria-frontend-7f3a91`

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
      },
      {
        "id": "m002",
        "timestamp": "2026-11-07T10:32+08:00",
        "sender": "other",
        "type": "text",
        "content": "有呀！"
      }
    ]
  },
  "profile": {
    "self": { "nickname": "小 A", "age_range": "25-29" },
    "other": { "nickname": "小 B", "relationship_stage": "同事，认识 3 个月" }
  },
  "client_id": "auria-frontend-7f3a91",
  "options": { "include_advice": true, "include_evidence": true }
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `conversation` | 是 | 墨翊 `chat.json` Schema 1.0，必须含 `schema_version`、`messages` |
| `profile` | 否 | 人物档案，仅作补充上下文，**不能替代聊天证据**；结构自由（对象） |
| `client_id` | 否 | 8–64 位字母数字 `_` `-`；不传则服务端生成并返回 |
| `options.include_advice` | 否 | 默认 `true`，为 `false` 时 `advisor` 为空 |
| `options.include_evidence` | 否 | 默认 `true`，为 `false` 时 `evidence` 为空对象（减小响应体积） |
| `options.thinking_level` | 否 | `auto`(默认) / `low` / `medium` / `high`；控制定性分析的思考强度，是否真实生效见响应 `ai_config.thinking` |

`messages[].sender` 只接受 `self` / `other` / `unknown`；`unknown` 不会被猜成任何一方。

### A.2 响应（真实运行示例，数组已截断）

```json
{
  "analysis_id": "46a5084a-b053-43a0-a63a-c7d11cc778be",
  "client_id": "auria-frontend-7f3a91",
  "created_at": "2026-11-07T12:21:42.626262+00:00",
  "expires_at": "2026-11-14T12:21:42.626262+00:00",
  "status": "completed",

  "ai_config": {
    "thinking": {
      "requested": "auto",
      "applied": "server-default",
      "supported": true,
      "sent_parameters": {},
      "note": "使用服务端默认思考配置（环境变量 LLM_THINKING），本次请求不覆盖。"
    }
  },

  "metrics": {
    "message_counts": { "self": 6, "other": 6, "unknown": 0, "total": 12 },
    "participation_balance": 1.0,
    "other_question_ratio": 0.3333,
    "shared_activity_ratio": 0.1667,
    "positive_tone_ratio": 0.75,
    "interaction_index": 79.7,
    "interaction_index_components": [
      {
        "key": "participation_balance",
        "label": "参与平衡度",
        "raw_value": 1.0,
        "normalized_score": 1.0,
        "weight": 0.25,
        "contribution": 0.25,
        "available": true,
        "note": "双方消息量越接近 1.0，说明对话越双向。"
      }
    ],
    "formulas": [
      {
        "key": "participation_balance",
        "label": "参与平衡",
        "formula": "2 × min(self, other) / (self + other)",
        "denominator": "self + other（不含 unknown）",
        "note": "取值 0~1，1 表示双方消息量完全相同；无已被确认的发送者时为 null。"
      }
    ],
    "semantic_detection": {
      "method": "llm",
      "text_message_count": 12,
      "flagged_message_count": 12,
      "note": "语义标记由 LLM 识别，Python 仅做汇总统计。"
    },
    "disclaimer": "互动参考指数为启发式参考值，不代表真实好感概率。"
  },

  "daily_distribution": [
    { "date": "2026-11-06", "self": 3, "other": 3, "unknown": 0, "total": 6 },
    { "date": "2026-11-07", "self": 2, "other": 2, "unknown": 0, "total": 4 },
    { "date": "2026-11-08", "self": 1, "other": 1, "unknown": 0, "total": 2 }
  ],

  "portraits": {
    "self_portrait": [
      {
        "key": "topic_initiative",
        "label": "话题主动性",
        "level": "高",
        "score": 80,
        "detail": "两次会话均由用户主动发起",
        "evidence_ids": ["m001", "m007", "m009"],
        "confidence": "high"
      }
    ],
    "other_portrait": [
      {
        "key": "response_engagement",
        "label": "关心与回应程度",
        "level": "中",
        "score": 55,
        "detail": "提醒用户别感冒、建议点热汤",
        "evidence_ids": ["m002", "m006"],
        "confidence": "high"
      }
    ]
  },

  "signals": [
    {
      "category": "positive",
      "name": "接受线下见面邀约",
      "description": "对方收到看展邀约后直接同意周六下午前往，还主动询问具体地点",
      "evidence_ids": ["m010"],
      "positive_interpretation": "对方愿意和用户进行线下活动，接受度较高",
      "alternative_interpretation": "对方本身对展览感兴趣，恰好周六有空",
      "evidence_strength": "strong",
      "impact": "大幅提升关系发展可能性判断",
      "scope": "仅说明本次邀约被接受，不代表长期意愿"
    }
  ],

  "interaction_patterns": [
    {
      "event_id": "evt_1",
      "category": "邀请见面",
      "participants": ["self"],
      "message_ids": ["m009"],
      "description": "用户邀请对方周末一起看摄影展",
      "certainty": "high"
    }
  ],

  "relationship_assessment": {
    "stage": "友好互动期",
    "summary": "双方处于有来有回的友好社交阶段，具备线下推进机会",
    "supporting_facts": ["对方多次关心用户生活状态", "对方接受线下邀约"],
    "contradicting_facts": ["对方从未主动发起会话"],
    "neutral_alternatives": ["提醒健康、接受展览邀约也可能是普通社交行为"],
    "confidence": "medium"
  },

  "advisor": {
    "relationship_summary": "互动友好，可以自然推进线下见面",
    "strongest_signals": ["连续两次关心健康", "接受邀约并主动问地点"],
    "uncertainties": ["对方主动意愿强度尚不明确"],
    "suggestions": ["先确认时间地点", "见面时多聊双方兴趣"]
  },

  "evidence": {
    "m010": {
      "id": "m010",
      "sender": "other",
      "sender_label": "对方(TA)",
      "timestamp": "2026-11-07T10:20+08:00",
      "type": "text",
      "content": "周六下午可以，具体在哪？"
    }
  },

  "data_quality": {
    "total_messages": 12,
    "confirmed_sender_ratio": 1.0,
    "unknown_sender_ratio": 0.0,
    "time_span": "2026-11-06T12:00:00+00:00 ~ 2026-11-08T10:12:00+00:00",
    "analyzable_text_ratio": 1.0,
    "time_order_anomalies": 0,
    "duplicate_message_risk": "low",
    "partial_export_possible": false,
    "coverage": "共 12 条消息；已确认发送者 12/12（1.0）",
    "limitations": []
  },

  "limitations": ["样本仅覆盖 3 天共 12 条消息"],
  "errors": []
}
```

### A.3 字段用途（前端绘图对照）

| 字段 | 前端用途 |
|---|---|
| `metrics.message_counts` | 圆环图（self / other / unknown 三段） |
| `metrics.participation_balance` | 进度条 0–100（乘 100 显示） |
| `metrics.other_question_ratio` | 进度条（TA 提问占比） |
| `metrics.shared_activity_ratio` | 进度条（共同活动表达） |
| `metrics.positive_tone_ratio` | 进度条（积极语气） |
| `metrics.interaction_index` | 大号数字 + 环形仪表盘（0–100，**需展示 disclaimer**） |
| `metrics.interaction_index_components` | 指标拆解列表（每项含 weight / contribution，可画堆叠条） |
| `metrics.formulas` | 指标口径弹窗/脚注（含分母定义） |
| `daily_distribution` | 柱状图（x=date，y 分 self / other 两色堆叠） |
| `portraits.self_portrait / other_portrait` | 雷达图（`score` 0–100，`数据不足` 时 `score=null` 需跳过该轴）或 7 条进度条 |
| `signals` | 证据卡片列表（`category` 决定配色，`evidence_ids` 关联 `evidence` 展开原文） |
| `evidence` | 证据卡片正文（key = 消息 ID） |
| `relationship_assessment` | 结论卡（stage 徽章 + summary + 支持/反向/中性三栏） |
| `advisor` | 军师建议卡（最多 3 条 suggestions） |

### A.4 指标计算口径（严格定义）

所有指标都由 **Python 计算**；LLM 只负责给单条消息打语义标签（是否提问 / 是否共同活动 / 是否积极语气），Python 汇总成比例。

设：

- `self_n` / `other_n` / `unknown_n`：该方消息数（所有类型）
- `known_n = self_n + other_n`
- `text_all`：可分析文本消息集合（`type == "text"` 且 `content` 去空格后非空）
- `text_other`：`text_all` 中 `sender == other` 的消息集合

| 指标 | 公式 | 分母 |
|---|---|---|
| `message_counts.self/other/unknown` | 直接计数 | 无（绝对数） |
| `participation_balance` | `2 × min(self_n, other_n) / (self_n + other_n)` | `self_n + other_n`（**不含 unknown**）；`known_n = 0` 时为 `null` |
| `other_question_ratio` | `|{m ∈ text_other : is_question}| / |text_other|` | TA 的可分析文本消息数 |
| `shared_activity_ratio` | `|{m ∈ text_all : shared_activity}| / |text_all|` | 全部可分析文本消息数 |
| `positive_tone_ratio` | `|{m ∈ text_all : positive_tone}| / |text_all|` | 全部可分析文本消息数 |
| `interaction_index` | 见下式 | 各子项先归一化到 0–1 再加权 |

`interaction_index` 精确公式（权重和为 1.0）：

```
S1 = participation_balance                                 权重 0.25
S2 = min(1, total / 100)                                   权重 0.15   # 100 条消息视为满分
S3 = min(1, other_question_ratio / 0.30)                   权重 0.25   # TA 提问占 30% 视为满分
S4 = min(1, shared_activity_ratio / 0.20)                  权重 0.20   # 共同活动占 20% 视为满分
S5 = positive_tone_ratio                                   权重 0.15

interaction_index = round(100 × (0.25·S1 + 0.15·S2 + 0.25·S3 + 0.20·S4 + 0.15·S5), 1)
```

- 任一分项为 `null`（数据不足）时按 0 计入，并在 `interaction_index_components[].available` 标记为 `false`
- 每个分项的 `contribution = round(normalized_score × weight, 4)`，前端可直接堆叠展示
- `semantic_detection.method`：
  - `"llm"`：LLM 正常返回了语义标签
  - `"keyword_fallback"`：LLM 未返回标签时退化为关键词规则，**此时指标仅供粗略参考**，前端应提示

> ⚠️ `interaction_index` 是**启发式参考指数**，不是真实好感概率，不可作为关系结论的因果依据。响应中 `metrics.disclaimer` 必须展示。

### A.5 画像维度 key 对照

| key | label |
|---|---|
| `topic_initiative` | 话题主动性 |
| `conversation_continuity` | 对话延续程度 |
| `life_sharing` | 个人生活分享 |
| `emotion_expression` | 情绪表达程度 |
| `care_and_response` | 关心与回应程度 |
| `invitation_and_offline` | 邀约与线下互动 |
| `boundary_expression` | 关系边界表达 |

`score` 由 `level` 确定性映射：`高=80`、`中=55`、`低=30`、`数据不足=null`（仅用于绘图，不代表精确程度）。

`signals[].category` 取值语义：`positive`（积极互动信号）/ `negative`（可能的消极互动信号）/ `neutral`（普通社交行为）/ `ambiguous`（有多种合理解释）。

---

## B. AI 情感军师（多轮）

### B.1 请求

`POST /api/v1/advisor/chat`

```json
{
  "analysis_id": "46a5084a-b053-43a0-a63a-c7d11cc778be",
  "session_id": null,
  "message": "她答应看展，是不是说明有戏？我下一步该怎么做？",
  "client_id": "auria-frontend-7f3a91",
  "thinking_level": "auto",
  "web_search": false
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `analysis_id` | 是 | API A 返回的 ID，报告过期返回 410 |
| `message` | 是 | 用户提问，去空格后不能为空，≤ 2000 字 |
| `session_id` | 否 | 首轮不传（服务端新建并返回）；后续轮次原样带回。**传入不存在的 session_id 返回 404**，不会静默新建 |
| `client_id` | 否 | 必须与创建分析时一致，否则 403 |
| `thinking_level` | 否 | `auto`(默认) / `low` / `medium` / `high`，见 B.4 |
| `web_search` | 否 | 布尔，**默认 `false`（关闭）**；开启后只用清洗过的用户提问检索，见 B.4 |

> 服务端不会重新分析全部聊天记录：报告、原文与统计都已持久化，军师只读取本次相关的报告摘要 + Top-N 证据原文。

### B.2 响应（真实运行示例）

```json
{
  "analysis_id": "46a5084a-b053-43a0-a63a-c7d11cc778be",
  "session_id": "490d8f28-71e0-4e28-8d91-69d9dbc3dcd2",
  "turn": 1,
  "reply": "从目前聊天来看，对方愿意接受你的看展邀约还主动问地点（m010），加上之前多次提醒你别感冒、问有没有吃饭，对你是有明显好感的。不过现在还不能完全确定，也有可能是她本身对摄影展感兴趣。",
  "evidence_ids": ["m002", "m004", "m006", "m010"],
  "evidence": [
    {
      "id": "m010",
      "sender": "other",
      "sender_label": "对方(TA)",
      "timestamp": "2026-11-07T10:20+08:00",
      "type": "text",
      "content": "周六下午可以，具体在哪？"
    }
  ],
  "suggestions": [
    "看展时多聊摄影相关的话题，也自然分享一点自己的生活",
    "看完展可以顺势约个饭，不要一次安排太满",
    "之后观察她会不会主动找你聊天，判断主动意愿"
  ],
  "boundary_notes": [
    "保持轻松自然，不要过度追问对方私人问题"
  ],
  "ai_config": {
    "thinking": {
      "requested": "auto",
      "applied": "server-default",
      "supported": true,
      "sent_parameters": {},
      "note": "使用服务端默认思考配置（环境变量 LLM_THINKING），本次请求不覆盖。"
    },
    "web_search": {
      "requested": false,
      "performed": false,
      "results_count": 0,
      "query_used": null,
      "note": "未开启联网搜索（默认关闭）。"
    }
  }
}
```

| 字段 | 说明 |
|---|---|
| `session_id` | 会话标识，前端需持久化后携带 |
| `turn` | 当前是第几轮（从 1 开始），达到 `MAX_ADVISOR_TURNS` 返回 429 |
| `reply` | 只针对当前问题的自然语言回复（60~200 字），**不复述画像 / 指标 / 关系评估**；可含消息 ID 引用如 `m010` |
| `evidence_ids` | 本轮引用的消息 ID，**已过滤掉模型编造的 ID**，可直接用于高亮原文 |
| `evidence` | 上述 ID 对应的原文，便于前端直接渲染引用卡片 |
| `suggestions` | 沟通建议（0–3 条） |
| `boundary_notes` | 边界提醒（尊重对方意愿、避免过度解读） |

### B.3 多轮会话行为

- 同一 `session_id` 会保留上下文（默认最近 20 轮 / 40 条消息窗口）
- 上下文与 `analysis_id`、`client_id` 绑定，换账号或换报告都无法复用
- 显式传入的 `session_id` 不存在（已过期或被清理）时返回 `404 ANALYSIS_NOT_FOUND`，前端应清空本地 `session_id` 重新开始；服务端**不会**用这个 ID 静默新建会话
- 会话默认 7 天过期（`SESSION_TTL_SECONDS` 可调），每次对话会刷新有效期

---

### B.4 AI 配置参数（真实生效范围）

#### `thinking_level`：思考强度

| 取值 | 下发参数 | 生效条件 | 说明 |
|---|---|---|---|
| `auto`（默认） | 不下发 | — | 沿用服务端默认（环境变量 `LLM_THINKING`），响应 `applied = "server-default"` |
| `low` | `thinking.type = disabled` | 端点支持 thinking 参数 | 关闭深度思考，优先响应速度与成本 |
| `medium` | `thinking.type = enabled` | 同上 | 使用模型默认思考预算 |
| `high` | `thinking.type = enabled` + `reasoning_effort = high` | 同上 | 请求更高推理强度 |

**不支持时会明确说明，不会假装生效**：

- 端点不支持时（如 DeepSeek / Kimi / 一般 OpenAI 兼容端点），响应返回
  `supported=false`、`applied="server-default"`、`sent_parameters={}`，
  `note` 明确写「该档位未生效」。
- 是否支持以 `GET /health` 的 `features.thinking_supported` 为准。
- 平台网关不返回 reasoning token 明细，因此服务端**不承诺**强度可被量化验证；`high` 只是把更强的参数真实下发给上游。

#### `web_search`：联网搜索（默认关闭）

| 项 | 说明 |
|---|---|
| 默认值 | `false`（关闭），不传即关闭 |
| 开关语义 | `true` = 本次请求执行一次真实联网检索，并把结果作为外部参考注入上下文 |
| 搜索词来源 | **只使用当前这条用户提问**，并做隐私清洗：去掉 `m001` 这类消息 ID、去掉引号内长片段、去掉「引用那条」等指代残句、截断到 60 字 |
| 永不外发的内容 | 聊天原文、证据 message、人物档案、分析报告、历史会话 |
| 结果元信息 | 响应 `ai_config.web_search`：`requested / performed / results_count / query_used / note` |
| 失败处理 | 搜索失败时 `performed=false` 且 `note` 说明原因，**不伪造搜索结果**，也不影响军师回复 |
| 部署可用性 | 以 `GET /health` 的 `features.web_search.supported` 为准；不可用时 `performed=false` |

**实测记录（2026-11-07，平台网关 `doubao-seed-2-0-pro-260215`）**：`low` / `medium` / `high` 三档均真实下发（`high` 附带 `reasoning_effort=high`）；`web_search=true` 真实返回 3 条检索结果并注入上下文。DeepSeek / Kimi 直连未实测（无 Key），按设计返回 `supported=false`，详见 `docs/TEST_REPORT.md`。

#### 明确不支持的配置（避免误用）

- 接口**不接收** `api_key` / `base_url` / `model` 等凭据与模型切换参数，模型与密钥只由服务端环境变量管理；
- 不支持按请求切换模型（同一部署固定一个模型端点）；
- 不支持流式输出（两个接口均为一次性 JSON 响应）；
- 联网搜索只返回搜索摘要与链接，不抓取网页全文。

---

## C. 健康检查

`GET /health`

```json
{
  "status": "ok",
  "version": "1.0.0",
  "time": "2026-11-07T12:21:42.626262+00:00",
  "store_backend": "memory",
  "model": {
    "configured": true,
    "provider": "platform-gateway",
    "model": "doubao-seed-2-0-pro-260215"
  },
  "features": {
    "thinking_levels": ["auto", "low", "medium", "high"],
    "thinking_supported": true,
    "thinking_note": "当前端点接受思考强度参数，实际推理深度由上游模型决定。",
    "provider": "platform-gateway",
    "web_search": {
      "supported": true,
      "default_enabled": false,
      "privacy": "只使用清洗后的用户提问作为搜索词，不上传聊天原文或人物档案。",
      "note": "搜索执行结果以 ai_config.web_search.performed 为准。"
    }
  }
}
```

`model.configured = false` 表示未配置任何模型凭据，此时分析/对话接口会返回 `503 MODEL_NOT_CONFIGURED`。
该接口不返回任何密钥内容。

---

## D. 联调建议流程

1. `GET /health` 确认服务与模型可用
2. `POST /api/v1/analyze` 拿到 `analysis_id` / `client_id` 与图表数据
3. 渲染圆环图 + 柱状图 + 雷达图 + 证据卡片
4. 用户提问时 `POST /api/v1/advisor/chat`，把首轮返回的 `session_id` 存下来
5. 统一处理错误：读 `error.code`；`410` 提示重新分析，`503` 提示服务未配置模型

## E. 本地调试

```bash
# 1. 安装依赖
uv sync

# 2. 配置模型
cp .env.example .env   # 填入 LLM_API_KEY（DeepSeek / Kimi 均可）

# 3. 启动
bash scripts/run_api.sh        # 默认 http://127.0.0.1:8000

# 4. 真实模型端到端验证
PYTHONPATH=src python scripts/smoke_test_api.py
```

Swagger UI：`http://127.0.0.1:8000/docs`

---

## F. 向后兼容与变更记录

### F.1 兼容承诺

- 路径不变：`/api/v1/analyze`、`/api/v1/advisor/chat`、`/health`。
- 已有请求字段不重命名、不改为必填：不带任何新增字段的旧请求行为完全一致。
- 已有响应字段不删除、不改类型：新增字段（`ai_config`、`ai_config.thinking`、`ai_config.web_search`）均为**附加字段**，老前端可忽略。
- `reply` 语义收紧（只回答问题、不复述报告），字段名与类型未变。

### F.2 本次变更（v1.1.0）

| 变更 | 类型 | 说明 |
|---|---|---|
| 军师 `reply` 精简 | 行为 | 上下文瘦身（画像只给等级）+ 提示词禁止复述报告；回复 60~200 字 |
| `options.thinking_level` | 新增可选 | 分析接口思考强度，默认 `auto` |
| `thinking_level` | 新增可选 | 军师接口思考强度，默认 `auto` |
| `web_search` | 新增可选 | 军师接口联网搜索，默认 `false` |
| `ai_config` | 新增响应字段 | 报告/对话返回思考强度与搜索的真实生效情况 |
| `/health.features` | 新增响应字段 | 声明本部署真实支持的能力 |

### F.3 前端最小改动建议

- 想在设置面板提供「思考强度」：把 `low/medium/high` 原样传给接口即可；若 `ai_config.thinking.supported === false`，UI 应展示「当前模型不支持该设置」而不是假装已开启。
- 想加「联网搜索」开关：默认 `false`，开启后读 `ai_config.web_search.performed` 判断是否真的搜到，不要仅凭请求参数假设成功。

---

## G. API 地址、CORS 与部署配置

### G.1 地址

| 环境 | 地址 |
|---|---|
| 本地 | `http://127.0.0.1:8000`（`bash scripts/run_api.sh`） |
| 独立部署 | `http://<你的域名>/api/v1/analyze`、`/api/v1/advisor/chat`、`/health` |
| 文档 | `/docs`（Swagger UI）、`/redoc`、`/openapi.json` |

### G.2 CORS

默认放行：

- 正则 `https://([a-zA-Z0-9-]+\.)*github\.io`（覆盖 `*.github.io` 的 GitHub Pages）
- 本地开发来源：`http://localhost:3000`、`http://localhost:5173`、`http://localhost:8080`、`http://127.0.0.1:5500`

自定义：

```bash
CORS_ALLOW_ORIGINS="https://auria.github.io,https://example.com"
CORS_ALLOW_ORIGIN_REGEX="https://([a-zA-Z0-9-]+\.)*github\.io"
CORS_ALLOW_CREDENTIALS=false
```

允许的方法：`GET, POST, OPTIONS`；允许的请求头：`Content-Type, X-Client-Id, Authorization`。

> 若前端用 `credentials: 'include'`，需要设置 `CORS_ALLOW_CREDENTIALS=true` 且不能用通配来源（本服务默认使用正则白名单，可满足）。

### G.3 关键环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | — | 任意 OpenAI 兼容端点 |
| `DEEPSEEK_API_KEY` | — | 使用 DeepSeek 官方 |
| `MOONSHOT_API_KEY` | — | 使用 Kimi / Moonshot 官方 |
| `LLM_THINKING` | `disabled` | `auto` 档位与服务端默认行为的思考开关 |
| `ANALYSIS_TTL_SECONDS` / `SESSION_TTL_SECONDS` | 604800 | 报告 / 会话有效期（秒） |
| `STORE_BACKEND` | `memory` | `memory` / `postgres` |
| `DATABASE_URL` / `PGDATABASE_URL` | — | postgres 连接串 |
| `MAX_MESSAGES_PER_REQUEST` | 3000 | 单次分析消息上限 |
| `MAX_MESSAGE_CHARS` | 4000 | 单条消息字符上限 |
| `MAX_ADVISOR_MESSAGE_CHARS` | 2000 | 军师提问字符上限 |
| `MAX_ADVISOR_TURNS` | 60 | 单会话轮数上限 |
| `ADVISOR_EVIDENCE_LIMIT` | 8 | 军师每轮检索证据条数 |

### G.4 联调检查清单

1. `GET /health` → `status=ok`、`model.configured=true`；
2. 看 `features.thinking_supported` / `features.web_search.supported` 决定前端是否展示对应设置；
3. `POST /api/v1/analyze` → 存 `analysis_id` + `client_id`；
4. 画图：`metrics` / `daily_distribution` / `portraits` / `signals` + `evidence`；
5. `POST /api/v1/advisor/chat` → 存 `session_id`，后续每轮带上；
6. 统一按 `error.code` 分支处理：`410` 重新分析、`503` 提示未配置模型、`403` 提示重新分析（client_id 不匹配）。
