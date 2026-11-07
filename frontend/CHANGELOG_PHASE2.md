# V6 第二阶段整合修改记录

## 保留内容

- 保留 V6 首页、粉白视觉、导航、人物档案、双向画像、互动信号页面布局、子乔军师聊天布局。
- 保留第一阶段两套虚构演示场景、手动模式切换、请求失败提示与重试。
- 未修改文青后端源码；本 ZIP 只交付前端。
- 未把用户私人聊天 JSON 放进项目或测试夹具。

## 本阶段修改

- `api/adapter.js`：按文青 v1 API 契约实现 `buildAnalyzeRequest`、`readAnalyzeResponse`、`buildAdvisorRequest`、`readAdvisorResponse`；映射 metrics、daily distribution、signals、evidence、portraits、relationship assessment、reply、session_id、suggestions 和 boundary_notes。
- `api/client.js`：增加 `/health` GET、`X-Client-Id` 请求头、后端结构化错误码解析、HTTP/网络/超时处理。
- `api/config.js`：启用真实 API 配置入口，Base URL 默认留空；不包含任何密钥。
- `app.js`：生成并保存客户端 ID；接入健康检查、两个真实 API、`analysis_id` / `client_id` / `session_id`、思考强度和联网搜索参数；真实模式只显示后端数据，演示模式继续使用本地 Mock。
- `app.js`：允许 Schema 1.0 时间戳不带时区，保留原始值并提示后端默认 +8 小时解释；保留 `sender_name` 和 `metadata`。
- `app.js`：真实模式画像改为展示后端 `portraits`；互动信号使用后端指标和证据，正确处理 null、比例单位与统计口径。
- `dashboard.js`：扩展真实 API Dashboard 模型，支持 null 指标、后端免责声明、语义识别提示、关系评估和证据。
- `phase1.css`：只增加简易 AI 设置和证据引用样式，没有重新布局现有页面。
- `tests/`：增加无时区虚构样例和真实 API 契约模拟测试。

## 验收状态

- 原有导入回归：12 组通过。
- 第一阶段流程回归：通过。
- API 适配层与多轮流程模拟：通过。
- 新增后端契约浏览器测试：5 项通过。
- 用用户提供的清理版 JSON 在本地浏览器测试：16 条消息解析成功（本人 9、对方 7、未知 0），无未捕获浏览器异常。该私人文件未包含在 ZIP。
- Python/JavaScript 源码语法检查通过。

## 尚未验证

- 未配置实际公网后端 Base URL。
- 未使用真实模型供应商 Key 完成生产环境端到端测试。
- 未验证真实服务器 CORS、自定义域名、HTTPS、数据库持久化及生产部署。
