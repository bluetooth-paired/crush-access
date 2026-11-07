# 接口与上线步骤

## 接口交接

| 请求 | 约定 |
| --- | --- |
| `GET /health` | 检查服务、模型配置和思考强度、联网搜索能力。预览会返回 `provider=local-preview`。 |
| `POST /api/v1/analyze` | 将 Schema 1.0 的文件对象放到 `conversation`，保留消息 ID、原时间戳、发送者和正文。响应中的 `analysis_id` 和 `client_id` 交给军师。 |
| `POST /api/v1/advisor/chat` | 带上同一份报告和客户端标识。首轮无 `session_id`，后续沿用服务返回的会话 ID。 |

字段以 [文青 Agent API](../backend/docs/api.md) 为准。前端映射在 `frontend/api/adapter.js`，请求和错误处理在 `frontend/api/client.js`。文件自身是标准 UTF-8 JSON，`conversation` 包装在提交 API 时添加。

## 公网联调顺序

1. 后端同学确认 HTTPS 托管环境，按 `backend/README.md` 启动正式 Agent。正式启动与模型配置使用后端环境，预览启动器只用于本机。
2. 在托管环境设置模型提供商和服务端密钥，确认 `/health` 返回真实提供商。用虚构 JSON 在后端验证一次报告和军师两轮，记录实际模型、HTTP 状态和超时情况。
3. 只允许预期网页来源访问，配置反向代理的请求体和超时限制。公开接入前确认访问鉴权、速率限制、日志脱敏和存储保留策略。客户端 ID 用于报告归属校验，公共入口仍需决定如何鉴权。
4. 在 `frontend/api/config.js` 配置实际 HTTPS Base URL，在独立网页预览中复测报告、会话、错误提示和本地演示。服务端密钥留在托管环境。
5. 审核通过后再调整 GitHub Pages 发布配置，从第二阶段目录发布。用公开网址重新验收真实模式和离线演示模式。

前端负责人确认页面、模式切换和旧功能回归。后端负责人确认真实模型、CORS、鉴权与存储。导出负责人用本机验证后的适配器生成 Schema 1.0，并用虚构样例交接给团队联调。
