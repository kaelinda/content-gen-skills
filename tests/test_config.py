from pathlib import Path
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "publishing-wechat-articles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.config import load_repository_config


class RepositoryConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = load_repository_config(ROOT / "publishing-wechat-articles")

    def test_profiles_are_repository_local(self):
        self.assertEqual(set(self.config.accounts), {"tech", "parenting"})
        for profile in self.config.accounts.values():
            self.assertFalse(profile.vault_default.is_absolute())
            self.assertNotIn(".hermes", str(profile.vault_default))
            self.assertTrue((self.config.skill_root / profile.theme_file).is_file())
            self.assertTrue((self.config.skill_root / profile.cover_template).is_file())

    def test_account_routing_uses_profile_keywords(self):
        self.assertEqual(self.config.route_account("auto", "Swift Agent 实战", ""), "tech")
        self.assertEqual(self.config.route_account("auto", "孩子进入青春期", ""), "parenting")
        self.assertEqual(self.config.route_account("parenting", "Swift 教程", ""), "parenting")

    def test_prepare_config_loads_without_private_runtime_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "publishing-wechat-articles"
            shutil.copytree(ROOT / "publishing-wechat-articles", skill)
            (skill / "config" / "runtime.local.toml").unlink()
            self.assertTrue((skill / "config" / "runtime.example.toml").is_file())

            config = load_repository_config(skill)

            self.assertEqual(config.runtime_path.name, "runtime.example.toml")
            self.assertEqual(config.runtime.oss_access_key_id, "")
            self.assertEqual(config.runtime.oss_access_key_secret, "")

    def test_credentials_are_named_not_stored(self):
        self.assertTrue(self.config.runtime_path.is_file())
        self.assertEqual(self.config.runtime_path.stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.config.runtime.oss_access_key_id)
        self.assertTrue(self.config.runtime.oss_access_key_secret)
        raw = (self.config.skill_root / "config/accounts.toml").read_text()
        self.assertNotIn("LTAI", raw)
        self.assertNotIn("app_secret =", raw)
        active_source = "\n".join(
            path.read_text(errors="ignore")
            for path in (self.config.skill_root / "scripts/wechat_pipeline").rglob("*.py")
        )
        self.assertNotIn("os.environ", active_source)
        self.assertNotIn(".hermes", active_source)


if __name__ == "__main__":
    unittest.main()
