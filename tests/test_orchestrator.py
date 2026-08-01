from pathlib import Path
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "publishing-wechat-articles"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.config import load_repository_config
from wechat_pipeline.models import Stage
from wechat_pipeline.orchestrator import Pipeline, PipelineError


class OrchestratorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.config = load_repository_config(SKILL)

    def tearDown(self):
        self.temp.cleanup()

    def test_prepare_requires_editorial_markdown(self):
        pipeline = Pipeline(self.config, self.workspace)
        manifest = pipeline.plan("Title", "Summary", "tech", run_id="run-one")
        with self.assertRaises(PipelineError):
            pipeline.prepare(manifest.run_id, render_png=False)

    def test_prepare_is_local_and_resumes_from_disk(self):
        external_calls = []
        pipeline = Pipeline(self.config, self.workspace, external_hook=external_calls.append)
        manifest = pipeline.plan("Swift Agent 工程化实战：从原型到稳定上线", "Summary", "tech", run_id="run-two")
        run_dir = self.workspace / "runs" / manifest.run_id
        (run_dir / "article.md").write_text(
            "## 从原型到生产\n\nSwift Agent 工程化需要稳定性检查。\n\n## 稳定上线\n\n本文给出从原型到稳定上线的实战路径。\n",
            encoding="utf-8",
        )

        prepared = pipeline.prepare(manifest.run_id, render_png=False)
        self.assertEqual(prepared.state, Stage.RENDERED)
        self.assertEqual(external_calls, [])
        self.assertTrue((run_dir / "article.html").is_file())
        self.assertTrue((run_dir / "cover.html").is_file())
        self.assertTrue((run_dir / "quality.json").is_file())
        self.assertTrue((run_dir / "title-quality.json").is_file())

        restarted = Pipeline(self.config, self.workspace)
        loaded = restarted.status(manifest.run_id)
        self.assertEqual(loaded.state, Stage.RENDERED)
        self.assertEqual(
            set(loaded.artifacts),
            {"article_markdown", "article_html", "cover_html", "quality_report", "title_quality_report"},
        )

    def test_title_gate_runs_before_render_and_retitle_recovers(self):
        cover_calls = []

        def cover_renderer(html, output):
            cover_calls.append(html)
            output.write_bytes(b"\x89PNG\r\n\x1a\ncover")
            return output

        pipeline = Pipeline(self.config, self.workspace, cover_renderer=cover_renderer)
        manifest = pipeline.plan("震惊！99% 的程序员都不知道！！！", "Summary", "tech", run_id="run-title")
        run_dir = self.workspace / "runs" / manifest.run_id
        (run_dir / "article.md").write_text(
            "## Swift Agent 工程化\n\nSwift Agent 从原型走向稳定上线需要完整的工程化检查。\n",
            encoding="utf-8",
        )

        with self.assertRaises(PipelineError):
            pipeline.prepare(manifest.run_id)
        self.assertEqual(cover_calls, [])
        self.assertFalse((run_dir / "article.html").exists())
        self.assertTrue((run_dir / "title-quality.json").is_file())
        self.assertEqual(pipeline.status(manifest.run_id).state, Stage.NEEDS_REVIEW)

        revised = pipeline.retitle(manifest.run_id, "Swift Agent 工程化实战：从原型到稳定上线")
        self.assertEqual(revised.state, Stage.WRITTEN)
        prepared = pipeline.prepare(manifest.run_id)
        self.assertEqual(prepared.state, Stage.RENDERED)
        self.assertEqual(len(cover_calls), 1)


if __name__ == "__main__":
    unittest.main()
