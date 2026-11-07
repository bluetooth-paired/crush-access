import argparse
import codecs
import json
import tempfile
from pathlib import Path

from .adapter import export_json, export_markdown, normalize_messages, parse_wechat_history


_MAX_INPUT_BYTES = 16 * 1024 * 1024


def _read_history(path: Path) -> object:
    with path.open("rb") as source:
        data = source.read(_MAX_INPUT_BYTES + 1)
    if len(data) > _MAX_INPUT_BYTES:
        raise ValueError("The history export exceeds 16 MiB. Request a smaller page from wechat-cli.")
    encoding = "utf-16" if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)) else "utf-8-sig"
    try:
        return json.loads(data.decode(encoding))
    except (ValueError, RecursionError):
        raise ValueError("Expected valid history JSON in UTF-8 or BOM-marked UTF-16.") from None


def _export_pair(conversation: dict, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise ValueError("The output directory already exists. Choose a new directory.")
    with tempfile.TemporaryDirectory(prefix=".chat-export-", dir=destination.parent) as folder:
        staged = Path(folder) / "export"
        staged.mkdir()
        export_json(conversation, staged / "chat.json")
        export_markdown(conversation, staged / "chat.md")
        staged.rename(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert one wechat-cli JSON history to JSON and Markdown.")
    parser.add_argument("history", type=Path, help="Input file from wechat-cli history --format json.")
    parser.add_argument("--output-dir", required=True, type=Path, help="New folder for the two exports.")
    parser.add_argument("--self-label", action="append", default=[], help="Opt in to matching this self display name; repeatable.")
    parser.add_argument("--other-label", action="append", default=[], help="Opt in to matching this peer display name; repeatable.")
    parser.add_argument("--include-sender-names", action="store_true", help="Keep explicitly matched display names as sender_name.")
    parser.add_argument("--utc-offset", help="Known source timezone offset, e.g. +08:00.")
    parser.add_argument("--start-time", help="Inclusive source-local date or minute, e.g. 2026-11-07T10:30.")
    parser.add_argument("--end-time", help="Inclusive source-local date or minute.")
    parser.add_argument("--limit", type=int, help="Keep at most this many messages in source order after filtering.")
    parser.add_argument("--exclude-id", action="append", default=[], help="Exclude an exact message ID; repeatable.")
    args = parser.parse_args()
    try:
        conversation = normalize_messages(
            parse_wechat_history(_read_history(args.history)),
            self_labels=args.self_label,
            other_labels=args.other_label,
            utc_offset=args.utc_offset,
            include_sender_names=args.include_sender_names,
            start_time=args.start_time,
            end_time=args.end_time,
            limit=args.limit,
            exclude_ids=args.exclude_id,
        )
        _export_pair(conversation, args.output_dir)
    except ValueError as error:
        parser.exit(2, f"Error: {error}\n")
    except OSError:
        parser.exit(2, "Error: could not read the history or write exports. Check paths and permissions.\n")
    print(f"Wrote chat.json and chat.md ({conversation['metadata']['total_messages']} messages).")


if __name__ == "__main__":
    main()
