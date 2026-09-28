from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "publishing-wechat-articles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.render import render_markdown


class RenderTest(unittest.TestCase):
    def test_renders_escaped_markdown_with_local_theme(self):
        markdown = """---
title: Demo
---
## Heading <script>alert(1)</script>

Body **bold** and `code`.
"""
        rendered = render_markdown(markdown, "#nice h2 { color: red; }", title="A < B")
        self.assertIn("<h2", rendered)
        self.assertIn("Heading &lt;script&gt;", rendered)
        self.assertNotIn("<script>alert", rendered)
        self.assertIn("#nice h2 { color: red; }", rendered)
        self.assertIn("<title>A &lt; B</title>", rendered)

    def test_removes_javascript_and_data_resource_schemes(self):
        markdown = """## Links

[bad](javascript:alert(1)) [good](https://example.com/docs)

![bad image](data:text/html,boom)
"""
        rendered = render_markdown(markdown, "")
        self.assertNotIn("javascript:", rendered.lower())
        self.assertNotIn("data:text", rendered.lower())
        self.assertIn('href="https://example.com/docs"', rendered)

    def test_renders_article_tables_lists_and_mobile_overflow(self):
        markdown = """## Results

| Metric | Before | After |
|---|---|---|
| Top 1 | 5% | 18% |

1. First
2. Second

![Chart](https://example.com/chart.png)
"""
        rendered = render_markdown(markdown, "")
        self.assertIn("<table>", rendered)
        self.assertIn("<th>Metric</th>", rendered)
        self.assertIn("<td>18%</td>", rendered)
        self.assertIn("<ol>", rendered)
        self.assertIn('class="table-scroll"', rendered)
        self.assertIn("overflow-x:auto", rendered)
        self.assertIn('<figure><img src="https://example.com/chart.png"', rendered)


if __name__ == "__main__":
    unittest.main()
