from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "publishing-wechat-articles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.manifest import RunManifest
from wechat_pipeline.models import Stage
from wechat_pipeline.publish import AmbiguousExternalError, Publisher, PublishError


class FakeOss:
    def __init__(self):
        self.calls = []

    def upload(self, key, data, content_type):
        self.calls.append((key, data, content_type))
        return "https://objects.example/" + key

    def verify(self, url, expected):
        return True


class FakeFeishu:
    def __init__(self, fail_record_once=False, ambiguous_message=False):
        self.messages = []
        self.records = []
        self.fail_record_once = fail_record_once
        self.ambiguous_message = ambiguous_message

    def send_handoff(self, account, title, summary, cover_url, html_url):
        self.messages.append((account, title, summary, cover_url, html_url))
        if self.ambiguous_message:
            raise AmbiguousExternalError("message timeout")
        return "message-1"

    def create_tracking(self, account, fields):
        self.records.append((account, fields))
        if self.fail_record_once:
            self.fail_record_once = False
            raise RuntimeError("temporary record failure")
        return "record-1"

    @staticmethod
    def handoff_text(title, summary, cover_url, html_url):
        return f"标题：{title}\n摘要：{summary}\n封面：{cover_url}\nHTML：{html_url}"

    def inspect_handoff_history(self, account, expected_text, *, since_ms):
        return {"found": False, "covered_since": True, "scanned": 3}


class PublishTest(unittest.TestCase):
    def _prepared_run(self, root: Path) -> Path:
        run_dir = root / "run-publish"
        run_dir.mkdir()
        (run_dir / "article.html").write_bytes(b"<h2>article</h2>")
        (run_dir / "cover.png").write_bytes(b"\x89PNG\r\n\x1a\ncover")
        manifest = RunManifest.create("run-publish", "publish", "tech", "Title", "Summary")
        manifest.state = Stage.RENDERED
        manifest.record_artifact("article_html", run_dir / "article.html", run_dir)
        manifest.record_artifact("cover_png", run_dir / "cover.png", run_dir)
        manifest.save(run_dir / "manifest.json")
        return run_dir

    def test_hash_keys_one_handoff_and_boolean_tracking(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._prepared_run(Path(tmp))
            oss, feishu = FakeOss(), FakeFeishu()
            result = Publisher(oss, feishu).publish(run_dir / "manifest.json")

            self.assertEqual(result.state, Stage.RECORDED)
            self.assertEqual(len(oss.calls), 2)
            html_hash = hashlib.sha256(b"<h2>article</h2>").hexdigest()[:16]
            self.assertIn(html_hash, oss.calls[1][0])
            self.assertEqual(len(feishu.messages), 1)
            self.assertEqual(len(feishu.records), 1)
            self.assertIs(feishu.records[0][1]["是否已发布"], False)

    def test_resume_does_not_repeat_completed_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._prepared_run(Path(tmp))
            oss, feishu = FakeOss(), FakeFeishu(fail_record_once=True)
            publisher = Publisher(oss, feishu)
            with self.assertRaises(RuntimeError):
                publisher.publish(run_dir / "manifest.json")
            self.assertEqual(len(oss.calls), 2)
            self.assertEqual(len(feishu.messages), 1)

            result = publisher.publish(run_dir / "manifest.json")
            self.assertEqual(result.state, Stage.RECORDED)
            self.assertEqual(len(oss.calls), 2)
            self.assertEqual(len(feishu.messages), 1)
            self.assertEqual(len(feishu.records), 2)

    def test_ambiguous_timeout_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._prepared_run(Path(tmp))
            oss, feishu = FakeOss(), FakeFeishu(ambiguous_message=True)
            with self.assertRaises(PublishError):
                Publisher(oss, feishu).publish(run_dir / "manifest.json")
            loaded = RunManifest.load(run_dir / "manifest.json")
            self.assertEqual(loaded.state, Stage.NEEDS_RECONCILE)
            with self.assertRaises(PublishError):
                Publisher(oss, feishu).publish(run_dir / "manifest.json")
            self.assertEqual(len(feishu.messages), 1)

    def test_local_media_uploaded_and_verified_before_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._prepared_run(Path(tmp))
            (run_dir / "figs").mkdir()
            data = b"synthetic image bytes"
            (run_dir / "figs" / "chart.png").write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            key = "wechat/tech/chart-media.png"
            url = "https://objects.example/" + key
            (run_dir / "article.html").write_text(f'<h2>article</h2><img src="{url}">')
            (run_dir / "media.json").write_text(json.dumps({"images": [{"path": "figs/chart.png", "sha256": digest,
                "key": key, "url": url, "content_type": "image/png"}]}))
            manifest = RunManifest.load(run_dir / "manifest.json")
            manifest.record_artifact("article_html", run_dir / "article.html", run_dir)
            manifest.record_artifact("media_manifest", run_dir / "media.json", run_dir)
            manifest.save(run_dir / "manifest.json")

            oss, feishu = FakeOss(), FakeFeishu()
            result = Publisher(oss, feishu).publish(run_dir / "manifest.json")
            self.assertEqual(result.state, Stage.RECORDED)
            self.assertEqual(len(oss.calls), 3)
            self.assertEqual(oss.calls[0], (key, data, "image/png"))
            self.assertEqual(result.external["media"][digest], url)

    def test_reconciled_absent_handoff_can_send_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._prepared_run(Path(tmp))
            manifest = RunManifest.load(run_dir / "manifest.json")
            manifest.state = Stage.NEEDS_RECONCILE
            manifest.external = {
                "cover_url": "https://objects.example/cover.png",
                "html_url": "https://objects.example/article.html",
                "upload_verification": {"cover_url": {"verified": True}, "html_url": {"verified": True}},
                "delivery": {"status": "dispatching"},
            }
            manifest.save(run_dir / "manifest.json")
            oss, feishu = FakeOss(), FakeFeishu()
            publisher = Publisher(oss, feishu)
            reconciled = publisher.reconcile_handoff(run_dir / "manifest.json")
            self.assertEqual(reconciled.state, Stage.UPLOADED)
            self.assertFalse(reconciled.external["handoff_reconciliation"]["found"])
            finished = publisher.publish(run_dir / "manifest.json")
            self.assertEqual(finished.state, Stage.RECORDED)
            self.assertEqual(len(feishu.messages), 1)
            self.assertEqual(len(oss.calls), 0)


if __name__ == "__main__":
    unittest.main()
