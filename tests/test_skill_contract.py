from pathlib import Path
import json
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "publishing-wechat-articles"


class SkillContractTest(unittest.TestCase):
    def test_required_skill_files_exist(self):
        required = [
            "SKILL.md",
            "agents/openai.yaml",
            "scripts/preflight.py",
            "references/resource-map.md",
            "references/writing-contract.md",
            "references/publishing-contract.md",
            "references/troubleshooting.md",
        ]
        for relative_path in required:
            self.assertTrue((SKILL / relative_path).is_file(), relative_path)

    def test_skill_declares_current_pipeline_invariants(self):
        text = (SKILL / "SKILL.md").read_text()
        for phrase in [
            "collect-only",
            "prepare-only",
            "publish",
            "10 个阶段",
            "只发送 1 条消息",
            "未经用户授权不得",
            "先运行预检",
            "标题校验",
            "title-quality.json",
            "retitle",
        ]:
            self.assertIn(phrase, text)

        self.assertLess(text.index("标题校验"), text.index("Cover"))

    def test_writing_contract_explains_title_quality_gate(self):
        text = (SKILL / "references/writing-contract.md").read_text()
        for phrase in [
            "80",
            "正文关键词",
            "价值信号",
            "夸张",
            "title-quality.json",
            "needs_review",
        ]:
            self.assertIn(phrase, text)

    def test_publishing_contract_uses_boolean_status_and_account_routing(self):
        text = (SKILL / "references/publishing-contract.md").read_text()
        for phrase in [
            "tech",
            "parenting",
            "是否已发布",
            "false",
            "标题 + 摘要 + 封面 URL + HTML URL",
            "HTML URL 返回 200",
        ]:
            self.assertIn(phrase, text)

    def test_skill_contains_no_embedded_credentials(self):
        content = "\n".join(
            path.read_text(errors="ignore")
            for path in SKILL.rglob("*")
            if path.is_file() and path.name != "runtime.local.toml"
        )
        forbidden = [
            r"LTAI[0-9A-Za-z]{12,}",
            r"app_secret\s*:\s*[0-9A-Za-z]{16,}",
            r"OSS_SK\s*=\s*['\"](?!__MIGRATED_TO_RUNTIME_LOCAL__)[^'\"]+",
        ]
        for pattern in forbidden:
            self.assertIsNone(re.search(pattern, content), pattern)

    def test_preflight_routes_parenting_content(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts/preflight.py"),
                "--mode",
                "collect-only",
                "--title",
                "孩子进入青春期后，父母怎么沟通",
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["account"], "parenting")
        self.assertEqual(
            payload["record_fields"],
            ["是否已发布", "标题", "摘要", "封面", "内容"],
        )

    def test_preflight_defaults_technical_content_to_tech(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts/preflight.py"),
                "--mode",
                "collect-only",
                "--title",
                "Swift Agent 的工程化实践",
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["account"], "tech")
        self.assertEqual(
            payload["record_fields"],
            ["内容", "是否已发布", "标题", "摘要", "封面"],
        )


if __name__ == "__main__":
    unittest.main()
