# 申请查看你的好感度 · V6 第二阶段前后端整合版

本版本以 Auria 的 `heart-signal-v6-phase1` 为前端基线，保留原有 V6 页面、导航、视觉风格和两套离线演示场景；在此基础上接入文青新版 Agent 后端 v1 API。

**当前状态：前端 API 契约适配和浏览器模拟联调已完成；尚未连接实际公网后端。** 要使用真实 AI，必须先部署后端并配置下方 Base URL。Mock/演示模式始终可独立运行。

## 启动前端

解压后进入 `heart-signal-v6/` 目录：

```bash
python -m http.server 8080
```

打开 `http://localhost:8080/`。也可以部署该目录到 GitHub Pages。前端是静态 HTML/CSS/JavaScript，不需要 Node 构建。

## 配置真实后端

先按文青后端 ZIP 的 README 部署 FastAPI 服务，并确认：

- `GET https://你的后端域名/health` 返回 `status: "ok"`；
- 后端使用 HTTPS；
- 后端 CORS 允许你的 GitHub Pages 来源。文青后端默认允许 `https://*.github.io`，自定义域名需通过 `CORS_ALLOW_ORIGINS` 追加；
- 模型 API Key 只配置在后端 `.env`，**绝不能放进前端**。

然后编辑 `api/config.js`：

```js
window.HeartSignalAPIConfig = Object.freeze({
  baseUrl: 'https://你的后端域名',
  timeoutMs: 90000,
  enabled: true
});
```

`baseUrl` 不要带结尾 `/`。本仓库默认留空，避免误连到不存在的服务。没有配置 Base URL 时，真实模式会明确提示，不会发送数据。

切换到「真实 API」后，前端会请求 `/health`，读取思考强度与联网搜索能力。后端未提供某项能力时，前端禁用相应选项或使用服务端默认值，不会假装生效。

## 真实调用流程

1. 导入 `chat.json` Schema 1.0。
2. 用户确认身份映射并明确同意将本次聊天 JSON 发送到配置的后端。
3. 前端调用 `POST /api/v1/analyze`，请求体按文青文档包装为 `conversation`，并带 `client_id`、`profile`、`options`。
4. 前端保存响应的 `analysis_id` 和 `client_id`，使用后端返回的 `metrics`、`daily_distribution`、`portraits`、`signals`、`evidence` 渲染页面。
5. 军师调用 `POST /api/v1/advisor/chat`。首轮 `session_id` 为 `null`，后端返回后保存；后续轮次沿用同一个 `session_id`。对话上下文由后端管理，前端不重复发送历史聊天记录。
6. `client_id` 只保存在浏览器 `localStorage`，用于报告归属校验；聊天 JSON 和模型密钥不会写入 `localStorage`。

详细契约同时收录于本项目 `docs/agent-api-v1.md`；最终以文青后端 ZIP 的 `docs/api.md` 和实际源码为准。

## JSON 导入约定

- 支持 `schema_version: "1.0"`、`source: "wechat-cli"`、`chat_type: "private"`、`messages` 和可选 `metadata`。
- 每条消息保留 `id`、`timestamp`、`sender`、`type`、`content` 和可选 `sender_name`。
- `sender` 只接受 `self` / `other` / `unknown`；不会根据昵称或正文猜测身份。
- 支持带时区时间戳和无时区时间戳，例如 `2026-11-06T22:39`。无时区时间原样保留，前端会提示后端按 `ASSUME_NAIVE_TZ_OFFSET_HOURS`（默认 `+8`）解释；不会自动补造时区或秒数。
- `metadata` 保留在原始 `conversation` 中；统计以 `messages` 实际内容为准。
- 不支持 Markdown 文件导入、微信导出或 OCR；保留 V6 原有文本粘贴和 `.txt` / `.csv` 导入。

## 真实模式与演示模式

- **真实模式**：只使用后端返回的指标和 `reply`；接口失败时显示错误，不会自动退回本地规则。
- **演示模式**：使用两套虚构 Mock 数据和本地预设回复，不调用后端。页面明确标识演示模式。
- 两种模式复用原有 UI。不要把真实聊天内容放进 Mock、测试夹具或公开仓库。

## 指标展示规则

- `participation_balance`、`other_question_ratio`、`shared_activity_ratio`、`positive_tone_ratio` 是 0～1 比例，显示百分数时乘以 100。
- `interaction_index` 是 0～100，不再乘以 100。
- `shared_activity_ratio` 和 `positive_tone_ratio` 的分母是双方全部可分析文本消息；不能标成仅 TA 的占比。
- `other_question_ratio` 是 TA 可分析文本消息中的提问占比。
- `null` 显示为「数据不足」，不伪装成 0%。
- `interaction_index` 的免责声明及语义识别方式提示会展示在页面。

## 测试

需要 Python、Playwright 和 Chromium：

```bash
pip install playwright
python tests/test_import.py
python tests/test_phase1.py
python tests/test_api_adapter.py
python tests/test_backend_contract.py
```

`test_backend_contract.py` 使用完全虚构的 API 响应和虚构 JSON，验证真实请求/响应契约映射、无时区时间戳、`client_id`、双 API、多轮 `session_id`、设置参数、证据和建议渲染。它是**浏览器级模拟联调**，不是公网后端或真实模型的端到端测试。

## 已知限制

- 尚未配置实际后端公网 Base URL，因此本交付不能声称已完成真实模型端到端联调。
- 后端存储有效期、生产鉴权、隐私告知、服务可用性和模型供应商能力由后端部署配置决定。
- GitHub Pages 仅承载静态前端；Agent 后端必须单独部署到支持 HTTPS 的服务环境。
- 真实聊天记录仅用于用户明确授权的本地/后端测试，不随本前端 ZIP 打包。
