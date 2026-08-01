from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "publishing-wechat-articles"
SCRIPTS = SKILL / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.capture import FetchResponse
from wechat_pipeline.config import load_repository_config
from wechat_pipeline.manifest import RunManifest
from wechat_pipeline.models import Stage
from wechat_pipeline.orchestrator import Pipeline
from wechat_pipeline.publish import Publisher


class FakeOss:
    def __init__(self):
        self.uploads = []

    def upload(self, key, data, content_type):
        self.uploads.append((key, content_type))
        return "https://objects.example/" + key

    def verify(self, url, expected):
        return True


class FakeFeishu:
    def __init__(self):
        self.messages = []
        self.records = []

    def send_handoff(self, *args):
        self.messages.append(args)
        return "message-e2e"

    def create_tracking(self, account, fields):
        self.records.append((account, fields))
        return "record-e2e"


def fake_cover_renderer(html, output):
    output.write_bytes(b"\x89PNG\r\n\x1a\nfixture-cover")
    return output


class EndToEndTest(unittest.TestCase):
    def test_fixture_flow_persists_artifacts_and_exact_side_effects(self):
        source = (FIXTURES / "source.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            pipeline = Pipeline(
                load_repository_config(SKILL),
                workspace,
                cover_renderer=fake_cover_renderer,
            )
            manifest = pipeline.plan(
                "Fixture Article",
                "A local acceptance fixture",
                "tech",
                mode="publish",
                run_id="e2e-run",
            )
            pipeline.capture(
                manifest.run_id,
                "https://93.184.216.34/source",
                fetcher=lambda url, limit: FetchResponse(url, 200, {"content-type": "text/html"}, source),
            )
            run_dir = workspace / "runs" / manifest.run_id
            shutil.copyfile(FIXTURES / "article.md", run_dir / "article.md")

            prepared = pipeline.prepare(manifest.run_id)
            self.assertEqual(prepared.state, Stage.RENDERED)
            self.assertTrue((run_dir / "article.html").is_file())
            self.assertTrue((run_dir / "cover.png").is_file())

            oss, feishu = FakeOss(), FakeFeishu()
            published = Publisher(oss, feishu).publish(run_dir / "manifest.json")
            self.assertEqual(published.state, Stage.RECORDED)
            self.assertEqual(len(oss.uploads), 2)
            self.assertEqual(len(feishu.messages), 1)
            self.assertEqual(len(feishu.records), 1)
            self.assertIs(feishu.records[0][1]["是否已发布"], False)

            reloaded = RunManifest.load(run_dir / "manifest.json")
            self.assertEqual(reloaded.external["message_id"], "message-e2e")
            self.assertEqual(reloaded.external["record_id"], "record-e2e")
            for artifact in reloaded.artifacts.values():
                self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
