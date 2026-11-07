# 军师交流后端

需要 Node.js 22 或更新版本。在仓库根目录打开 PowerShell，先在当前窗口设置 DeepSeek 密钥，再启动服务。

```powershell
$env:DEEPSEEK_API_KEY = Read-Host 'DeepSeek API Key' -MaskInput
node server/server.mjs
```

打开 `http://127.0.0.1:8787/#advisor`。服务器同时提供网页和聊天接口。可以用 `DEEPSEEK_MODEL` 切换模型，默认 `deepseek-flash`。`GET /api/status` 显示密钥是否已经配置，首次发送消息才能确认密钥是否有效。

线上使用需要一个独立的 HTTPS 后端。将 `DEEPSEEK_API_KEY` 放入托管平台的密钥配置，将 `HOST` 设为平台要求的监听地址，并在 `ADVISOR_ALLOWED_ORIGIN` 中填写前端的 HTTPS 来源，例如 `https://bluetooth-paired.github.io`。只要对外提供服务，即使由反向代理转发到本机地址，也要配置独立的 `ADVISOR_ACCESS_TOKEN`。它需要 32–256 个 URL 安全字符，由授权使用者在页面中输入。这个口令和 DeepSeek API Key 都应通过托管平台的密钥配置管理。HTTPS 反向代理需保留请求主机名。服务内的请求频率和并发限制按进程计算。

```powershell
node --test server/server.test.mjs
```

测试通过本机地址运行，使用模拟模型回复。线上模型配置参考 [DeepSeek API 文档](https://api-docs.deepseek.com/)。
