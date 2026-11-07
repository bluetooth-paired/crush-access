# 测试报告（2026-11-07）

> 本报告只记录**实际执行过**的验证结果。未执行的部分单独列在「未验证项」中，不根据代码存在推断为通过。

## 1. 自动化测试

```bash
uv run pytest -q
# 134 passed, 2 warnings in 4.65s
```

覆盖范围：

| 测试文件 | 覆盖点 | 结果 |
|---|---|---|
| `tests/test_api.py` | 两个接口的成功/错误分支、字段契约 | 通过 |
| `tests/test_security.py` | 缺失/错误 `client_id`、跨分析读取、未知 `session_id`、header/body 冲突、存储层归属校验 | 通过 |
| `tests/test_env_and_provider.py` | `.env` 优先级、DeepSeek/Kimi 模型推导、`max_tokens` 收敛、缺配置时报错 | 通过 |
| `tests/test_advisor_output.py` | 军师输出 JSON 解析、报告复述抑制、空回复兜底 | 通过 |
| `tests/test_compat.py` | Schema 1.0、无时区时间戳、`sender_name`、`metadata`、`content=null` | 通过 |
| `tests/test_preprocessor.py` / `test_metrics.py` | 时间线归一化、互动指标 | 通过 |
| `tests/test_store.py` / `test_service.py` | 会话归属、TTL、服务编排 | 通过 |

## 2. 全新虚拟环境安装与启动

在独立目录复制项目（不含 `.venv`）后执行：

```bash
uv sync                                   # 成功
PYTHONPATH=src .venv/bin/python -m uvicorn api.app:app --port 8010
curl http://127.0.0.1:8010/health         # 200 {"status":"ok",...}
```

结论：全新虚拟环境安装依赖后可正常启动 FastAPI。系统需要 `libcairo2-dev`、`libdbus-1-dev`、`libgirepository1.0-dev`（仅当平台脚手架依赖需要从源码编译时）。

## 3. 真实链路联调（平台模型网关 `doubao-seed-2-0-pro-260215`）

执行方式：真实 HTTP 请求（非 TestClient），使用虚构数据 `tests/fixtures/fictional_chat.json`。

| 步骤 | 结果 | 备注 |
|---|---|---|
| `POST /api/v1/analyze` | 200，50.2s | `interaction_index=79.7`，12 条 evidence，`ai_config.thinking` 为对象 |
| `POST /api/v1/advisor/chat` 第 1 轮 | 200，11.0s | reply 72 字，`thinking=medium` 实际下发 |
| 第 2 轮（`thinking_level=high` + `web_search=true`） | 200，9.5s | reply 53 字且引用上一轮「摄影展」上下文；搜索真实执行 3 条结果 |
| 第 3 轮（`thinking_level=low`） | 200，4.3s | reply 71 字，`thinking=disabled` 下发 |
| 无 `client_id` 读报告/会话 | 401 `CLIENT_ID_REQUIRED` | 未返回任何报告内容 |
| 错误 `client_id` | 403 `ANALYSIS_FORBIDDEN` | |
| 未知 `session_id` | 404 `ANALYSIS_NOT_FOUND` | 明确报错，不再静默新建会话 |
| 未知 `analysis_id` | 404 `ANALYSIS_NOT_FOUND` | |
| 用 A 报告的 `session_id` 访问 B 报告 | 404 `ANALYSIS_NOT_FOUND` | |

观察到的回复样例（第 2 轮）：

> 你之前提的摄影展她已经爽快答应啦，直接敲定细节就行不用绕弯子。这次见面相处舒服的话，后续约她也不会太难的。

结论：`reply` 为针对当前问题的自然语言建议，没有复述人物画像或整份分析报告。

## 4. 未验证项 / 外部限制

| 项目 | 状态 | 说明 |
|---|---|---|
| DeepSeek / Kimi 真实调用 | **未验证** | 当前环境无对应 API Key。仅通过单元测试验证模型名推导、base_url 选择和 `max_tokens` 收敛逻辑；未做真实外网请求 |
| `thinking_level` on DeepSeek / Kimi | **已知不支持** | 仅平台网关下发 `thinking` / `reasoning_effort`；DeepSeek/Kimi 直连时会明确返回 `supported=false` 与说明，不会伪装成功 |
| `web_search` 脱离平台运行 | **受限** | 依赖 `coze-coding-dev-sdk` 与平台凭据；缺失时 `performed=false` + 明确原因 |
| PostgreSQL 后端 | **未连真实库** | 无 `DATABASE_URL`；内存后端完成真实验证，PostgreSQL 存储代码路径由单元测试覆盖 |
| 多副本会话共享 | **未验证** | 默认 `memory` 后端仅在单进程内有效，重启后会话记忆丢失（需 `STORE_BACKEND=postgres`） |
