from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "publishing-wechat-articles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.capture import FetchResponse, archive_capture, capture_source
import wechat_pipeline.capture as capture_module


class CaptureTest(unittest.TestCase):
    def test_https_context_uses_certifi_when_default_store_is_empty(self):
        empty_context = unittest.mock.Mock()
        empty_context.get_ca_certs.return_value = []
        certifi_context = unittest.mock.Mock()

        with patch("ssl.create_default_context", side_effect=[empty_context, certifi_context]) as create_context:
            factory = getattr(capture_module, "_https_context", lambda: None)
            result = factory()

        self.assertIs(result, certifi_context)
        self.assertEqual(create_context.call_count, 2)
        self.assertIn("cafile", create_context.call_args_list[1].kwargs)

    def test_x_status_uses_repository_fxtwitter_parser(self):
        payload = {
            "tweet": {
                "text": "A captured post",
                "author": {"name": "Author"},
                "media": [{"url": "https://pbs.twimg.com/media/demo.jpg"}],
            }
        }
        calls = []

        def fetcher(url, max_bytes):
            calls.append(url)
            return FetchResponse(url, 200, {"content-type": "application/json"}, json.dumps(payload).encode())

        with patch("wechat_pipeline.capture.validate_public_url", side_effect=lambda value: value):
            result = capture_source("https://x.com/demo/status/123", fetcher=fetcher)
        self.assertEqual(calls, ["https://api.fxtwitter.com/demo/status/123"])
        self.assertEqual(result.method, "fxtwitter")
        self.assertEqual(result.content_md, "A captured post")
        self.assertEqual(result.images[0]["url"], "https://pbs.twimg.com/media/demo.jpg")

    def test_blog_capture_is_bounded_and_never_uploads(self):
        calls = []
        html = b"""<!doctype html><title>Safe &amp; Useful</title>
        <article><h1>Hello</h1><p>Body text.</p>
        <img src=\"https://93.184.216.34/a.png\" alt=\"diagram\"></article>"""

        def fetcher(url, max_bytes):
            calls.append((url, max_bytes))
            return FetchResponse(url, 200, {"content-type": "text/html"}, html)

        result = capture_source("https://93.184.216.34/post", fetcher=fetcher)
        self.assertEqual(result.title, "Safe & Useful")
        self.assertIn("Body text.", result.content_md)
        self.assertEqual(result.images[0]["url"], "https://93.184.216.34/a.png")
        self.assertEqual(len(calls), 1)
        self.assertNotIn("oss", json.dumps(result.to_dict()).lower())

    def test_archive_writes_local_provenance_only(self):
        response = FetchResponse(
            "https://93.184.216.34/post",
            200,
            {"content-type": "text/html"},
            b"<title>Demo</title><main><p>Captured body</p></main>",
        )
        result = capture_source(response.url, fetcher=lambda *_: response)
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = archive_capture(result, Path(tmp))
            self.assertEqual(set(artifacts), {"raw", "content", "metadata", "images"})
            self.assertIn("Captured body", artifacts["content"].read_text())
            metadata = json.loads(artifacts["metadata"].read_text())
            self.assertEqual(metadata["source_url"], response.url)


if __name__ == "__main__":
    unittest.main()
