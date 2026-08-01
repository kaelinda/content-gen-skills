from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "publishing-wechat-articles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.title_quality import check_title


TECH_BODY = """## 从原型到生产

Swift Agent 的工程化不只包括原型开发，还需要稳定性检查、失败恢复和上线验证。

## 稳定上线的关键

本文给出 Swift Agent 从原型走向稳定上线的完整实战路径。
"""


class TitleQualityTest(unittest.TestCase):
    def test_focused_title_with_clear_value_passes(self):
        report = check_title("Swift Agent 工程化实战：从原型到稳定上线", TECH_BODY)
        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.score, 80)
        self.assertGreater(report.metrics["body_overlap"], 0)
        self.assertIn("实战", report.metrics["value_signals"])

    def test_sensational_title_is_blocked(self):
        report = check_title("震惊！这个方法让 99% 的程序员彻底失业！！！", TECH_BODY)
        codes = {item.code for item in report.blocking}
        self.assertIn("title-sensational", codes)
        self.assertIn("title-punctuation", codes)

    def test_vague_title_is_blocked_by_low_score(self):
        report = check_title("关于 AI 的一些思考", "## AI\n\n这里记录 AI 产品设计与工程实践。")
        codes = {item.code for item in report.findings}
        self.assertIn("title-vague", codes)
        self.assertIn("title-low-score", codes)
        self.assertFalse(report.passed)

    def test_title_body_mismatch_is_blocked_by_low_score(self):
        report = check_title("青春期孩子沟通的 5 个实用方法", TECH_BODY)
        codes = {item.code for item in report.findings}
        self.assertIn("title-body-mismatch", codes)
        self.assertIn("title-low-score", codes)
        self.assertFalse(report.passed)


if __name__ == "__main__":
    unittest.main()
