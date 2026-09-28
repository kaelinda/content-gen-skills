from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "publishing-wechat-articles"
CLI = "publishing-wechat-articles/scripts/pipeline.py"


class AgentDiscoveryTest(unittest.TestCase):
    def test_codex_and_claude_resolve_the_same_canonical_skill(self):
        codex = ROOT / ".agents" / "skills" / "publishing-wechat-articles"
        claude = ROOT / ".claude" / "skills" / "publishing-wechat-articles"
        self.assertTrue(codex.is_symlink())
        self.assertTrue(claude.is_symlink())
        self.assertEqual(codex.resolve(), SKILL.resolve())
        self.assertEqual(claude.resolve(), SKILL.resolve())

    def test_root_instructions_use_one_cli(self):
        for name in ("AGENTS.md", "CLAUDE.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("publishing-wechat-articles", text)
            self.assertIn(CLI, text)

    def test_active_runtime_has_no_external_hermes_paths_or_env_reads(self):
        paths = [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]
        paths.extend(sorted((SKILL / "scripts" / "wechat_pipeline").glob("*.py")))
        paths.extend([SKILL / "scripts" / "pipeline.py", SKILL / "scripts" / "preflight.py"])
        content = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for forbidden in ("~/.hermes", "/Users/nowcoder", "OSS_AK", "OSS_SK"):
            self.assertNotIn(forbidden, content)
        self.assertIn("lark-cli", content)

    def test_vendored_hermes_sources_are_present(self):
        for name in (
            "tech-content-writer",
            "content-collector",
            "wechat-cover-html",
            "md-to-html",
            "tech-wechat-publish",
        ):
            self.assertTrue((SKILL / "vendor" / "hermes" / name).is_dir(), name)


if __name__ == "__main__":
    unittest.main()
