# 第二阶段集成交接

本分支交付可以在本机运行的集成预览。前端来自 `heart-signal-v6-phase2-integrated.zip`，后端来自文青的 `crush-access-agent-backend_f5311dbd(1).zip`。微信导出沿用主分支已合并的 `chat_import/`。现有公开演示页由 `docs/` 发布，第二阶段前端在 `frontend/`。

## 目录

| 路径 | 用途 |
| --- | --- |
| `frontend/` | 网页、静态资源、接口适配、虚构演示和前端测试 |
| `backend/` | 文青 Agent 源码、接口说明、虚构测试和本机预览入口 |
| `chat_import/` | 微信聊天 Schema 1.0 导出器及 Markdown 双格式输出 |
| `preview.mjs` | 在 `127.0.0.1:8789` 提供网页，把三个预览 API 请求转发至 `127.0.0.1:8010` |
| `check-browser.cjs` | 浏览器联调测试 |

## 从本机打开

使用 Python 3.12 和 Node.js。以下命令在项目根目录执行，Windows PowerShell 示例。

```powershell
python -m venv .venv
$py = '.\.venv\Scripts\python.exe'
& $py -m pip install -r backend/requirements-preview.txt
& $py -m pip install --no-deps coze-coding-utils==0.2.8
& $py backend/preview_api.py
```

在第二个窗口运行 `node preview.mjs`，然后打开 http://127.0.0.1:8789/#import。第一窗口运行真实 FastAPI 路由、分析流程和内存会话，但模型输出使用本地模拟。页面会显示「本地集成预览」。

1. 在「聊天导入」选择「真实 API」，等待健康检查通过。
2. 选择 `backend/tests/fixtures/fictional_chat.json`。预览应显示 12 条虚构消息。
3. 确认隐私、双方身份和本次发送授权，点击「确认并提交分析」。
4. 在互动信号页查看报告，再切到军师连续提问两次。回复中的「本地预览」标识表示模型仍是替身。
5. 测试演示模式时，从首页选「查看示例」，进入军师后点一个快捷问题。

接口烟测可另开窗口执行 `& $py backend/smoke_preview.py`，其中 `$py` 为同一个 Python 路径。浏览器回归使用 `node check-browser.cjs`，需要安装 Playwright，并能启动本机 Edge。导出模块回归用 `python -m unittest discover -s tests -v`。

本机依赖清单按已经使用的版本记录，独立新机器的安装与复测仍需交接时完成。

## 后续

- [接口与上线步骤](DEPLOYMENT.md)
- [验收记录与未完成项](VERIFICATION.md)
