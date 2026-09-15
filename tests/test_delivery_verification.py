from pathlib import Path
import hashlib
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "publishing-wechat-articles" / "scripts"))

from wechat_pipeline.oss import OssClient, OssError
from wechat_pipeline.feishu import FeishuClient, FeishuError
from wechat_pipeline.publish import Publisher, PublishError
from wechat_pipeline.manifest import RunManifest
from wechat_pipeline.models import Stage


class DeliveryVerificationTest(unittest.TestCase):
    def test_public_get_compares_bytes_and_checks_all_images(self):
        html = b'<img src="/a.png"><img src="https://assets.example/b.png">'
        calls = []
        def transport(request, timeout):
            calls.append((request.get_method(), request.full_url))
            if request.full_url.endswith("article.html"):
                return 200, {"content-type": "text/html", "content-disposition": "attachment"}, html
            return 200, {"content-type": "image/png"}, b"image"
        client = OssClient("bucket", "example", "test", "test", transport=transport)
        with patch("wechat_pipeline.oss.validate_public_url", side_effect=lambda value: value):
            self.assertTrue(hasattr(client, "verify_artifact"), "byte-level verification is required")
            receipt = client.verify_artifact("https://objects.example/article.html", "text/html", html)
            self.assertEqual(receipt["sha256"], hashlib.sha256(html).hexdigest())
            self.assertEqual(len(receipt["images"]), 2)
            self.assertEqual(receipt["browser_preview"], "not-claimed")
            self.assertEqual(receipt["content_disposition"], "attachment")
            self.assertTrue(all(method == "GET" for method, _ in calls))
            with self.assertRaisesRegex(OssError, "bytes"):
                client.verify_artifact("https://objects.example/article.html", "text/html", b"changed")


    def _feishu(self, transport):
        account = SimpleNamespace(chat_id="chat-test", base_token="base-test", table_id="table-test")
        runtime = SimpleNamespace(accounts={"tech": account}, primary_chat_id="", tech_app_id="app-test", tech_app_secret="secret-test")
        client = FeishuClient(SimpleNamespace(runtime=runtime), transport=transport)
        client._tokens["tech"] = "token-test"
        return client

    def test_tracking_schema_is_read_before_write_and_types_checked(self):
        calls = []
        fields = {"标题": "Title", "摘要": "Summary", "内容": "https://objects.example/article.html", "封面": "https://objects.example/cover.png", "是否已发布": False}
        schema = [{"field_name": name, "type": 7 if name == "是否已发布" else 1} for name in fields]
        def transport(request, timeout):
            calls.append(request)
            data = {"items": schema, "has_more": False} if request.get_method() == "GET" else {"record": {"record_id": "rec-test"}}
            return 200, {}, json.dumps({"code": 0, "data": data}).encode()
        client = self._feishu(transport)
        self.assertEqual(client.create_tracking("tech", fields), "rec-test")
        self.assertEqual([r.get_method() for r in calls], ["GET", "POST"])
        schema[0]["type"] = 7
        calls.clear()
        with self.assertRaises(FeishuError):
            client.create_tracking("tech", fields)
        self.assertEqual([r.get_method() for r in calls], ["GET"])
        fields["是否已发布"] = "false"
        with self.assertRaises(FeishuError):
            client.create_tracking("tech", fields)


    def test_message_and_record_readback_require_exact_ids_and_values(self):
        text = "标题：Title\n摘要：Summary\n封面：https://objects.example/cover.png\nHTML：https://objects.example/article.html"
        message = {"message_id": "msg-test", "chat_id": "chat-test", "msg_type": "text", "body": {"content": json.dumps({"text": text})}}
        fields = {"标题": "Title", "摘要": "Summary", "内容": "https://objects.example/article.html", "封面": "https://objects.example/cover.png", "是否已发布": False}
        record = {"record_id": "rec-test", "fields": dict(fields)}
        calls = []
        def transport(request, timeout):
            calls.append(request)
            data = {"items": [message]} if "/messages/" in request.full_url else {"record": record}
            return 200, {}, json.dumps({"code": 0, "data": data}).encode()
        client = self._feishu(transport)
        self.assertTrue(hasattr(client, "verify_handoff"), "message readback is required")
        self.assertTrue(client.verify_handoff("tech", "msg-test", "Title", "Summary", fields["封面"], fields["内容"])["verified"])
        self.assertTrue(client.verify_tracking("tech", "rec-test", fields)["verified"])
        message["body"]["content"] = json.dumps({"text": text + "\nextra"})
        with self.assertRaises(FeishuError):
            client.verify_handoff("tech", "msg-test", "Title", "Summary", fields["封面"], fields["内容"])
        record["fields"]["是否已发布"] = 0
        with self.assertRaises(FeishuError):
            client.verify_tracking("tech", "rec-test", fields)
        self.assertTrue(all(r.get_method() == "GET" for r in calls))


    def _run(self, root, run_id="run-one"):
        run_dir = root / run_id
        run_dir.mkdir()
        (run_dir / "article.html").write_bytes(b"<h2>article</h2>")
        (run_dir / "cover.png").write_bytes(b"cover")
        manifest = RunManifest.create(run_id, "publish", "tech", "Title", "Summary")
        manifest.state = Stage.RENDERED
        manifest.record_artifact("article_html", run_dir / "article.html", run_dir)
        manifest.record_artifact("cover_png", run_dir / "cover.png", run_dir)
        path = run_dir / "manifest.json"
        manifest.save(path)
        return path

    def _adapters(self, manifest_path, fail_message=False, fail_record=False):
        from tests.test_publish import FakeOss, FakeFeishu
        class VerifiedOss(FakeOss):
            def verify_artifact(self, url, expected, data):
                return {"verified": True, "sha256": hashlib.sha256(data).hexdigest(), "images": [], "browser_preview": "not-claimed"}
        class VerifiedFeishu(FakeFeishu):
            def destination_key(self, account):
                return "same-chat"
            def verify_handoff(self, account, message_id, *args):
                saved = RunManifest.load(manifest_path)
                if saved.external.get("message_id") != message_id:
                    raise AssertionError("ID must be checkpointed before readback")
                if fail_message:
                    raise FeishuError("message readback mismatch")
                return {"verified": True, "message_id": message_id}
            def verify_tracking(self, account, record_id, fields):
                saved = RunManifest.load(manifest_path)
                if saved.external.get("record_id") != record_id:
                    raise AssertionError("ID must be checkpointed before readback")
                if fail_record:
                    raise FeishuError("record readback mismatch")
                return {"verified": True, "record_id": record_id}
        return VerifiedOss(), VerifiedFeishu()

    def test_publisher_checkpoints_ids_then_persists_readback_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._run(Path(tmp))
            oss, feishu = self._adapters(path)
            result = Publisher(oss, feishu).publish(path)
            self.assertTrue(result.external.get("handoff_verification", {}).get("verified"), "handoff must be read back")
            self.assertTrue(result.external["tracking_verification"]["verified"])
            self.assertEqual(result.external["delivery"]["status"], "pending-downstream")
            self.assertNotEqual(result.state, Stage.PUBLISHED)
            self.assertEqual(len(feishu.messages), 1)
            self.assertEqual(len(feishu.records), 1)


    def test_serial_queue_survives_restart_until_exact_draft_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = self._run(root), self._run(root, "run-two")
            oss, feishu = self._adapters(first)
            Publisher(oss, feishu).publish(first)
            next_oss, next_feishu = self._adapters(second)
            with self.assertRaisesRegex(PublishError, "unresolved"):
                Publisher(next_oss, next_feishu).publish(second)
            self.assertEqual(next_feishu.messages, [])
            self.assertEqual(next_oss.calls, [])
            publisher = Publisher(oss, feishu)
            confirmation = {"kind": "wechat-draft", "title": "Wrong", "draft_id": "draft-test", "message_id": "message-1", "confirmed_by": "publishing-assistant", "evidence": "Exact draft readback"}
            with self.assertRaises(PublishError):
                publisher.confirm_downstream(first, confirmation)
            confirmation["title"] = "Title"
            draft = publisher.confirm_downstream(first, confirmation)
            self.assertEqual(draft.state, Stage.RECORDED)
            self.assertEqual(draft.external["delivery"]["status"], "draft-confirmed")
            # An ordinary resume must not erase the downstream confirmation.
            publisher.publish(first)
            self.assertEqual(RunManifest.load(first).external["delivery"]["status"], "draft-confirmed")
            result = Publisher(next_oss, next_feishu).publish(second)
            self.assertEqual(result.state, Stage.RECORDED)
            self.assertEqual(len(next_feishu.messages), 1)


if __name__ == "__main__":
    unittest.main()
