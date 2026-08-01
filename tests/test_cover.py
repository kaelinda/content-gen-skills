from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "publishing-wechat-articles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.cover import build_cover_html, render_cover_png


class CoverTest(unittest.TestCase):
    def test_all_cover_fields_are_html_escaped(self):
        template = "<h1>{{TITLE}}</h1><p>{{SUMMARY}}</p><b>{{TAG}}</b><i>{{BRAND}}</i>"
        payload = {name: '<img src=x onerror="boom">' for name in ("title", "summary", "tag", "brand")}
        rendered = build_cover_html(template, **payload)
        self.assertNotIn("<img", rendered)
        self.assertNotIn("onerror=\"boom\"", rendered)
        self.assertEqual(rendered.count("&lt;img"), 4)

    def test_png_renderer_uses_fixed_viewport_without_shell(self):
        events = []

        class Page:
            def set_content(self, html, wait_until):
                events.append(("content", html, wait_until))

            def screenshot(self, path, type):
                Path(path).write_bytes(b"\x89PNG\r\n\x1a\nfixture")
                events.append(("screenshot", path, type))

        class Browser:
            def new_page(self, viewport):
                events.append(("viewport", viewport))
                return Page()

            def close(self):
                events.append(("close",))

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "cover.png"
            render_cover_png("<html></html>", output, browser_factory=lambda: Browser())
            self.assertEqual(events[0], ("viewport", {"width": 1200, "height": 540}))
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
