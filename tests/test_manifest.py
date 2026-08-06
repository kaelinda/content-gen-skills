from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "publishing-wechat-articles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.manifest import ManifestError, RunManifest
from wechat_pipeline.models import Stage


class ManifestTest(unittest.TestCase):
    def test_atomic_roundtrip_and_artifact_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            artifact = run_dir / "article.md"
            artifact.write_text("content", encoding="utf-8")
            manifest = RunManifest.create("run-fixed", "prepare-only", "tech", "Title", "Summary")
            manifest.record_artifact("article_markdown", artifact, run_dir)
            manifest.save(run_dir / "manifest.json")

            loaded = RunManifest.load(run_dir / "manifest.json")
            self.assertEqual(loaded.run_id, "run-fixed")
            self.assertEqual(
                loaded.artifacts["article_markdown"]["sha256"],
                "ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9432297b9ec9f73",
            )
            self.assertFalse((run_dir / "manifest.json.tmp").exists())

    def test_rejects_invalid_state_transition(self):
        manifest = RunManifest.create("run-fixed", "prepare-only", "tech", "Title", "Summary")
        with self.assertRaises(ManifestError):
            manifest.transition(Stage.UPLOADED)

    def test_author_voice_is_optional_and_roundtrips_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            manifest = RunManifest.create("run-fixed", "prepare-only", "tech", "Title", "Summary")
            self.assertFalse(manifest.requires_voice)

            manifest.enable_author_voice("2026-08-06", "a" * 64)
            manifest.save(path)

            loaded = RunManifest.load(path)
            self.assertTrue(loaded.requires_voice)
            self.assertEqual(loaded.editorial["profile_sha256"], "a" * 64)
            self.assertEqual(loaded.editorial["brief_status"], "missing")
            self.assertEqual(loaded.editorial["review_status"], "missing")


if __name__ == "__main__":
    unittest.main()
