# crush-access-agent-backend

「申请查看你的好感度」AI Agent 与后端接口。

单 Agent 架构：**同一个 Agent** 既能在对话中分析聊天记录，也能基于分析报告做情感军师多轮交流。
对外暴露两个后端 API：互动信号分析（API A）与 AI 情感军师（API B）。

- 分析结果**允许**引导，指标**不允许**编造：所有数字由 Python 计算，LLM 只做语义打标与定性判断
- 互动参考指数只是启发式参考，**不是**好感概率
- 军师 `reply` 只回答当前问题（60~200 字），不复述画像/指标/报告
- 可选 AI 配置：思考强度 `low/medium/high`（按端点真实能力映射）、联网搜索（默认关闭，仅用清洗后的用户提问检索）
- 不存真实聊天记录到代码仓库；仓库内测试数据全部为虚构数据

> 完整接口契约（含 chat.json Schema 1.0 输入规范、指标口径、错误码、CORS、AI 配置参数生效范围）见 **`docs/api.md`**。

---

## 目录结构

```
.
├── config/
│   └── agent_llm_config.json        # 模型参数 + Agent 系统提示词
├── docs/
│   ├── api.md                       # 两个 API 的完整联调文档（字段、样例、口径）
│   ├── TEST_REPORT.md               # 实测结果与未验证项（区分已通过/受外部限制）
│   └── schemas/                     # 请求/响应 JSON Schema
├── scripts/
│   ├── run_api.sh                   # 启动独立后端（uvicorn）
│   ├── smoke_test_api.py            # 真实模型端到端冒烟测试
│   └── build_zip.py                 # 打包交付 ZIP
├── src/
│   ├── agents/
│   │   ├── agent.py                 # 唯一 Agent：一个实例、两种模式的系统提示
│   │   ├── service.py               # 统一 Agent 服务：analyze() / advisor_chat()
│   │   ├── advisor.py               # 证据检索 + 军师输出解析
│   │   ├── prompts.py               # 军师系统提示（含输出 JSON 契约）
│   │   └── context.py               # ContextVar：模式与报告上下文
│   ├── analysis/                    # 分析域（确定性为主）
│   │   ├── schema.py                # 输入 Schema 1.0 + 输出数据模型
│   │   ├── preprocessor.py          # 数据质量 + 客观统计
│   │   ├── metrics.py               # 指标公式、每日分布、关键词兜底
│   │   ├── prompts.py               # 分析系统提示 + 用户消息构造
│   │   ├── analyzer.py              # LLM 调用、JSON 容错、重试、校验
│   │   └── service.py               # 编排：校验 → 统计 → LLM → 合并 → 指标
│   ├── api/                         # FastAPI 层
│   │   ├── app.py                   # create_app()：CORS、异常、/health、路由
│   │   ├── routes_analyze.py        # POST /api/v1/analyze
│   │   ├── routes_advisor.py        # POST /api/v1/advisor/chat
│   │   ├── schemas.py               # 请求/响应模型（驱动 OpenAPI）
│   │   ├── transformers.py          # 报告 → 前端绘图结构（portraits）
│   │   ├── errors.py                # 统一错误格式
│   │   └── server.py                # 独立启动入口
│   ├── store/                       # 报告与会话存储（TTL + 归属隔离）
│   ├── llm/provider.py              # 模型凭据解析（环境变量）
│   ├── llm/thinking.py              # 思考强度 → 真实下发参数映射
│   ├── settings.py                  # 全部运行配置
│   ├── tools/                       # Agent 可调用的工具
│   └── main.py                      # 平台运行时入口（已挂载同一套路由）
├── tests/
│   ├── fixtures/fictional_chat.json # 虚构测试聊天数据
│   ├── test_ai_config.py            # 思考强度映射 / 联网搜索隐私 / 兼容性
│   ├── test_api.py                  # 路由/隔离/错误/CORS/OpenAPI
│   ├── test_metrics.py              # 指标公式与边界
│   ├── test_store.py                # 有效期与归属隔离
│   └── ...                          # 其他既有测试
├── .env.example
└── pyproject.toml
```

---

## 快速开始

