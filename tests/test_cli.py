from dataclasses import replace
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "publishing-wechat-articles"
SCRIPTS = SKILL / "scripts"
CLI = SCRIPTS / "pipeline.py"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.config import load_repository_config
from wechat_pipeline.preflight import run_preflight


class CliTest(unittest.TestCase):
    def test_all_commands_expose_help(self):
        for command in (
            "preflight",
            "plan",
            "capture",
            "brief",
            "voice-review",
            "retitle",
            "prepare",
            "status",
            "publish",
            "resume",
        ):
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, str(CLI), command, "--help"],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_preflight_detects_missing_internal_asset_and_credentials(self):
        config = load_repository_config(SKILL)
        broken_profile = replace(config.accounts["tech"], theme_file=Path("missing.css"))
        broken_config = replace(config, accounts={**config.accounts, "tech": broken_profile})
        report = run_preflight(broken_config, "prepare-only", "tech", playwright_available=True)
        self.assertIn("theme_file", report.failures)

        empty_runtime = replace(config.runtime, oss_access_key_id="", oss_access_key_secret="")
        publish_config = replace(config, runtime=empty_runtime)
        publish_report = run_preflight(publish_config, "publish", "tech", playwright_available=True)
        self.assertIn("oss_credentials", publish_report.failures)

    def test_preflight_checks_voice_files_only_when_advanced_mode_is_requested(self):
        config = load_repository_config(SKILL)
        broken = replace(config, voice_author_path=Path("missing-author.toml"))

        default_report = run_preflight(
            broken,
            "prepare-only",
            "tech",
            playwright_available=True,
        )
        voice_report = run_preflight(
            broken,
            "prepare-only",
            "tech",
            author_voice=True,
            playwright_available=True,
        )

        self.assertNotIn("voice_profile", default_report.failures)
        self.assertIn("voice_profile", voice_report.failures)

    def test_author_voice_preflight_rejects_malformed_profile(self):
        config = load_repository_config(SKILL)
        with tempfile.TemporaryDirectory() as tmp:
            malformed = Path(tmp) / "author.toml"
            malformed.write_text("not valid = [", encoding="utf-8")
            broken = replace(config, voice_author_path=malformed)

            report = run_preflight(
                broken,
                "prepare-only",
                "tech",
                author_voice=True,
                playwright_available=True,
            )

        self.assertIn("voice_profile", report.failures)
        check = next(item for item in report.checks if item.name == "voice_profile")
        self.assertEqual(check.status, "invalid")

    def test_plan_and_status_roundtrip_with_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--workspace",
                    tmp,
                    "plan",
                    "--title",
                    "Swift Agent",
                    "--summary",
                    "Summary",
                    "--run-id",
                    "cli-run",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(plan.stdout)
            self.assertEqual(payload["run_id"], "cli-run")
            status = subprocess.run(
                [sys.executable, str(CLI), "--workspace", tmp, "status", "cli-run", "--json"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(json.loads(status.stdout)["state"], "planned")

            retitle = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--workspace",
                    tmp,
                    "retitle",
                    "cli-run",
                    "--title",
                    "Swift Agent 工程化实战：从原型到稳定上线",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            revised = json.loads(retitle.stdout)
            self.assertEqual(revised["title"], "Swift Agent 工程化实战：从原型到稳定上线")
            self.assertEqual(revised["state"], "planned")

    def test_plan_author_voice_is_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--workspace",
                    tmp,
                    "plan",
                    "--title",
                    "Swift Agent 工程化实战",
                    "--summary",
                    "Summary",
                    "--run-id",
                    "voice-cli-run",
                    "--author-voice",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(result.stdout)
            self.assertTrue(payload["editorial"]["author_voice_enabled"])
            self.assertIn("voice_context", payload["artifacts"])

    def test_publish_requires_commit_flag(self):
        result = subprocess.run(
            [sys.executable, str(CLI), "publish", "missing-run", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--commit", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
