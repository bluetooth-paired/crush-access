# V6 修订版运行与部署

## 在本机打开

安装 Node.js 22 或更新版本。在解压后的目录打开 PowerShell，运行以下命令。

```powershell
node server/server.mjs
```

浏览器打开 http://127.0.0.1:8787/。档案、导入和本地互动报告可以直接使用。要试用 DeepSeek，请先停止服务，然后在同一个 PowerShell 窗口执行以下命令。

```powershell
$env:DEEPSEEK_API_KEY = Read-Host 'DeepSeek API Key' -MaskInput
node server/server.mjs
```

打开 http://127.0.0.1:8787/#advisor。密钥存在时页面会显示模型配置就绪，首次成功回复后才能确认模型可用。密钥只由后端读取。

## 发布到 GitHub Pages

原工作流继续发布 `docs/`。`server/` 需单独托管在 HTTPS 后端。发布前按 [服务端说明](server/README.md) 设置密钥、访问令牌和前端来源。把 `docs/index.html` 的 `advisor-api-base` 填成 HTTPS 后端地址。用户在军师页面输入的是这个后端发放的应用访问令牌。

## 验收

- 在三段人物档案输入昵称、选年龄段和编辑长文本，确认焦点、滚动位置及步骤切换后的值。
- 用虚构资料测试 CSV 和 wechat-cli 导出的 JSON、Markdown。加载示例报告后返回导入页，原草稿应保留。
- 直接打开军师页，刷新后仍停留在该页，会话从空状态开始。发送测试问题后查看模型回复及错误提示。
