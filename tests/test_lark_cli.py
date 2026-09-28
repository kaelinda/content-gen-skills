import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "publishing-wechat-articles" / "scripts"))

from wechat_pipeline.feishu import FeishuError
from wechat_pipeline.lark_cli import LarkCliFeishuClient


class LarkCliTest(unittest.TestCase):
    def client(self):
        account = SimpleNamespace(chat_id=LarkCliFeishuClient.HANDOFF_CHAT_ID,
                                  base_token="base", table_id="table")
        runtime = SimpleNamespace(accounts={"tech": account}, primary_chat_id="")
        return LarkCliFeishuClient(SimpleNamespace(runtime=runtime))

    def test_user_markdown_send_uses_one_deterministic_key(self):
        client = self.client()
        calls = []
        def fake_run(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0, stdout=json.dumps({"ok": True, "data": {"message_id": "om_test"}}), stderr="")
        with patch("wechat_pipeline.lark_cli.subprocess.run", side_effect=fake_run):
            first = client.send_handoff("tech", "标题", "摘要", "https://example.com/cover.png", "https://example.com/article.html")
            second = client.send_handoff("tech", "标题", "摘要", "https://example.com/cover.png", "https://example.com/article.html")
        self.assertEqual((first, second), ("om_test", "om_test"))
        self.assertEqual(calls[0][0], calls[1][0])
        args = calls[0][0]
        self.assertEqual(args[:3], ["lark-cli", "im", "+messages-send"])
        self.assertEqual(args[args.index("--as") + 1], "user")
        self.assertEqual(len(args[args.index("--idempotency-key") + 1]), 32)
        self.assertIn("Ctrl+A", args[args.index("--markdown") + 1])
        self.assertEqual(calls[0][1]["env"]["LARK_CLI_NO_PROXY"], "1")

    def test_api_error_on_stderr_is_reported(self):
        client = self.client()
        error = {"ok": False, "error": {"code": 99992402, "message": "field validation failed"}}
        with patch("wechat_pipeline.lark_cli.subprocess.run", return_value=SimpleNamespace(
                returncode=1, stdout="", stderr=json.dumps(error))):
            with self.assertRaisesRegex(FeishuError, "99992402"):
                client.send_handoff("tech", "标题", "摘要", "https://example.com/c", "https://example.com/h")

    def test_readback_requires_user_sender_and_all_links(self):
        client = self.client()
        title, summary = "标题", "摘要"
        cover, html = "https://example.com/c", "https://example.com/h"
        body = {"content_v2": [[{"tag": "md", "text": client.handoff_text(title, summary, cover, html)}]]}
        item = {"message_id": "om_test", "chat_id": client.HANDOFF_CHAT_ID,
                "sender": {"sender_type": "user"}, "body": {"content": json.dumps(body)}}
        with patch.object(client, "_request_json", return_value={"data": {"items": [item]}}):
            self.assertTrue(client.verify_handoff("tech", "om_test", title, summary, cover, html)["verified"])
            item["sender"]["sender_type"] = "app"
            with self.assertRaises(FeishuError):
                client.verify_handoff("tech", "om_test", title, summary, cover, html)

    def test_history_normalizes_lark_blank_lines_and_receipt_requires_later_reply(self):
        client = self.client()
        title, summary = "标题", "摘要"
        cover, html = "https://example.com/c", "https://example.com/h"
        expected = client.handoff_text(title, summary, cover, html)
        handoff = {"message_id": "om_user", "chat_id": client.HANDOFF_CHAT_ID,
                   "create_time": "100", "sender": {"sender_type": "user"},
                   "body": {"content": json.dumps({"content_v2": [[{"text": expected.replace("\n\n", "\n\u200b\n")}]]})}}
        reply = {"message_id": "om_reply", "chat_id": client.HANDOFF_CHAT_ID,
                 "create_time": "200", "sender": {"sender_type": "app"},
                 "body": {"content": json.dumps({"content_v2": [[{"text": f"{title} 草稿ID：draft-1"}]]})}}
        def read(url, body, *, token):
            if url.endswith("om_user"):
                return {"data": {"items": [handoff]}}
            if url.endswith("om_reply"):
                return {"data": {"items": [reply]}}
            return {"data": {"items": [reply, handoff], "has_more": False}}
        with patch.object(client, "_request_json", side_effect=read):
            result = client.inspect_handoff_history("tech", expected, since_ms=0)
            self.assertEqual(result["message_id"], "om_user")
            self.assertTrue(client.verify_draft_receipt("tech", "om_reply", "om_user", title, "draft-1")["verified"])
            reply["create_time"] = "50"
            with self.assertRaises(FeishuError):
                client.verify_draft_receipt("tech", "om_reply", "om_user", title, "draft-1")


if __name__ == "__main__":
    unittest.main()