```bash
# 1. 安装依赖（使用 uv）
uv sync

# 2. 配置模型凭据（二选一）
cp .env.example .env
#  (a) DeepSeek:  DEEPSEEK_API_KEY=sk-xxx
#  (b) Kimi:      MOONSHOT_API_KEY=sk-xxx
#  (c) 任意 OpenAI 兼容: LLM_API_KEY / LLM_BASE_URL / LLM_MODEL

# 3. 启动服务
bash scripts/run_api.sh            # http://127.0.0.1:8000
#    或用 uvicorn 直接启动
PYTHONPATH=src python -m uvicorn api.app:app --port 8000
```

- Swagger UI：`http://127.0.0.1:8000/docs`
- OpenAPI：`http://127.0.0.1:8000/openapi.json`
- 健康检查：`http://127.0.0.1:8000/health`（会返回当前生效的 `provider` / `model` / `thinking_supported` / `web_search`）

> 安装提示：`uv sync` 会带入平台脚手架的 `pycairo` / `dbus-python` / `PyGObject`，在干净的 Debian/Ubuntu 上若失败，先安装：
> `apt-get install -y libcairo2-dev libdbus-1-dev libgirepository1.0-dev`。业务代码本身不依赖这三个包。
>
> `.env` 从**项目根目录**读取（也兼容 `COZE_WORKSPACE_PATH/.env`），已存在的环境变量优先级更高；修改后需重启进程。

### 一次完整调用

```bash
# API A：分析
curl -s -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H 'Content-Type: application/json' \
  -d @- <<'JSON' | python -m json.tool
{
  "conversation": {
    "schema_version": "1.0",
    "source": "wechat-cli",
    "chat_type": "private",
    "messages": [
      {"id": "m001", "timestamp": "2026-11-07T10:30+08:00", "sender": "self", "type": "text", "content": "周末有空吗？"},
      {"id": "m002", "timestamp": "2026-11-07T10:32+08:00", "sender": "other", "type": "text", "content": "有呀！"}
    ]
  }
}
JSON

# API B：军师对话（把上一步的 analysis_id / client_id 填进来）
curl -s -X POST http://127.0.0.1:8000/api/v1/advisor/chat \
  -H 'Content-Type: application/json' \
  -d '{"analysis_id":"<ID>","message":"她这样说是有戏吗？","client_id":"<CLIENT_ID>"}' \
  | python -m json.tool
```

---

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | 空 | 任意 OpenAI 兼容服务（优先级最高）。只填 Key + 已知厂商端点时会自动推导模型名；缺少端点且未指定模型时**直接报错**而不是静默请求 OpenAI 官方 |
| `DEEPSEEK_API_KEY` | 空 | 使用 DeepSeek，base 默认 `https://api.deepseek.com/v1`，模型默认 `deepseek-chat`（可用 `DEEPSEEK_MODEL` 覆盖） |
| `MOONSHOT_API_KEY` | 空 | 使用 Kimi，base 默认 `https://api.moonshot.cn/v1`，模型默认 `kimi-k3`（可用 `MOONSHOT_MODEL` 覆盖，如 `kimi-k2.6`） |
| `COZE_WORKLOAD_IDENTITY_API_KEY` + `COZE_INTEGRATION_MODEL_BASE_URL` | 空 | 部署在本平台时可用，自动作为兜底（使用 `config/agent_llm_config.json` 的模型） |
| `LLM_JSON_MODE` | `true` | 分析节点使用 JSON 模式（`response_format=json_object`），降低解析失败重试 |
| `LLM_MAX_COMPLETION_TOKENS` | 配置值 | 输出上限；会按端点自动收敛（DeepSeek / Kimi 8192，平台 10000） |
| `ASSUME_NAIVE_TZ_OFFSET_HOURS` | `8` | 无时区时间戳按此时区解析（微信导出为本地时间） |
| `ANALYSIS_TTL_SECONDS` | `604800` | 报告有效期（秒） |
| `SESSION_TTL_SECONDS` | `604800` | 军师会话有效期（秒） |
| `STORE_BACKEND` | `memory` | `memory` 或 `postgres` |
| `DATABASE_URL` / `PGDATABASE_URL` | 空 | `postgres` 后端连接串 |
| `CORS_ALLOW_ORIGINS` | 本地开发来源 | 逗号分隔的额外允许来源 |
| `CORS_ALLOW_ORIGIN_REGEX` | `https://([a-zA-Z0-9-]+\.)*github\.io` | 默认放行 GitHub Pages |
| `MAX_MESSAGES_PER_REQUEST` | `3000` | 单次分析消息上限 |
| `LLM_MAX_RETRIES` | `3` | JSON 解析失败时的重试次数 |

