from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
import tomllib
import traceback
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "publishing-wechat-articles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.config import load_repository_config  # noqa: E402
from wechat_pipeline.preflight import run_preflight  # noqa: E402


class RepositoryConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repository = Path(self.temp.name).resolve()
        self.skill = self.repository / "publishing-wechat-articles"
        self.environment = patch.dict("os.environ", {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        # Copy only known public assets, never the developer's private config.
        source = ROOT / "publishing-wechat-articles"
        (self.skill / "config").mkdir(parents=True)
        for name in ("accounts.toml", "runtime.example.toml"):
            shutil.copyfile(source / "config" / name, self.skill / "config" / name)
        profiles = tomllib.loads((self.skill / "config/accounts.toml").read_text())["accounts"]
        paths = [path.relative_to(source) for path in (source / "scripts/wechat_pipeline").glob("*.py")]
        for profile in profiles.values():
            paths.extend(Path(profile[key]) for key in ("theme_file", "cover_template"))
        for relative in paths:
            target = self.skill / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
        self.config = load_repository_config(self.skill)

    def write_dotenv(self, text, mode=0o600):
        path = self.repository / ".env"
        path.write_text(text, encoding="utf-8")
        path.chmod(mode)
        return path

    def write_runtime(self, text, mode=0o600):
        path = self.skill / "config/runtime.local.toml"
        path.write_text(text, encoding="utf-8")
        path.chmod(mode)
        return path

    def preflight(self, config, mode="publish"):
        return run_preflight(config, mode, "tech", playwright_available=True)

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
            shutil.copytree(
                self.skill, skill,
                ignore=shutil.ignore_patterns("runtime.local.toml"),
            )
            self.assertFalse((skill / "config" / "runtime.local.toml").exists())
            self.assertTrue((skill / "config" / "runtime.example.toml").is_file())

            with patch.dict("os.environ", {}, clear=True):
                config = load_repository_config(skill)

            self.assertEqual(config.runtime_path.name, "runtime.example.toml")
            self.assertEqual(config.runtime.oss_access_key_id, "")
            self.assertEqual(config.runtime.oss_access_key_secret, "")

    def test_credentials_are_named_not_stored(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "publishing-wechat-articles"
            shutil.copytree(
                self.config.skill_root / "config", skill / "config",
                ignore=shutil.ignore_patterns("runtime.local.toml"),
            )
            runtime_path = skill / "config" / "runtime.local.toml"
            template = (skill / "config" / "runtime.example.toml").read_text()
            runtime_path.write_text(
                template.replace('access_key_id = ""', 'access_key_id = "test-ak"')
                .replace('access_key_secret = ""', 'access_key_secret = "test-sk"')
            )
            runtime_path.chmod(0o600)
            with patch.dict("os.environ", {}, clear=True):
                config = load_repository_config(skill)
            self.assertEqual(config.runtime_path, runtime_path.resolve())
            self.assertEqual(config.runtime_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(config.runtime.oss_access_key_id, "test-ak")
            self.assertEqual(config.runtime.oss_access_key_secret, "test-sk")
        raw = (self.config.skill_root / "config/accounts.toml").read_text()
        self.assertNotIn("LTAI", raw)
        self.assertNotIn("app_secret =", raw)
        active_source = "\n".join(
            path.read_text(errors="ignore")
            for path in (self.config.skill_root / "scripts/wechat_pipeline").rglob("*.py")
        )
        self.assertNotIn(".hermes", active_source)

    def test_environment_values_override_local_runtime_without_printing_them(self):
        values = {
            "OSS_ACCESS_KEY_ID": "env-ak",
            "OSS_ACCESS_KEY_SECRET": "env-sk",
            "OSS_BUCKET": "env-bucket",
            "FEISHU_TECH_APP_ID": "env-tech-app",
            "FEISHU_TECH_APP_SECRET": "env-tech-secret",
            "FEISHU_TECH_CHAT_ID": "env-tech-chat",
            "FEISHU_TECH_BASE_ID": "env-tech-base",
            "FEISHU_TECH_TABLE_ID": "env-tech-table",
        }
        with patch.dict("os.environ", values, clear=True):
            config = load_repository_config(self.skill)
        self.assertEqual(config.runtime_source, "environment")
        self.assertEqual(config.oss.bucket, "env-bucket")
        self.assertEqual(config.runtime.oss_access_key_id, "env-ak")
        self.assertEqual(config.runtime.accounts["tech"].table_id, "env-tech-table")


    def test_repository_dotenv_loads_from_non_repository_cwd_without_mutating_environment(self):
        path = self.write_dotenv('OSS_ACCESS_KEY_ID="dotenv-ak"\nOSS_BUCKET=dotenv-bucket\n')
        other = self.repository / "elsewhere"
        other.mkdir()
        (other / ".env").write_text("OSS_ACCESS_KEY_ID=wrong-cwd\n")
        before = dict(os.environ)
        previous = Path.cwd()
        try:
            os.chdir(other)
            config = load_repository_config(self.skill)
        finally:
            os.chdir(previous)
        self.assertEqual(config.runtime.oss_access_key_id, "dotenv-ak")
        self.assertEqual(config.oss.bucket, "dotenv-bucket")
        self.assertEqual(config.dotenv_path, path)
        self.assertEqual(config.runtime_source, "dotenv")
        self.assertEqual(dict(os.environ), before)

    def test_no_parent_home_or_skill_dotenv_discovery(self):
        home = self.repository / "home"
        home.mkdir()
        (home / ".env").write_text("OSS_ACCESS_KEY_ID=wrong-home\n")
        (self.skill / ".env").write_text("OSS_ACCESS_KEY_ID=wrong-skill\n")
        self.write_dotenv("OSS_ACCESS_KEY_ID=wrong-ancestor\n")
        nested = self.repository / "nested" / "skill"
        shutil.copytree(self.skill, nested, ignore=shutil.ignore_patterns(".env"))
        with patch.dict("os.environ", {"HOME": str(home)}, clear=True):
            config = load_repository_config(nested)
        self.assertEqual(config.runtime.oss_access_key_id, "")
        self.assertIsNone(config.dotenv_path)

    def test_dotenv_can_be_explicitly_disabled_without_reading_it(self):
        self.write_dotenv('OSS_ACCESS_KEY_ID="malformed\n')
        config = load_repository_config(self.skill, load_dotenv=False)
        self.assertEqual(config.runtime.oss_access_key_id, "")
        self.assertIsNone(config.dotenv_path)

    def test_layer_precedence_checks_all_aliases_before_next_layer(self):
        self.write_runtime('[oss]\naccess_key_id="local-ak"\naccess_key_secret="local-sk"\n')
        self.write_dotenv(
            "OSS_ACCESS_KEY_ID=dotenv-ak\nWECHAT_OSS_ACCESS_KEY_SECRET=dotenv-sk\n"
            "FEISHU_TECH_BASE_ID=dotenv-base\nOPENAI_API_KEY=dotenv-image-key\n"
        )
        with patch.dict("os.environ", {
            "WECHAT_OSS_ACCESS_KEY_ID": "process-ak",
            "WECHAT_TECH_BASE_TOKEN": "process-base",
            "IMAGE_API_KEY": "process-image-key",
        }, clear=True):
            config = load_repository_config(self.skill)
        self.assertEqual(config.runtime.oss_access_key_id, "process-ak")
        self.assertEqual(config.runtime.oss_access_key_secret, "dotenv-sk")
        self.assertEqual(config.runtime.accounts["tech"].base_token, "process-base")
        self.assertEqual(config.runtime.image_generation.api_key, "process-image-key")

    def test_primary_alias_wins_only_within_the_same_layer(self):
        self.write_dotenv("OSS_ACCESS_KEY_ID=primary\nWECHAT_OSS_ACCESS_KEY_ID=alias\n")
        self.assertEqual(load_repository_config(self.skill).runtime.oss_access_key_id, "primary")
        with patch.dict("os.environ", {"OSS_ACCESS_KEY_ID": "process-primary", "WECHAT_OSS_ACCESS_KEY_ID": "process-alias"}):
            self.assertEqual(load_repository_config(self.skill).runtime.oss_access_key_id, "process-primary")

    def test_partial_local_runtime_deep_merges_example_sections(self):
        path = self.write_runtime('[accounts.tech]\nchat_id="local-chat"\n[image_generation]\nmodel="local-model"\n')
        config = load_repository_config(self.skill)
        self.assertEqual(config.runtime_path, path)
        self.assertEqual(config.runtime.accounts["tech"].chat_id, "local-chat")
        self.assertEqual(config.runtime.accounts["tech"].table_id, "")
        self.assertEqual(config.runtime.accounts["parenting"].chat_id, "")
        self.assertEqual(config.runtime.oss_access_key_id, "")
        self.assertEqual(config.runtime.image_generation.model, "local-model")
        self.assertEqual(config.runtime.image_generation.timeout_seconds, 120)

    def test_empty_values_explicitly_override_lower_layers(self):
        self.write_runtime('[oss]\naccess_key_secret="local-secret"\n[image_generation]\nenabled=true\nallowed_download_hosts=["cdn.example"]\n')
        self.write_dotenv("OSS_ACCESS_KEY_ID=dotenv-ak\nWECHAT_OSS_ACCESS_KEY_SECRET=\nIMAGE_ENABLED=\nIMAGE_ALLOWED_DOWNLOAD_HOSTS=\nOSS_ENDPOINT=\n")
        with patch.dict("os.environ", {"WECHAT_OSS_ACCESS_KEY_ID": ""}, clear=True):
            config = load_repository_config(self.skill)
        self.assertEqual(config.runtime.oss_access_key_id, "")
        self.assertEqual(config.runtime.oss_access_key_secret, "")
        self.assertFalse(config.runtime.image_generation.enabled)
        self.assertEqual(config.runtime.image_generation.allowed_download_hosts, ())
        self.assertEqual(config.oss.endpoint, "")

    def test_empty_numeric_value_is_invalid_not_inherited(self):
        self.write_dotenv("IMAGE_TIMEOUT_SECONDS=\n")
        with self.assertRaisesRegex(ValueError, "IMAGE_TIMEOUT_SECONDS"):
            load_repository_config(self.skill)

    def test_numeric_error_and_traceback_do_not_echo_values(self):
        secret = "synthetic-value-must-not-appear"
        with patch.dict("os.environ", {"IMAGE_TIMEOUT_SECONDS": secret}):
            try:
                load_repository_config(self.skill)
            except ValueError as exc:
                self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
            else:
                self.fail("invalid numeric input was accepted")

    def test_process_region_beats_dotenv_endpoint(self):
        self.write_dotenv("OSS_ENDPOINT=dotenv-endpoint\n")
        with patch.dict("os.environ", {"WECHAT_OSS_REGION": "cn-test"}, clear=True):
            config = load_repository_config(self.skill)
        self.assertEqual(config.oss.endpoint, "oss-cn-test.aliyuncs.com")

    def test_runtime_repr_hides_all_secret_fields(self):
        values = {
            "OSS_ACCESS_KEY_ID": "synthetic-access-id",
            "OSS_ACCESS_KEY_SECRET": "synthetic-access-secret",
            "FEISHU_TECH_APP_SECRET": "synthetic-tech-secret",
            "FEISHU_PARENTING_APP_SECRET": "synthetic-parenting-secret",
            "FEISHU_TECH_BASE_ID": "synthetic-base-token",
            "OPENAI_API_KEY": "synthetic-image-secret",
        }
        self.write_dotenv("\n".join(f"{key}={value}" for key, value in values.items()))
        config = load_repository_config(self.skill)
        self.assertEqual(config.runtime.oss_access_key_secret, values["OSS_ACCESS_KEY_SECRET"])
        self.assertEqual(config.runtime.image_generation.api_key, values["OPENAI_API_KEY"])
        for value in values.values():
            self.assertNotIn(value, repr(config))
            self.assertNotIn(value, repr(config.runtime))
            self.assertNotIn(value, json.dumps(self.preflight(config).to_dict()))

    def test_preflight_does_not_require_secret_free_example_permissions(self):
        self.config.runtime_path.chmod(0o644)
        report = self.preflight(self.config)
        self.assertNotIn("runtime_permissions", report.failures)
        self.assertIn("oss_credentials", report.failures)
        self.assertTrue(self.preflight(self.config, "prepare-only").ready)

    def test_preflight_checks_insecure_dotenv_without_exposing_secrets(self):
        secret = "synthetic-dotenv-secret"
        self.write_dotenv(f"OSS_ACCESS_KEY_SECRET={secret}\n", mode=0o644)
        config = load_repository_config(self.skill)
        for mode in ("collect-only", "prepare-only", "publish"):
            with self.subTest(mode=mode):
                report = self.preflight(config, mode)
                self.assertIn("dotenv_permissions", report.failures)
                self.assertNotIn(secret, json.dumps(report.to_dict()))

    def test_partial_environment_does_not_bypass_private_runtime_permissions(self):
        template = self.config.runtime_path.read_text()
        self.write_runtime(template.replace('access_key_secret = ""', 'access_key_secret = "synthetic-local-secret"'), mode=0o644)
        with patch.dict("os.environ", {"OSS_BUCKET": "one-environment-setting"}, clear=True):
            config = load_repository_config(self.skill)
        report = self.preflight(config)
        self.assertIn("runtime_permissions", report.failures)
        self.assertNotIn("synthetic-local-secret", json.dumps(report.to_dict()))

    def test_preflight_checks_both_private_files_even_with_process_override(self):
        self.write_runtime(self.config.runtime_path.read_text(), mode=0o644)
        dotenv = self.write_dotenv("OSS_ACCESS_KEY_SECRET=dotenv-secret\n", mode=0o644)
        with patch.dict("os.environ", {"OSS_ACCESS_KEY_SECRET": "process-secret"}):
            config = load_repository_config(self.skill)
        report = self.preflight(config)
        self.assertIn("runtime_permissions", report.failures)
        self.assertIn("dotenv_permissions", report.failures)
        self.write_runtime(self.config.runtime_path.read_text(), mode=0o600)
        dotenv.chmod(0o600)
        report = self.preflight(config)
        self.assertNotIn("runtime_permissions", report.failures)
        self.assertNotIn("dotenv_permissions", report.failures)

    def test_preflight_rejects_deleted_or_replaced_private_sources(self):
        dotenv = self.write_dotenv("OSS_ACCESS_KEY_SECRET=dotenv-secret\n")
        config = load_repository_config(self.skill)
        dotenv.unlink()
        self.assertIn("dotenv_permissions", self.preflight(config).failures)
        target = self.repository / "other.env"
        target.write_text("unused")
        target.chmod(0o600)
        dotenv.symlink_to(target)
        self.assertIn("dotenv_permissions", self.preflight(config).failures)

    def test_resolved_skill_root_selects_canonical_repository_dotenv(self):
        self.write_dotenv("OSS_ACCESS_KEY_ID=canonical-repository\n")
        wrapper = self.repository / "wrapper"
        wrapper.mkdir()
        linked_skill = wrapper / "linked-skill"
        linked_skill.symlink_to(self.skill, target_is_directory=True)
        (wrapper / ".env").write_text("OSS_ACCESS_KEY_ID=wrong-wrapper\n")
        config = load_repository_config(linked_skill)
        self.assertEqual(config.runtime.oss_access_key_id, "canonical-repository")
        self.assertEqual(config.repository_root, self.repository)

    def test_malformed_dotenv_fails_closed_even_with_process_credentials(self):
        secret = "synthetic-malformed-secret"
        self.write_dotenv(f'# first line\nOSS_ACCESS_KEY_SECRET="{secret}\n')
        with patch.dict("os.environ", {"OSS_ACCESS_KEY_SECRET": "process-secret"}):
            try:
                load_repository_config(self.skill)
            except ValueError as exc:
                self.assertEqual(str(exc), "invalid .env syntax at line 2")
                self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
            else:
                self.fail("malformed dotenv was ignored")

    def test_symlink_dotenv_is_rejected_but_opt_out_does_not_inspect_it(self):
        dotenv = self.repository / ".env"
        dotenv.symlink_to(self.repository / "nonexistent-target")
        with self.assertRaises(ValueError):
            load_repository_config(self.skill)
        self.assertIsNone(load_repository_config(self.skill, load_dotenv=False).dotenv_path)

    def test_disabled_dotenv_still_allows_explicit_process_overrides(self):
        self.write_dotenv("OSS_ACCESS_KEY_ID=dotenv-value\n")
        with patch.dict("os.environ", {"WECHAT_OSS_ACCESS_KEY_ID": "process-value"}, clear=True):
            config = load_repository_config(self.skill, load_dotenv=False)
        self.assertEqual(config.runtime.oss_access_key_id, "process-value")
        self.assertEqual(config.runtime_source, "environment")

    def test_preflight_checks_empty_dotenv_and_dotenv_plus_partial_local(self):
        self.write_dotenv("", mode=0o644)
        config = load_repository_config(self.skill)
        self.assertIn("dotenv_permissions", self.preflight(config).failures)
        self.write_dotenv("OSS_BUCKET=one-dotenv-setting\n")
        self.write_runtime('[oss]\naccess_key_secret="synthetic-local-secret"\n', mode=0o644)
        config = load_repository_config(self.skill)
        self.assertIn("runtime_permissions", self.preflight(config).failures)

    def test_local_toml_can_explicitly_clear_example_value(self):
        self.write_runtime('[feishu]\nmode=""\n')
        config = load_repository_config(self.skill)
        self.assertEqual(config.runtime.feishu_mode, "")
        self.assertEqual(config.runtime.image_generation.timeout_seconds, 120)

    def test_private_runtime_symlink_is_not_an_implicit_credential_source(self):
        path = self.skill / "config/runtime.local.toml"
        path.symlink_to(self.config.runtime_path)
        with self.assertRaises(ValueError):
            load_repository_config(self.skill)


if __name__ == "__main__":
    unittest.main()
