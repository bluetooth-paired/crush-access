# 申请查看你的好感度

蓝牙已配队黑客松项目，包含微信聊天导入、双向画像、好感信号分析与 AI 情感军师。

## 运行聊天导入模块

在仓库根目录用 Python 3.10 或更高版本运行虚构样例：

```bash
python -m chat_import examples/wechat-history.synthetic.json --output-dir chat-demo --self-label "演示本人" --other-label "演示对方" --utc-offset +08:00
```

打开 `chat-demo` 查看 `chat.json` 和 `chat.md`。项目仓库中的聊天样例为虚构数据。微信导出方式、字段和队友接入示例见 [微信聊天导入说明](docs/chat-import.md)。
