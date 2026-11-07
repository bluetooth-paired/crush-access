# 微信聊天导入

导入器使用 Python 3.10 或更高版本的标准库，接收 `wechat-cli history` 的单聊 JSON，输出同一份数据的 `chat.json` 和 `chat.md`。在部分 macOS 或 Linux 环境中，Python 命令是 `python3`。

## 命令行转换已有 JSON

在仓库目录用虚构数据跑一遍：

```powershell
python -m chat_import examples/wechat-history.synthetic.json --output-dir chat-demo --self-label "演示本人" --other-label "演示对方" --include-sender-names
```

`chat-demo` 应是一个新目录，父目录需存在。运行成功后，目录里会有 UTF-8 的 `chat.json` 和 `chat.md`。这份样例有 3 条消息，第 2 条带表情和换行，第 3 条没有可确认的发言者。

需要缩小分析范围时，可以为转换器追加以下选项。也可以组合使用。

| 选项 | 作用 |
| --- | --- |
| `--start-time 2026-11-07T10:30` | 包含起始分钟 |
| `--end-time 2026-11-07` | 包含整个结束日。也可用带时分的值，包含整个结束分钟 |
| `--exclude-id m003` | 按当前原始批次的 ID 排除，可重复指定。ID 不存在时会报错 |
| `--limit 20` | 按原顺序保留筛选后前 20 条 |

先确定每条消息的 ID，再按时间和排除条件筛选，最后应用条数上限。因此编号有空缺是正常的。即使两条记录带不同的 UTC 偏移，时间筛选也使用各自显示的日期和时间。同一批记录可先完整导出查看 ID，再用原始输入生成一个新的筛选目录。筛选结果为空时会生成空导出，Agent 的分析接口要求至少有一条消息。

## 可选来源：从本机微信导出

能够成功初始化 `wechat-cli` 的用户，可以把导出的单聊文件交给转换器。自动提取依赖运行平台与微信版本。开发和联调可先使用虚构样例。

按所用版本的说明初始化。[原项目](https://github.com/huohuoer/wechat-cli/tree/a3789232d4f79bf0b30634d9dadbce71e4acd601)和 [Windows 4.1 适配版](https://github.com/TheRaptors/wechat-cli/tree/6770e1e0c0847e193fb3e3b22e4cd6b93de9aacc)均使用 `init` 和 `history`。Windows 微信 4.1.15.56 已用后者验证了文字消息导出。PyPI 同名包的接口不同。

用 `--limit` 控制条数，用 `--start-time` 和 `--end-time` 选择时间范围。建议使用 `wechat-cli history "对方备注" --type text --limit 200 --format json`，并把标准输出保存到本地文件。输入支持 UTF-8 和带 BOM 的 UTF-16。导出含查询失败、数据格式错误或群聊时，转换器会给出错误。

在 Windows 上用 PowerShell 重定向原始 JSON 时，使用 PowerShell 7.4 或更高版本来保留外部程序输出的字节。也可以在 Python 中捕获程序输出并直接按 UTF-8 保存。转换之前先确认读取命令运行成功。

真实文件和微信工具的密钥配置留在被 Git 忽略的 `private-data` 目录内，或放在仓库之外。公开仓库里只提交源码、文档和虚构样例。

## 数据格式 1.0

`chat.json` 顶层有 `schema_version`、`source`、`chat_type`、`messages` 和 `metadata`。`source` 为 `wechat-cli`，`chat_type` 为 `private`。

| 消息字段 | 约定 |
| --- | --- |
| `id` | 优先保留结构化来源提供的唯一字符串 ID。上游只有文本时生成 `m001` 等批次内编号 |
| `timestamp` | ISO 8601，例如 `2026-11-07T10:30`。保留来源已有的精度和时区。仅当已确认来源偏移时才使用 `--utc-offset=+08:00` 为无偏移记录补上时区 |
| `sender` | `self`、`other` 或 `unknown` |
| `sender_name` | 可选。启用 `--include-sender-names` 时，保留已匹配的标签或结构化来源给出的显示名 |
| `type` | 按来源的筛选条件填写，未筛选时填 `unknown`，保留正文的类型标记。`link` 筛选可能包括文件，填 `link_or_file` |
| `content` | 保留消息正文的标点、空格、换行和表情 |

`metadata` 包含 `total_messages`、`unknown_senders`、`anonymized`、`id_origin` 和 `timestamp_precision`。两项条数按最终消息数组计算。生成编号标记为 `export`，保留来源提供的编号标记为 `upstream`。文本记录的精度为 `minute`，结构化记录可保留秒、小数秒或混合精度。正文仍可能包含个人信息，所以 `anonymized` 为 `false`。

`chat.md` 的标题是「微信聊天记录」，正文按「时间 | 我／对方／未知」分段。带有 Markdown 结构或 HTML 的消息会放在纯文本代码块里，保留字面内容并避免干扰后续消息。两份文件使用同一份标准化数据，保留导出里的消息顺序和重复消息。

`wechat-cli` 的 JSON 记录在格式化时已舍弃秒、时区和可靠的发送方 ID。默认把发送者记作 `unknown`，保留时间后面的全文。明确知道双方在文件中的显示名时，可以用 `--self-label` 和 `--other-label` 启用精确前缀匹配。遇到重名、前缀重叠或无匹配仍标记 `unknown`。正文恰好以匹配前缀开头的无发言者记录存在歧义，使用标签选项后请核对样例结果。

如果可信上游能提供结构化消息，可使用同一个 history 外层，把 `messages` 中的每条记录改为包含字符串 `id`、`timestamp`、`sender`、`type`、`content` 的对象，另可提供 `sender_name`。结构化记录使用显式角色，正文中的昵称和冒号保持原样。同一批不能混用字符串和对象。当前 wechat-cli 的常见 history 输出仍是字符串数组。

`chat.json` 只包含 JSON 文档。原消息中出现的 Python、JSON、代码围栏或开发说明仍是正文，只有明确选中消息 ID 或设置筛选范围时才排除。Markdown 继续将可能干扰排版的正文放入纯文本围栏。

## 后端调用

队友可以在自己的后端直接调用转换函数。`raw_data` 是上游导出的 JSON 对象。

```python
from chat_import import normalize_messages, parse_wechat_history, render_markdown

history = parse_wechat_history(raw_data)
conversation = normalize_messages(history)
markdown = render_markdown(conversation)
```

确认了双方的显示名时，可以向 `normalize_messages` 提供 `self_labels` 和 `other_labels`。知道来源时区时可以提供 `utc_offset`。
命令行中的负偏移使用等号形式，例如 `--utc-offset=-05:00`。

调用文青 Agent 的 `POST /api/v1/analyze` 时，将导出对象包装为请求体 `{"conversation": conversation}`。包装只发生在调用时。Agent 接受可选的 `sender_name`，并能解析有偏移和无偏移的 ISO 时间。此版本 Agent 在计算统计时把无偏移时间按 UTC 解释，适配器不会据此改写原始时间。

## 验证

```powershell
python -m unittest discover -s tests -v
```

适配依据为 `wechat-cli` 的 [history JSON 输出](https://github.com/huohuoer/wechat-cli/blob/a3789232d4f79bf0b30634d9dadbce71e4acd601/wechat_cli/commands/history.py#L54-L75) 和[消息格式化代码](https://github.com/huohuoer/wechat-cli/blob/a3789232d4f79bf0b30634d9dadbce71e4acd601/wechat_cli/core/messages.py#L504-L528)。本仓库的示例和测试使用虚构数据。
