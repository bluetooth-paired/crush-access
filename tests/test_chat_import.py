import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from chat_import import export_json, export_markdown, normalize_messages, parse_wechat_history


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "wechat-history.synthetic.json"


def history(*messages, **overrides):
    return {
        "is_group": False,
        "count": len(messages),
        "type": "text",
        "messages": list(messages),
        "failures": None,
        **overrides,
    }


class AdapterTests(unittest.TestCase):
    def test_synthetic_history_preserves_content_and_roles(self):
        raw = json.loads(SAMPLE.read_text(encoding="utf-8"))
        result = normalize_messages(
            parse_wechat_history(raw),
            self_labels=("演示本人",),
            other_labels=("演示对方",),
            utc_offset="+08:00",
        )
        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(result["source"], "wechat-cli")
        self.assertEqual(result["chat_type"], "private")
        self.assertEqual(
            result["messages"],
            [
                {"id": "m001", "timestamp": "2026-11-07T10:30+08:00", "sender": "self",
                 "type": "text", "content": "周末有空吗？"},
                {"id": "m002", "timestamp": "2026-11-07T10:32+08:00", "sender": "other",
                 "type": "text", "content": "有呀，怎么啦 😊\n周六下午有空。"},
                {"id": "m003", "timestamp": "2026-11-07T10:34+08:00", "sender": "unknown",
                 "type": "text", "content": "地点：学校北门见。"},
            ],
        )
        self.assertEqual(result["metadata"]["total_messages"], 3)
        self.assertEqual(result["metadata"]["unknown_senders"], 1)
        self.assertEqual(result["metadata"]["id_origin"], "export")
        self.assertEqual(result["metadata"]["timestamp_precision"], "minute")
        self.assertFalse(result["metadata"]["anonymized"])
        self.assertNotIn("synthetic-contact", json.dumps(result))

    def test_no_label_mapping_keeps_whole_message_and_unknown_sender(self):
        parsed = parse_wechat_history(history("[2026-11-07 10:30] Me: this could be the body"))
        message = normalize_messages(parsed)["messages"][0]
        self.assertEqual(message["timestamp"], "2026-11-07T10:30")
        self.assertEqual(message["sender"], "unknown")
        self.assertEqual(message["content"], "Me: this could be the body")

    def test_colon_in_confirmed_label_and_body(self):
        parsed = parse_wechat_history(history("[2026-11-07 10:30] A: class:  Meet at 10:30  \nOK"))
        message = normalize_messages(parsed, other_labels=("A: class",))["messages"][0]
        self.assertEqual(message["sender"], "other")
        self.assertEqual(message["content"], " Meet at 10:30  \nOK")

    def test_ambiguous_prefixes_keep_whole_message(self):
        parsed = parse_wechat_history(history("[2026-11-07 10:30] A: class: Meet"))
        for self_labels in [("A",), ("A: class",)]:
            with self.subTest(self_labels=self_labels):
                message = normalize_messages(
                    parsed, self_labels=self_labels, other_labels=("A: class",)
                )["messages"][0]
                self.assertEqual(message["sender"], "unknown")
                self.assertEqual(message["content"], "A: class: Meet")

    def test_duplicate_same_minute_messages_keep_separate_ids_and_order(self):
        message = "[2026-11-07 10:30] B: Again"
        parsed = parse_wechat_history(history(message, message, "[2026-11-07 10:30] A: OK"))
        rows = normalize_messages(parsed, self_labels=("A",), other_labels=("B",))["messages"]
        self.assertEqual([row["id"] for row in rows], ["m001", "m002", "m003"])
        self.assertEqual([row["content"] for row in rows], ["Again", "Again", "OK"])

    def test_unfiltered_type_does_not_infer_from_body(self):
        parsed = parse_wechat_history(history("[2026-11-07 10:30] [图片]", type=None))
        message = normalize_messages(parsed)["messages"][0]
        self.assertEqual(message["type"], "unknown")
        self.assertEqual(message["content"], "[图片]")

    def test_filter_type_keeps_media_marker(self):
        parsed = parse_wechat_history(history("[2026-11-07 10:30] [图片] (local_id=9)", type="image"))
        message = normalize_messages(parsed)["messages"][0]
        self.assertEqual(message["type"], "image")
        self.assertEqual(message["content"], "[图片] (local_id=9)")

    def test_malformed_envelopes_are_rejected(self):
        for raw in ([], history(is_group=True), history(is_group=None), history(123),
                    history(count=2), history(count=False), history(type=3)):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_wechat_history(raw)

    def test_partial_query_does_not_leak_failure_details(self):
        with self.assertRaisesRegex(ValueError, "reported 1 failure") as raised:
            parse_wechat_history(history(failures=["C:/private/path.db: internal detail"]))
        self.assertNotIn("private", str(raised.exception))

    def test_malformed_message_does_not_echo_body(self):
        for line in ("private content", "[2026-11-32 10:30] private content"):
            with self.subTest(line=line), self.assertRaisesRegex(ValueError, "Message 1") as raised:
                normalize_messages(parse_wechat_history(history(line)))
            self.assertNotIn("private content", str(raised.exception))

    def test_empty_history(self):
        result = normalize_messages(parse_wechat_history(history()))
        self.assertEqual(result["messages"], [])
        self.assertEqual(result["metadata"]["total_messages"], 0)

    def test_invalid_offset_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "offset"):
            normalize_messages(parse_wechat_history(history()), utc_offset="+24:01")

    def test_exporters_use_same_content_and_order(self):
        parsed = parse_wechat_history(history("[2026-11-07 10:30] A:  第一行\n第二行 😊",
                                               "[2026-11-07 10:32] B: 下一条"))
        result = normalize_messages(parsed, self_labels=("A",), other_labels=("B",))
        with tempfile.TemporaryDirectory(dir=ROOT, prefix=".test-chat-") as folder:
            json_path = Path(folder) / "chat.json"
            markdown_path = Path(folder) / "chat.md"
            export_json(result, json_path)
            export_markdown(result, markdown_path)
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), result)
            self.assertEqual(markdown_path.read_text(encoding="utf-8"),
                             "# 微信聊天记录\n\n消息总数：2\n\n---\n\n"
                             "### 2026-11-07 10:30 | 我\n\n 第一行\n第二行 😊\n\n"
                             "### 2026-11-07 10:32 | 对方\n\n下一条\n")

    def test_markdown_body_cannot_open_a_fence_or_imitate_a_heading(self):
        body = "````\n### Fake heading\n<script>example</script>"
        parsed = parse_wechat_history(history(f"[2026-11-07 10:30] {body}",
                                               "[2026-11-07 10:32] Next"))
        result = normalize_messages(parsed)
        with tempfile.TemporaryDirectory(dir=ROOT, prefix=".test-chat-") as folder:
            path = Path(folder) / "chat.md"
            export_markdown(result, path)
            self.assertEqual(result["messages"][0]["content"], body)
            self.assertIn(f"`````text\n{body}\n`````\n\n### 2026-11-07 10:32 | 未知\n\nNext\n",
                          path.read_text(encoding="utf-8"))


