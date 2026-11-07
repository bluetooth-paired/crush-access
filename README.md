# 申请查看你的好感度

蓝牙已配队黑客松项目，包含微信聊天导入、双向画像、好感信号分析与 AI 情感军师。

## 运行聊天导入模块

在仓库根目录用 Python 3.10 或更高版本运行虚构样例：

```bash
python -m chat_import examples/wechat-history.synthetic.json --output-dir chat-demo --self-label "演示本人" --other-label "演示对方" --include-sender-names
```

打开 `chat-demo` 查看纯 JSON 的 `chat.json` 和同批 `chat.md`。用 `--start-time`、`--end-time`、`--limit` 或重复指定 `--exclude-id` 选择要分析的消息。导入器默认保留原正文和时间精度，时区未知时不补偏移。

对接文青 Agent 时，向 `POST /api/v1/analyze` 发送 `{"conversation": <解析后的 chat.json>}`。导出文件自身保留 Schema 1.0 原有顶层。参数细节和接入示例见 [微信聊天导入说明](docs/chat-import.md)。
