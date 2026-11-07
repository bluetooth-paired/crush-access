import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_HISTORY_LINE = re.compile(r"\A\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2})\] ")
_UTC_OFFSET = re.compile(r"([+-])([01][0-9]|2[0-3]):([0-5][0-9])")
_SPEAKER_NAMES = {"self": "我", "other": "对方", "unknown": "未知"}
_MARKDOWN_SYNTAX = re.compile(r"[\\`~<>&#*_\[\]|$]|https?://|^(?: {4}|\t|[+\-=]|[0-9]+[.)] )", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class HistoryExport:
    messages: tuple[str, ...]
    message_type: str


def parse_wechat_history(raw_data: object) -> HistoryExport:
    """Validate the JSON envelope emitted by wechat-cli history."""
    if not isinstance(raw_data, dict):
        raise ValueError("Expected a wechat-cli history JSON object.")
    if raw_data.get("is_group") is not False:
        raise ValueError("Only one-to-one history with is_group=false is supported.")

    failures = raw_data.get("failures")
    if failures is not None and not isinstance(failures, list):
        raise ValueError("The history failures field must be a list or null.")
    if failures:
        raise ValueError(f"wechat-cli reported {len(failures)} failure(s); re-export the history.")

    messages = raw_data.get("messages")
    if not isinstance(messages, list) or not all(isinstance(line, str) for line in messages):
        raise ValueError("The history messages field must be an array of strings.")
    count = raw_data.get("count")
    if type(count) is not int or count != len(messages):
        raise ValueError("The history count does not match the number of messages.")

    message_type = raw_data.get("type")
    if message_type is not None and (not isinstance(message_type, str) or not message_type.strip()):
        raise ValueError("The history type field must be a non-empty string or null.")
    # Upstream's link filter includes all subtype 49 records, including files.
    if message_type == "link":
        message_type = "link_or_file"
    return HistoryExport(tuple(messages), message_type or "unknown")


def _parse_offset(value: str | None) -> timezone | None:
    if value is None:
        return None
    match = _UTC_OFFSET.fullmatch(value)
    if not match:
        raise ValueError("The UTC offset must use +HH:MM or -HH:MM.")
    sign, hours, minutes = match.groups()
    offset = timedelta(hours=int(hours), minutes=int(minutes))
    return timezone(-offset if sign == "-" else offset)


def _sender_prefixes(self_labels: Sequence[str], other_labels: Sequence[str]) -> tuple[tuple[str, str], ...]:
    prefixes = []
    for sender, labels in (("self", self_labels), ("other", other_labels)):
        if isinstance(labels, str):
            raise ValueError("Sender labels must be passed as a sequence of names.")
        for label in labels:
            if not isinstance(label, str) or not label.strip() or "\n" in label or "\r" in label:
                raise ValueError("Each sender label must be a non-empty single line.")
            prefixes.append((label + ": ", sender))
    return tuple(dict.fromkeys(prefixes))


def _normalize_line(line: str, index: int, message_type: str, prefixes: tuple[tuple[str, str], ...],
                    source_timezone: timezone | None) -> dict[str, str]:
    header = _HISTORY_LINE.match(line)
    if not header:
        raise ValueError(f"Message {index} has no recognized wechat-cli timestamp.")
    try:
        date = datetime.strptime(header[1], "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError(f"Message {index} has an invalid timestamp.") from None

    content = line[header.end():]
    matches = [(prefix, role) for prefix, role in prefixes if content.startswith(prefix)]
    sender = "unknown"
    if len(matches) == 1:
        prefix, sender = matches[0]
        content = content[len(prefix):]

    return {
        "id": f"m{index:03d}",
        "timestamp": date.replace(tzinfo=source_timezone).isoformat(timespec="minutes"),
        "sender": sender,
        "type": message_type,
        "content": content,
    }


def normalize_messages(history: HistoryExport, *, self_labels: Sequence[str] = (),
                       other_labels: Sequence[str] = (), utc_offset: str | None = None) -> dict[str, Any]:
    """Preserve the upstream page order and use only explicitly supplied sender labels."""
    source_timezone = _parse_offset(utc_offset)
    prefixes = _sender_prefixes(self_labels, other_labels)
    messages = [
        _normalize_line(line, index, history.message_type, prefixes, source_timezone)
        for index, line in enumerate(history.messages, 1)
    ]
    return {
        "schema_version": "1.0",
        "source": "wechat-cli",
        "chat_type": "private",
        "messages": messages,
        "metadata": {
            "total_messages": len(messages),
            "unknown_senders": sum(message["sender"] == "unknown" for message in messages),
            "anonymized": False,
            "id_origin": "export",
            "timestamp_precision": "minute",
        },
    }


def export_json(conversation: dict[str, Any], output_path: str | Path) -> None:
    document = json.dumps(conversation, ensure_ascii=False, indent=2)
    Path(output_path).write_text(document + "\n", encoding="utf-8", newline="\n")


def _markdown_body(content: str) -> str:
    if not _MARKDOWN_SYNTAX.search(content):
        return content
    longest_run = max((len(run) for run in re.findall(r"`+", content)), default=0)
    fence = "`" * max(3, longest_run + 1)
    return f"{fence}text\n{content}\n{fence}"


def render_markdown(conversation: dict[str, Any]) -> str:
    messages = conversation["messages"]
    header = f"# 微信聊天记录\n\n消息总数：{len(messages)}\n\n---"
    sections = [header]
    for message in messages:
        timestamp = message["timestamp"]
        display_time = timestamp[:16].replace("T", " ") if timestamp else "时间未知"
        sender_name = _SPEAKER_NAMES[message["sender"]]
        sections.append(f"### {display_time} | {sender_name}\n\n{_markdown_body(message['content'])}")
    return "\n\n".join(sections) + "\n"


def export_markdown(conversation: dict[str, Any], output_path: str | Path) -> None:
    Path(output_path).write_text(render_markdown(conversation), encoding="utf-8", newline="\n")
