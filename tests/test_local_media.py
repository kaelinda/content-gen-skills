from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "publishing-wechat-articles" / "scripts"))
from wechat_pipeline.local_media import resolve_local_images


class LocalMediaTest(unittest.TestCase):
    def test_resolves_run_local_image_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "figs").mkdir()
            Image.new("RGB", (4, 4), "red").save(run / "figs" / "chart.png")
            args = dict(bucket="bucket", endpoint="oss.example", prefix="wechat",
                        account="tech", title="Demo")
            markdown, images = resolve_local_images("## Chart\n\n![Chart](figs/chart.png)\n", run, **args)
            self.assertEqual(len(images), 1)
            self.assertIn(images[0]["url"], markdown)
            self.assertEqual(images[0]["content_type"], "image/png")
            with self.assertRaises(ValueError):
                resolve_local_images("![bad](../outside.png)", run, **args)


if __name__ == "__main__":
    unittest.main()
