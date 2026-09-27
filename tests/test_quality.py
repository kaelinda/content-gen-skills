from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "publishing-wechat-articles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.quality import check_article


class QualityTest(unittest.TestCase):
    def test_frontmatter_delimiters_are_not_body_horizontal_rules(self):
        markdown = """---
title: Demo
tags: [swift]
---

## Section

正文内容。
"""
        report = check_article(markdown, "<section id=\"nice\"><h2>Section</h2></section>")
        self.assertNotIn("body-horizontal-rule", {item.code for item in report.findings})

    def test_body_rule_and_full_banned_word_set_are_blocking(self):
        markdown = """## Section

值得注意的是，这不是速度，而是边界。

---

正文。
"""
        report = check_article(markdown, "<section id=\"nice\"><h2>Section</h2></section>")
        codes = {item.code for item in report.blocking}
        self.assertIn("banned-word", codes)
        self.assertIn("body-horizontal-rule", codes)

    def test_code_examples_do_not_trigger_banned_words(self):
        markdown = """## Section

```text
值得注意的是
```

`总的来说` is prompt text.
"""
        report = check_article(markdown, "<section id=\"nice\"><h2>Section</h2></section>")
        self.assertNotIn("banned-word", {item.code for item in report.blocking})

    def test_author_voice_mode_treats_generic_language_as_advisory(self):
        markdown = """## Section

值得注意的是，这不是速度，而是边界。
"""
        report = check_article(
            markdown,
            "<section id=\"nice\"><h2>Section</h2></section>",
            author_voice=True,
        )

        self.assertNotIn("banned-word", {item.code for item in report.blocking})
        self.assertIn("generic-language", {item.code for item in report.warnings})

    def test_structural_and_security_findings_are_blocking(self):
        markdown = """---
title: Demo
summary: Summary
---

## Section

[bad](javascript:alert(1))

```python
print('unfinished')

TODO: fill this later
Authorization: Bearer abcdefghijklmnop
"""
        report = check_article(markdown, "<h2>Section</h2>")
        codes = {item.code for item in report.blocking}
        self.assertTrue({"resource-url", "code-fence", "residual-marker", "sensitive-value"} <= codes)

    def test_account_rules_are_warnings_and_do_not_replace_mechanical_gates(self):
        report = check_article("## Section\n\nA short article.\n", "<h2>Section</h2>", account="parenting")
        warning_codes = {item.code for item in report.warnings}
        self.assertIn("parenting-age", warning_codes)
        self.assertIn("parenting-action", warning_codes)
        self.assertTrue(report.passed)


if __name__ == "__main__":
    unittest.main()
