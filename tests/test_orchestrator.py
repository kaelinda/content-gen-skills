from pathlib import Path
import hashlib
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
from tests.voice_helpers import valid_brief, valid_review


class OrchestratorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.config = load_repository_config(SKILL)

    def tearDown(self):
        self.temp.cleanup()

    def _plan_voice_run(self, run_id="voice-run"):
        pipeline = Pipeline(self.config, self.workspace)
        manifest = pipeline.plan(
            "Swift Agent 工程化实践：从原型到稳定运行",
            "说明从原型到稳定运行的工程边界。",
            "tech",
            run_id=run_id,
            author_voice=True,
        )
        return pipeline, manifest, self.workspace / "runs" / run_id

    def _ingest_valid_brief(self, pipeline, manifest):
        source = self.workspace / f"{manifest.run_id}-brief.json"
        source.write_text(
            json.dumps(valid_brief(manifest.editorial["profile_sha256"]), ensure_ascii=False),
            encoding="utf-8",
        )
        return pipeline.ingest_brief(manifest.run_id, source)

    def _write_voice_article(self, run_dir):
        article = run_dir / "article.md"
        article.write_text(
            "## Swift Agent 工程化判断\n\n具体正文说明 Swift Agent 从原型到稳定运行的工程边界。\n",
            encoding="utf-8",
        )
        return article

    def _ingest_valid_review(self, pipeline, manifest, article, *, decision="pass"):
        digest = hashlib.sha256(article.read_bytes()).hexdigest()
        payload = valid_review(digest, excerpt="具体正文")
        if decision == "revise":
            payload["decision"] = "revise"
            payload["dimensions"][0]["status"] = "weak"
        source = self.workspace / f"{manifest.run_id}-review.json"
        source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return pipeline.ingest_voice_review(manifest.run_id, source)

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

    def test_author_voice_is_opt_in_per_run(self):
        pipeline = Pipeline(self.config, self.workspace)

        default_run = pipeline.plan("Default", "Summary", "tech", run_id="default-run")
        advanced_run = pipeline.plan(
            "Advanced",
            "Summary",
            "tech",
            run_id="advanced-run",
            author_voice=True,
        )

        self.assertFalse(default_run.requires_voice)
        self.assertNotIn("voice_context", default_run.artifacts)
        self.assertTrue(advanced_run.requires_voice)
        self.assertIn("voice_context", advanced_run.artifacts)
        context_path = self.workspace / "runs" / "advanced-run" / "voice-context.json"
        context = json.loads(context_path.read_text(encoding="utf-8"))
        self.assertEqual(context["profile_sha256"], advanced_run.editorial["profile_sha256"])

    def test_collect_only_rejects_author_voice(self):
        pipeline = Pipeline(self.config, self.workspace)

        with self.assertRaisesRegex(PipelineError, "prepare-only or publish"):
            pipeline.plan(
                "Collection",
                "Summary",
                "tech",
                mode="collect-only",
                run_id="collect-run",
                author_voice=True,
            )

    def test_brief_and_review_ingestion_are_local_and_bound_to_enabled_run(self):
        pipeline = Pipeline(self.config, self.workspace)
        plain = pipeline.plan("Plain", "Summary", "tech", run_id="plain-run")
        plain_input = self.workspace / "plain-brief.json"
        plain_input.write_text(json.dumps(valid_brief(), ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(PipelineError, "not enabled"):
            pipeline.ingest_brief(plain.run_id, plain_input)

        manifest = pipeline.plan(
            "Advanced",
            "Summary",
            "tech",
            run_id="advanced-run",
            author_voice=True,
        )
        brief_input = self.workspace / "brief-input.json"
        brief_input.write_text(
            json.dumps(valid_brief(manifest.editorial["profile_sha256"]), ensure_ascii=False),
            encoding="utf-8",
        )
        briefed = pipeline.ingest_brief(manifest.run_id, brief_input)
        self.assertEqual(briefed.editorial["brief_status"], "ready")
        self.assertIn("author_brief", briefed.artifacts)

        run_dir = self.workspace / "runs" / manifest.run_id
        article = run_dir / "article.md"
        article.write_text("## 判断\n\n具体正文。\n", encoding="utf-8")
        digest = hashlib.sha256(article.read_bytes()).hexdigest()
        review_input = self.workspace / "review-input.json"
        review_input.write_text(
            json.dumps(valid_review(digest, excerpt="具体正文"), ensure_ascii=False),
            encoding="utf-8",
        )
        reviewed = pipeline.ingest_voice_review(manifest.run_id, review_input)
        self.assertEqual(reviewed.editorial["review_status"], "pass")
        self.assertIn("voice_review", reviewed.artifacts)

    def test_enabled_run_requires_brief_before_prepare(self):
        pipeline, manifest, run_dir = self._plan_voice_run()
        self._write_voice_article(run_dir)

        with self.assertRaisesRegex(PipelineError, "author brief"):
            pipeline.prepare(manifest.run_id, render_png=False)

        failed = pipeline.status(manifest.run_id)
        self.assertEqual(failed.state, Stage.NEEDS_REVIEW)
        self.assertFalse((run_dir / "article.html").exists())

    def test_enabled_run_requires_passing_current_review(self):
        pipeline, manifest, run_dir = self._plan_voice_run()
        self._ingest_valid_brief(pipeline, manifest)
        article = self._write_voice_article(run_dir)

        with self.assertRaisesRegex(PipelineError, "voice review"):
            pipeline.prepare(manifest.run_id, render_png=False)

        self._ingest_valid_review(pipeline, manifest, article, decision="revise")
        with self.assertRaisesRegex(PipelineError, "must pass"):
            pipeline.prepare(manifest.run_id, render_png=False)

    def test_enabled_run_prepares_after_valid_brief_and_review(self):
        external_calls = []
        pipeline = Pipeline(self.config, self.workspace, external_hook=external_calls.append)
        manifest = pipeline.plan(
            "Swift Agent 工程化实践：从原型到稳定运行",
            "说明从原型到稳定运行的工程边界。",
            "tech",
            run_id="voice-run",
            author_voice=True,
        )
        run_dir = self.workspace / "runs" / manifest.run_id
        self._ingest_valid_brief(pipeline, manifest)
        article = self._write_voice_article(run_dir)
        self._ingest_valid_review(pipeline, manifest, article)

        prepared = pipeline.prepare(manifest.run_id, render_png=False)

        self.assertEqual(prepared.state, Stage.RENDERED)
        self.assertEqual(external_calls, [])

    def test_article_edit_makes_voice_review_stale(self):
        pipeline, manifest, run_dir = self._plan_voice_run()
        self._ingest_valid_brief(pipeline, manifest)
        article = self._write_voice_article(run_dir)
        self._ingest_valid_review(pipeline, manifest, article)
        article.write_text("## 已修改\n\n这是一份不同的正文。\n", encoding="utf-8")

        with self.assertRaisesRegex(PipelineError, "stale voice review"):
            pipeline.prepare(manifest.run_id, render_png=False)

        failed = pipeline.status(manifest.run_id)
        self.assertEqual(failed.editorial["review_status"], "stale")

    def test_enabled_run_uses_voice_review_instead_of_blocking_generic_phrase(self):
        pipeline, manifest, run_dir = self._plan_voice_run()
        self._ingest_valid_brief(pipeline, manifest)
        article = self._write_voice_article(run_dir)
        article.write_text(
            "## Swift Agent 工程化判断\n\n值得注意的是，具体正文说明 Swift Agent 从原型到稳定运行的工程边界。\n",
            encoding="utf-8",
        )
        self._ingest_valid_review(pipeline, manifest, article)

        prepared = pipeline.prepare(manifest.run_id, render_png=False)
        report = json.loads((run_dir / "quality.json").read_text(encoding="utf-8"))

        self.assertEqual(prepared.state, Stage.RENDERED)
        self.assertIn("generic-language", {item["code"] for item in report["findings"]})


if __name__ == "__main__":
    unittest.main()
