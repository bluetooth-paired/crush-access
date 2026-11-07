import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_HISTORY_LINE = re.compile(r"\A\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2})\] ")
_UTC_OFFSET = re.compile(r"([+-])([01][0-9]|2[0-3]):([0-5][0-9])")
_DATE = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
_MINUTE = _DATE + r"[T ][0-9]{2}:[0-9]{2}"
_SOURCE_TIMESTAMP = re.compile(
    _MINUTE + r"(?::[0-9]{2}(?:\.([0-9]{1,6}))?)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])?"
)
_SPEAKER_NAMES = {"self": "我", "other": "对方", "unknown": "未知"}
_MARKDOWN_SYNTAX = re.compile(r"[\\`~<>&#*_\[\]|$]|https?://|^(?: {4}|\t|[+\-=]|[0-9]+[.)] )", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class SourceMessage:
    id: str
    timestamp: str
    sender: str
    type: str
    content: str
    sender_name: str | None


@dataclass(frozen=True, slots=True)
class HistoryExport:
    messages: tuple[str | SourceMessage, ...]
    message_type: str


def _source_datetime(value: str) -> datetime:
    match = _SOURCE_TIMESTAMP.fullmatch(value)
    if not match:
        raise ValueError("Invalid source timestamp.")
    iso = value[:-1] + "+00:00" if value.endswith("Z") else value
    if match[1]:
        start, end = match.span(1)
        iso = iso[:start] + match[1].ljust(6, "0") + iso[end:]
    return datetime.fromisoformat(iso)


def _read_source_message(row: dict, index: int) -> SourceMessage:
    fields = ("id", "timestamp", "sender", "type", "content")
    if any(not isinstance(row.get(key), str) for key in fields):
        raise ValueError(f"Structured message {index} must have string id, timestamp, sender, type and content.")
    if not row["id"].strip() or not row["type"].strip():
        raise ValueError(f"Structured message {index} has an empty ID or type.")
    try:
        _source_datetime(row["timestamp"])
    except ValueError:
        raise ValueError(f"Structured message {index} has an invalid timestamp.") from None
    name = row.get("sender_name")
    if name is not None and (not isinstance(name, str) or not name.strip() or "\n" in name or "\r" in name):
        raise ValueError(f"Structured message {index} has an invalid sender name.")
    sender = row["sender"] if row["sender"] in _SPEAKER_NAMES else "unknown"
    return SourceMessage(row["id"], row["timestamp"], sender, row["type"], row["content"], name)


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
    if not isinstance(messages, list):
        raise ValueError("The history messages field must be an array.")
    count = raw_data.get("count")
    if type(count) is not int or count != len(messages):
        raise ValueError("The history count does not match the number of messages.")

    message_type = raw_data.get("type")
    if message_type is not None and (not isinstance(message_type, str) or not message_type.strip()):
        raise ValueError("The history type field must be a non-empty string or null.")
    # Upstream's link filter includes all subtype 49 records, including files.
    if message_type == "link":
        message_type = "link_or_file"
    if all(isinstance(line, str) for line in messages):
        return HistoryExport(tuple(messages), message_type or "unknown")
    if not all(isinstance(row, dict) for row in messages):
        raise ValueError("The history messages must all be strings or all be structured objects.")
    structured = tuple(_read_source_message(row, index) for index, row in enumerate(messages, 1))
    if len({row.id for row in structured}) != len(structured):
        raise ValueError("Structured message IDs must be unique.")
    return HistoryExport(structured, message_type or "unknown")


def _parse_offset(value: str | None) -> timezone | None:
    if value is None:
        return None
    match = _UTC_OFFSET.fullmatch(value)
    if not match:
        raise ValueError("The UTC offset must use +HH:MM or -HH:MM.")
    sign, hours, minutes = match.groups()
    offset = timedelta(hours=int(hours), minutes=int(minutes))
    return timezone(-offset if sign == "-" else offset)


def _sender_prefixes(self_labels: Sequence[str], other_labels: Sequence[str]) -> tuple[tuple[str, str, str], ...]:
    prefixes = []
    for sender, labels in (("self", self_labels), ("other", other_labels)):
        if isinstance(labels, str):
            raise ValueError("Sender labels must be passed as a sequence of names.")
        for label in labels:
            if not isinstance(label, str) or not label.strip() or "\n" in label or "\r" in label:
                raise ValueError("Each sender label must be a non-empty single line.")
            prefixes.append((label + ": ", sender, label))
    return tuple(dict.fromkeys(prefixes))


def _normalize_line(line: str, index: int, message_type: str, prefixes: tuple[tuple[str, str, str], ...],
                    source_timezone: timezone | None, include_sender_names: bool) -> dict[str, str]:
    header = _HISTORY_LINE.match(line)
    if not header:
        raise ValueError(f"Message {index} has no recognized wechat-cli timestamp.")
    try:
        date = datetime.strptime(header[1], "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError(f"Message {index} has an invalid timestamp.") from None

    content = line[header.end():]
    matches = [(prefix, role, label) for prefix, role, label in prefixes if content.startswith(prefix)]
    sender = "unknown"
    sender_name = None
    if len(matches) == 1:
        prefix, sender, sender_name = matches[0]
        content = content[len(prefix):]

    message = {
        "id": f"m{index:03d}",
        "timestamp": date.replace(tzinfo=source_timezone).isoformat(timespec="minutes"),
        "sender": sender,
        "type": message_type,
        "content": content,
    }
    if include_sender_names and sender_name is not None:
        message["sender_name"] = sender_name
    return message


def _normalize_source(row: SourceMessage, utc_offset: str | None, include_sender_names: bool) -> dict[str, str]:
    timestamp = row.timestamp
    if utc_offset and _source_datetime(timestamp).tzinfo is None:
        timestamp += utc_offset
    message = {"id": row.id, "timestamp": timestamp, "sender": row.sender, "type": row.type, "content": row.content}
    if include_sender_names and row.sender_name:
        message["sender_name"] = row.sender_name
    return message


def _time_bound(value: str | None, *, end: bool = False) -> datetime | None:
    if value is None:
        return None
    if not re.fullmatch(rf"{_DATE}|{_MINUTE}", value):
        raise ValueError("Time bounds must use YYYY-MM-DD or YYYY-MM-DDTHH:MM without a timezone.")
    try:
        bound = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("Invalid time bound.") from None
    if end and len(value) == 10:
        bound = bound.replace(hour=23, minute=59)
    return bound.replace(second=59, microsecond=999999) if end else bound


def _select_messages(messages: list[dict[str, str]], start_time: str | None, end_time: str | None,
                     limit: int | None, exclude_ids: Sequence[str]) -> list[dict[str, str]]:
    start, end = _time_bound(start_time), _time_bound(end_time, end=True)
    if start is not None and end is not None and start > end:
        raise ValueError("The start time must not be after the end time.")
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("The message limit must be a positive integer.")
    if isinstance(exclude_ids, str) or any(not isinstance(value, str) or not value for value in exclude_ids):
        raise ValueError("Excluded IDs must be supplied as a sequence of non-empty strings.")
    excluded = set(exclude_ids)
    if excluded.difference(message["id"] for message in messages):
        raise ValueError("An excluded ID does not exist in this source batch.")
    selected = []
    for message in messages:
        if message["id"] in excluded:
            continue
        if start is not None or end is not None:
            displayed = _source_datetime(message["timestamp"]).replace(tzinfo=None)
            if (start is not None and displayed < start) or (end is not None and displayed > end):
                continue
        selected.append(message)
        if len(selected) == limit:
            break
    return selected


def _precision(messages: list[dict[str, str]]) -> str:
    values = set()
    for message in messages:
        suffix = message["timestamp"][16:]
        if not suffix.startswith(":"):
            values.add("minute")
        else:
            values.add("fractional_second" if suffix[3:4] == "." else "second")
    if len(values) > 1:
        return "mixed"
    return next(iter(values), "minute")


def normalize_messages(history: HistoryExport, *, self_labels: Sequence[str] = (),
                       other_labels: Sequence[str] = (), utc_offset: str | None = None,
                       include_sender_names: bool = False, start_time: str | None = None,
                       end_time: str | None = None, limit: int | None = None,
                       exclude_ids: Sequence[str] = ()) -> dict[str, Any]:
    """Normalize then select rows, keeping message IDs and source order stable."""
    source_timezone = _parse_offset(utc_offset)
    prefixes = _sender_prefixes(self_labels, other_labels)
    messages = [
        _normalize_source(line, utc_offset, include_sender_names) if isinstance(line, SourceMessage)
        else _normalize_line(line, index, history.message_type, prefixes, source_timezone, include_sender_names)
        for index, line in enumerate(history.messages, 1)
    ]
    messages = _select_messages(messages, start_time, end_time, limit, exclude_ids)
    structured = bool(history.messages) and isinstance(history.messages[0], SourceMessage)
    return {
        "schema_version": "1.0",
        "source": "wechat-cli",
        "chat_type": "private",
        "messages": messages,
        "metadata": {
            "total_messages": len(messages),
            "unknown_senders": sum(message["sender"] == "unknown" for message in messages),
            "anonymized": False,
            "id_origin": "upstream" if structured else "export",
            "timestamp_precision": _precision(messages) if structured else "minute",
        },
    }


def export_json(conversation: dict[str, Any], output_path: str | Path) -> None:
    document = json.dumps(conversation, ensure_ascii=False, indent=2, allow_nan=False)
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