**模型凭据只从环境变量读取，源码中没有任何硬编码密钥。**

---

## 测试

```bash
# 单元 + 接口测试（不调用真实模型，使用确定性替身）
PYTHONPATH=src python -m pytest -q

# 真实模型端到端冒烟（会调用真实 API，产生少量费用）
PYTHONPATH=src python scripts/smoke_test_api.py
```

`tests/test_api.py` 用 `FakeAnalyzer` / `FakeAgent` 替代模型调用，其余编排、校验、存储、错误处理全部走真实代码；
真实模型链路只由 `scripts/smoke_test_api.py` 验证，二者结果不会互相冒充。

实测结论见 [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md)，其中明确区分了**已实际执行通过**与**未验证/受外部限制**的部分：

- 已实测：全新虚拟环境安装启动、134 项自动化测试、真实模型 analyze → 3 轮军师对话、`thinking` 三档下发、`web_search` 真实检索、401/403/404 隔离行为
- 未验证：DeepSeek / Kimi 真实外网调用（无 Key）、PostgreSQL 真实库、多副本会话共享


---

## 安全与隐私

1. **归属隔离**：`analysis_id` 为 UUID v4；创建时可绑定 `client_id`，军师接口校验一致性：缺少凭据 401，凭据不匹配 403。
2. **会话归属**：传入的 `session_id` 必须属于当前 `client_id` 的该份报告；未知或跨报告 `session_id` 返回 404，**不会静默新建会话**。
3. **有效期**：报告与会话均带 TTL，过期返回 410，并在读取时惰性清理。
4. **最小化日志**：只打印 `analysis_id` / `session_id` / 消息条数 / 证据数，**不打印聊天正文与密钥**。
5. **防提示注入**：聊天正文被声明为「待分析数据」，其中出现的指令一律不执行。
6. **不落盘原文**：`memory` 后端不写磁盘；`postgres` 后端仅存 JSON 载荷，需自行按需清理。
7. **CORS 不开凭证**：避免与 `*` 通配产生安全隐患。

---

## 已知限制

- `memory` 后端重启后报告失效（生产建议 `STORE_BACKEND=postgres`）；多副本部署必须使用 `postgres`
- 语义打标依赖 LLM；当模型未返回标签时退化为关键词规则，`metrics.semantic_detection.method` 会标记为 `keyword_fallback`
- 目前只接收墨翊 `chat.json` Schema 1.0，不内置微信导出解析器
- 单次分析上限 3000 条消息；超长会话建议先截取时间窗口
- `interaction_index` 为启发式参考，不应作为任何关系结论的因果依据
- 未实现限流与鉴权体系，公网部署建议在网关层追加限流
- 思考强度 `thinking_level` 仅平台网关真实下发；DeepSeek / Kimi 直连会明确返回 `supported=false`（不伪装生效）
- `web_search` 依赖 `coze-coding-dev-sdk` 与平台凭据，脱离平台运行时会返回 `performed=false` 及原因

---

## 部署

```dockerfile
# Dockerfile（推荐：与 README 相同的 uv 安装流程）
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
      libcairo2-dev libdbus-1-dev libgirepository1.0-dev \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["bash", "scripts/run_api.sh"]
```

```bash
docker build -t crush-access-agent .
docker run -p 8000:8000 -e DEEPSEEK_API_KEY=sk-xxx \
  -e CORS_ALLOW_ORIGINS=https://auria.github.io crush-access-agent
```

生产建议：

- `STORE_BACKEND=postgres` + `DATABASE_URL`，保证多副本一致
- 反向代理（Nginx / Caddy）终止 TLS，并追加 IP 限流
- Auria 的 GitHub Pages 已在 CORS 正则白名单内；自定义域名请加 `CORS_ALLOW_ORIGINS`

---

## 平台内运行

本项目同时保留平台运行时入口：

```bash
bash scripts/local_run.sh -m flow                      # 运行工作流
bash scripts/http_run.sh -m http -p 5000              # 启动平台 HTTP 服务
```

平台入口 `src/main.py` 通过 `register_into(app)` 挂载了同一套 `/health`、`/api/v1/analyze`、`/api/v1/advisor/chat` 路由与 CORS 配置，行为与独立服务一致。