class CommandTests(unittest.TestCase):
    def run_converter(self, source, destination):
        return subprocess.run(
            [sys.executable, "-m", "chat_import", str(source), "--output-dir", str(destination),
             "--self-label", "演示本人", "--other-label", "演示对方", "--utc-offset", "+08:00"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False, timeout=15,
        )

    def test_command_creates_two_utf8_files_without_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT, prefix=".test-chat-") as folder:
            target = Path(folder) / "export"
            first = self.run_converter(SAMPLE, target)
            self.assertEqual(first.returncode, 0, first.stderr)
            json_file = target / "chat.json"
            markdown_file = target / "chat.md"
            before = json_file.read_bytes(), markdown_file.read_bytes()
            self.assertEqual(json.loads(before[0])["metadata"]["total_messages"], 3)
            self.assertIn("周六下午有空。", before[1].decode("utf-8"))
            second = self.run_converter(SAMPLE, target)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual((json_file.read_bytes(), markdown_file.read_bytes()), before)

    def test_command_supports_legacy_powershell_utf16_with_bom(self):
        with tempfile.TemporaryDirectory(dir=ROOT, prefix=".test-chat-") as folder:
            source = Path(folder) / "history.json"
            source.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-16")
            target = Path(folder) / "export"
            result = self.run_converter(source, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("周末有空吗？", (target / "chat.json").read_text(encoding="utf-8"))

    def test_invalid_json_does_not_leave_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT, prefix=".test-chat-") as folder:
            source = Path(folder) / "invalid.json"
            source.write_text("private chat body", encoding="utf-8")
            target = Path(folder) / "export"
            result = self.run_converter(source, target)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())
            self.assertNotIn("private chat body", result.stderr)
