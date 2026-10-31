"""Offline bootstrap tests: all HOME/repository writes stay in TemporaryDirectory.

Unit tests use explicit subprocess/preflight fixtures. Integration tests run the
actual CLI and bundled pip against locally synthesized wheels, never a network
index or the real checkout's configuration or Python environments.
"""
import base64
from contextlib import redirect_stderr, redirect_stdout
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("content_gen_bootstrap_under_test", SOURCE)
assert SPEC is not None and SPEC.loader is not None
bootstrap = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bootstrap
SPEC.loader.exec_module(bootstrap)
NAME = "publishing-wechat-articles"


def snapshot(root):
    """Capture only the fixture tree, including modes, links and mtimes."""
    result = {}
    for path in [root, *sorted(root.rglob("*"))]:
        info = path.lstat()
        data = (os.readlink(path) if path.is_symlink()
                else path.read_bytes() if path.is_file() else None)
        result[str(path.relative_to(root))] = (stat.S_IMODE(info.st_mode), info.st_mtime_ns, data)
    return result


@unittest.skipIf(os.name == "nt", "Unix pipeline; Windows users must use WSL")
class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bootstrap-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.home = self.base / "fake home"
        self.home.mkdir()
        self.root = self.base / "checkout with ' spaces ; literal"
        self.root.mkdir()
        self.canonical = self.root / NAME
        (self.canonical / "scripts").mkdir(parents=True)
        (self.canonical / "SKILL.md").write_text("---\nname: publishing-wechat-articles\n---\nCANONICAL BUSINESS RULES\n")
        (self.canonical / "scripts" / "pipeline.py").write_text("# Isolated fixture CLI\n")
        (self.root / "requirements.txt").write_text("# Offline fixture\n")
        (self.root / ".env.example").write_text("TEST_CREDENTIAL=template-fixture\n")
        for filename in ("AGENTS.md", "CLAUDE.md"):
            (self.root / filename).write_text(f"Read {NAME}/SKILL.md; use {NAME}/scripts/pipeline.py\n")
        for dirname in (".agents", ".claude"):
            parent = self.root / dirname / "skills"
            parent.mkdir(parents=True)
            (parent / NAME).symlink_to(f"../../{NAME}", target_is_directory=True)
        # Clear all real credentials, agent profile settings and install overrides.
        env = {"HOME": str(self.home), "PATH": os.environ.get("PATH", ""),
               "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(self.base)}
        self.environment = mock.patch.dict(os.environ, env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.commands = []
        self.fail_on = None
        self.preflight_code = 0
        self.report = {"mode": "prepare-only", "account": "tech", "ready": True,
                       "failures": [], "checks": [{"name": "playwright_chromium", "status": "ok", "required": True}]}
        self.probe = None
        self.raw_preflight = None

    def fake_venv(self):
        venv = self.root / ".venv"
        (venv / "bin").mkdir(parents=True, exist_ok=True)
        (venv / "pyvenv.cfg").write_text("# Mocked virtualenv for offline tests\n")
        python = venv / "bin" / "python"
        python.write_text("# Executions are mocked\n")
        python.chmod(0o755)

    def probe_info(self):
        venv = self.root / ".venv"
        return {"version": [3, 11], "prefix": str(venv), "base_prefix": "/fixture/base",
                "paths": {"purelib": str(venv / "lib/python3.11/site-packages"),
                          "platlib": str(venv / "lib/python3.11/site-packages"),
                          "scripts": str(venv / "bin"), "data": str(venv),
                          "stdlib": "/fixture/base/lib/python3.11",
                          "include": "/fixture/base/include/python3.11"}}

    def fake_run(self, command, **kwargs):
        self.commands.append(command)
        self.assertEqual(kwargs["cwd"], self.root)
        self.assertEqual(kwargs["env"]["HOME"], str(self.home))
        self.assertEqual(kwargs["env"]["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertFalse(kwargs.get("shell", False))
        self.assertTrue(kwargs["capture_output"])
        if command[1:3] == ["-m", "venv"]:
            label = "venv"
            if self.fail_on != label:
                self.fake_venv()
            output = ""
        elif command[1:2] == ["-c"]:
            label = "probe"
            output = json.dumps(self.probe if self.probe is not None else self.probe_info())
        elif command[1:3] == ["-m", "pip"]:
            label = "pip"
            output = ""
            for key in ("PIP_TARGET", "PIP_PREFIX", "PIP_PYTHON", "PIP_ROOT",
                        "PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE"):
                self.assertNotIn(key, kwargs["env"])
            self.assertEqual(kwargs["env"]["PIP_REQUIRE_VIRTUALENV"], "true")
            self.assertEqual(kwargs["env"]["PIP_USER"], "0")
            self.assertEqual(kwargs["env"]["PIP_CONFIG_FILE"], os.devnull)
        elif command[1:3] == ["-m", "playwright"]:
            label = "browser"
            output = ""
        elif "preflight" in command:
            label = "preflight"
            self.assertEqual(command, [str(self.root / ".venv" / "bin" / "python"),
                                      str(self.canonical / "scripts" / "pipeline.py"),
                                      "--workspace", str(self.root / "output"),
                                      "preflight", "--mode", "prepare-only", "--json"])
            return subprocess.CompletedProcess(command, self.preflight_code,
                                               self.raw_preflight if self.raw_preflight is not None else json.dumps(self.report),
                                               "PRIVATE-ERROR-FIXTURE")
        else:
            self.fail(f"Unexpected subprocess: {command}")
        code = 12 if self.fail_on == label else 0
        return subprocess.CompletedProcess(command, code, output, "PRIVATE-ERROR-FIXTURE")

    def invoke(self, *arguments):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), mock.patch.object(bootstrap.subprocess, "run", side_effect=self.fake_run):
            result = bootstrap.main(list(arguments), repo_root=self.root)
        return result, out.getvalue(), err.getvalue()

    def destination(self, agent):
        dirname = {"hermes": ".hermes", "codex": ".agents", "claude": ".claude"}[agent]
        return self.home / dirname / "skills" / NAME / "SKILL.md"

    def assert_conflict_untouched(self, *arguments):
        before = snapshot(self.base)
        code, out, err = self.invoke(*arguments)
        self.assertNotEqual(code, 0)
        self.assertEqual(self.commands, [])
        self.assertEqual(snapshot(self.base), before)
        self.assertNotIn("Bootstrap complete", out)
        return out, err

    def test_default_plan_dry_run_is_zero_write_and_zero_subprocess(self):
        env = self.root / ".env"
        env.write_text("DO_NOT_PRINT=existing-fixture\n")
        env.chmod(0o644)
        before = snapshot(self.base)
        code, out, err = self.invoke("--dry-run")
        self.assertEqual(code, 0, err)
        self.assertEqual(snapshot(self.base), before)
        self.assertEqual(self.commands, [])
        self.assertIn("Preflight NOT RUN", out)
        self.assertIn("-m pip install -r", out)
        self.assertIn("-m playwright install chromium", out)
        self.assertNotIn("existing-fixture", out + err)
        self.assertFalse((self.root / ".venv").exists())
        self.assertEqual(list(self.home.iterdir()), [])

    def test_dry_run_for_every_external_agent_is_zero_write(self):
        for agent in ("hermes", "codex", "claude", "generic"):
            with self.subTest(agent=agent):
                args = ["--agent", agent, "--dry-run"]
                if agent == "generic":
                    args.extend(["--skills-dir", str(self.home / "custom skills")])
                before = snapshot(self.base)
                code, out, err = self.invoke(*args)
                self.assertEqual(code, 0, err)
                self.assertEqual(snapshot(self.base), before)
                self.assertEqual(self.commands, [])
                self.assertIn("Bridge:", out)

    def test_project_does_not_discover_or_require_any_user_skill_directory(self):
        for name in (".hermes", ".agents", ".claude", ".codex"):
            (self.home / name).write_text("Not a directory; project must ignore this\n")
        before = snapshot(self.home)
        with mock.patch.object(bootstrap.Path, "home", side_effect=AssertionError("project requested user home")):
            code, _, err = self.invoke()
        self.assertEqual(code, 0, err)
        self.assertEqual(snapshot(self.home), before)

    def test_full_install_plan_creates_private_env_and_preserves_project_links(self):
        links = {name: (self.root / name / "skills" / NAME).lstat() for name in (".agents", ".claude")}
        code, out, err = self.invoke()
        self.assertEqual(code, 0, err)
        self.assertEqual((self.root / ".env").read_bytes(), (self.root / ".env.example").read_bytes())
        self.assertEqual(stat.S_IMODE((self.root / ".env").stat().st_mode), 0o600)
        self.assertEqual([command[2] if command[1] == "-m" else "probe" if command[1] == "-c" else "preflight"
                          for command in self.commands], ["venv", "probe", "pip", "playwright", "preflight"])
        self.assertEqual(self.commands[2][-2:], ["-r", str(self.root / "requirements.txt")])
        self.assertIn('"ready": true', out)
        self.assertIn("Bootstrap complete", out)
        self.assertEqual(list(self.home.iterdir()), [])
        for name, before in links.items():
            link = self.root / name / "skills" / NAME
            self.assertEqual(link.lstat().st_ino, before.st_ino)
            self.assertEqual(link.lstat().st_mtime_ns, before.st_mtime_ns)
            self.assertEqual(os.readlink(link), f"../../{NAME}")
            self.assertEqual(link.resolve(), self.canonical)

    def test_existing_env_is_not_read_or_replaced_and_is_chmod_600(self):
        env = self.root / ".env"
        contents = b"EXISTING_KEY=private-fixture\n# preserve byte for byte\n"
        env.write_bytes(contents)
        env.chmod(0o644)
        before_inode = env.stat().st_ino
        with mock.patch.object(bootstrap, "read_plain", wraps=bootstrap.read_plain) as read:
            code, out, err = self.invoke()
        self.assertEqual(code, 0, err)
        self.assertEqual(env.read_bytes(), contents)
        self.assertEqual(env.stat().st_ino, before_inode)
        self.assertEqual(stat.S_IMODE(env.stat().st_mode), 0o600)
        self.assertNotIn("private-fixture", out + err)
        self.assertFalse(any(call.args[0] == env for call in read.call_args_list))

    def test_all_agent_bridges_are_thin_and_do_not_copy_secrets(self):
        private_dir = self.canonical / "config"
        private_dir.mkdir()
        private = private_dir / "runtime.local.toml"
        private.write_text("PRIVATE_TOML_FIXTURE\n")
        private.chmod(0o600)
        original_private = private.read_bytes()
        for agent in ("hermes", "codex", "claude", "generic"):
            with self.subTest(agent=agent):
                args = ["--agent", agent]
                if agent == "generic":
                    base = self.home / "custom skills"
                    args.extend(["--skills-dir", str(base)])
                    target = base / NAME / "SKILL.md"
                else:
                    target = self.destination(agent)
                code, out, err = self.invoke(*args)
                self.assertEqual(code, 0, err)
                text = target.read_text()
                for path in (self.root, self.canonical / "SKILL.md", self.root / ".venv" / "bin" / "python",
                             self.canonical / "scripts" / "pipeline.py"):
                    self.assertIn(str(path), text)
                self.assertIn("Before doing any work, read the canonical Skill", text)
                self.assertNotIn("CANONICAL BUSINESS RULES", text)
                self.assertNotIn("PRIVATE_TOML_FIXTURE", text + out + err)
                self.assertEqual([p.name for p in target.parent.iterdir()], ["SKILL.md"])
                self.assertFalse(target.is_symlink())
        self.assertEqual(private.read_bytes(), original_private)
        self.assertFalse((self.home / ".codex").exists())

    def test_hermes_home_targets_only_explicit_profile(self):
        other = self.home / ".hermes" / "profiles" / "do-not-touch" / "skills" / NAME
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text("OTHER PROFILE FIXTURE\n")
        before = snapshot(other)
        active = self.home / "chosen profile"
        with mock.patch.dict(os.environ, {"HERMES_HOME": str(active)}):
            code, _, err = self.invoke("--agent", "hermes")
        self.assertEqual(code, 0, err)
        self.assertTrue((active / "skills" / NAME / "SKILL.md").is_file())
        self.assertEqual(snapshot(other), before)
        self.assertFalse(self.destination("hermes").exists())

    def test_custom_skills_parent_overrides_all_explicit_agent_defaults(self):
        for agent in ("hermes", "codex", "claude", "generic"):
            with self.subTest(agent=agent):
                base = self.home / f"custom {agent}"
                code, _, err = self.invoke("--agent", agent, "--skills-dir", str(base))
                self.assertEqual(code, 0, err)
                self.assertTrue((base / NAME / "SKILL.md").is_file())
        for agent in ("hermes", "codex", "claude"):
            self.assertFalse(self.destination(agent).exists())

    def test_generic_requires_parent_and_project_rejects_parent(self):
        for args in (("--agent", "generic"), ("--skills-dir", str(self.home / "custom"))):
            with self.subTest(args=args):
                self.assert_conflict_untouched(*args)

    def test_bridge_shell_commands_quote_spaces_and_shell_metacharacters(self):
        code, _, err = self.invoke("--agent", "codex")
        self.assertEqual(code, 0, err)
        text = self.destination("codex").read_text()
        script = text.split("```sh\n", 1)[1].split("```", 1)[0].strip().splitlines()
        self.assertEqual(shlex.split(script[0]), ["cd", str(self.root)])
        self.assertEqual(shlex.split(script[1]), self.commands[-1])
        for command in self.commands:
            if command[0] != sys.executable:
                self.assertEqual(command[0], str(self.root / ".venv" / "bin" / "python"))

    def test_repeat_install_reuses_venv_env_and_identical_bridge(self):
        args = ("--agent", "hermes", "--skip-deps", "--skip-browser")
        code, _, err = self.invoke(*args)
        self.assertEqual(code, 0, err)
        bridge = self.destination("hermes")
        before = (bridge.stat().st_ino, bridge.stat().st_mtime_ns, bridge.read_bytes())
        env = self.root / ".env"
        env.write_text("CUSTOM=keep-me\n")
        self.commands.clear()
        code, out, err = self.invoke(*args)
        self.assertEqual(code, 0, err)
        self.assertEqual((bridge.stat().st_ino, bridge.stat().st_mtime_ns, bridge.read_bytes()), before)
        self.assertEqual(env.read_text(), "CUSTOM=keep-me\n")
        self.assertFalse(any("venv" in command or "pip" in command or "playwright" in command for command in self.commands))
        self.assertEqual(len(self.commands), 2)
        self.assertIn("Reused bridge:", out)

    def test_moved_checkout_conflicts_instead_of_repointing_existing_bridge(self):
        code, _, err = self.invoke("--agent", "hermes")
        self.assertEqual(code, 0, err)
        moved = self.base / "moved checkout"
        self.root.rename(moved)
        self.root = moved
        self.canonical = moved / NAME
        self.commands.clear()
        _, err = self.assert_conflict_untouched("--agent", "hermes")
        self.assertIn("checkout may have moved", err)

    def test_conflicting_bridge_is_rejected_before_installs_or_env_creation(self):
        bridge = self.destination("codex")
        bridge.parent.mkdir(parents=True)
        bridge.write_text("User-owned Skill, not generated by bootstrap\n")
        _, err = self.assert_conflict_untouched("--agent", "codex")
        self.assertIn("Conflict", err)
        self.assert_conflict_untouched("--agent", "codex", "--dry-run")
        self.assertFalse((self.root / ".env").exists())
        self.assertFalse((self.root / ".venv").exists())

    def test_bridge_symlink_is_rejected_even_when_contents_are_identical(self):
        bridge = self.destination("claude")
        bridge.parent.mkdir(parents=True)
        elsewhere = self.base / "elsewhere.md"
        elsewhere.write_text(bootstrap.bridge_text(self.root))
        bridge.symlink_to(elsewhere)
        self.assert_conflict_untouched("--agent", "claude")
        self.assertTrue(bridge.is_symlink())

    def test_skill_directory_symlink_is_rejected_and_never_followed(self):
        bridge = self.destination("hermes")
        bridge.parent.parent.mkdir(parents=True)
        bridge.parent.symlink_to(self.canonical, target_is_directory=True)
        self.assert_conflict_untouched("--agent", "hermes")

    def test_custom_parent_symlink_and_parent_file_are_rejected(self):
        for kind in ("symlink", "file"):
            with self.subTest(kind=kind):
                parent = self.home / kind
                if kind == "symlink":
                    parent.symlink_to(self.base, target_is_directory=True)
                else:
                    parent.write_text("not a directory\n")
                self.assert_conflict_untouched("--agent", "generic", "--skills-dir", str(parent))

    def test_nonempty_unmanaged_skill_directory_is_not_adopted(self):
        bridge = self.destination("hermes")
        bridge.parent.mkdir(parents=True)
        (bridge.parent / "private.txt").write_text("Unrelated private file\n")
        self.assert_conflict_untouched("--agent", "hermes")

    def test_env_symlink_or_hardlink_cannot_chmod_an_external_file(self):
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                other = self.base / f"{kind}-outside-env"
                other.write_text("EXTERNAL_FIXTURE=unchanged\n")
                other.chmod(0o644)
                env = self.root / ".env"
                if kind == "symlink":
                    env.symlink_to(other)
                else:
                    os.link(other, env)
                self.assert_conflict_untouched()
                self.assertEqual(stat.S_IMODE(other.stat().st_mode), 0o644)
                env.unlink()

    def test_env_directory_is_a_conflict_before_dependency_installation(self):
        (self.root / ".env").mkdir()
        self.assert_conflict_untouched()

    def test_missing_env_template_fails_before_side_effects(self):
        (self.root / ".env.example").unlink()
        self.assert_conflict_untouched()

    def test_missing_project_link_fails_without_recreating_it(self):
        link = self.root / ".agents" / "skills" / NAME
        link.unlink()
        self.assert_conflict_untouched()
        self.assertFalse(link.exists())

    def test_wrong_project_symlink_is_rejected(self):
        link = self.root / ".claude" / "skills" / NAME
        link.unlink()
        link.symlink_to("../../missing-canonical", target_is_directory=True)
        self.assert_conflict_untouched()
        self.assertEqual(os.readlink(link), "../../missing-canonical")

    def test_venv_symlink_or_incomplete_directory_is_rejected(self):
        venv = self.root / ".venv"
        venv.symlink_to(self.home, target_is_directory=True)
        self.assert_conflict_untouched()
        venv.unlink()
        venv.mkdir()
        self.assert_conflict_untouched()

    def test_reused_interpreter_must_be_311_and_inside_this_venv(self):
        self.fake_venv()
        for overrides in ({"version": [3, 10]},
                          {"prefix": "/fixture/global", "base_prefix": "/fixture/global"}):
            probe = self.probe_info() | overrides
            with self.subTest(probe=probe):
                self.probe = probe
                self.commands.clear()
                code, out, err = self.invoke()
                self.assertNotEqual(code, 0)
                self.assertEqual(len(self.commands), 1)
                self.assertIn("Invalid virtualenv Python", err)
                self.assertNotIn("Bootstrap complete", out)
                self.assertFalse((self.root / ".env").exists())

    def test_skip_flags_skip_only_requested_installations_not_preflight(self):
        for flags, expected_pip, expected_browser in ((["--skip-deps"], False, True),
                                                     (["--skip-browser"], True, False),
                                                     (["--skip-deps", "--skip-browser"], False, False)):
            with self.subTest(flags=flags):
                self.commands.clear()
                code, _, err = self.invoke(*flags)
                self.assertEqual(code, 0, err)
                self.assertEqual(any(command[1:3] == ["-m", "pip"] for command in self.commands), expected_pip)
                self.assertEqual(any(command[1:3] == ["-m", "playwright"] for command in self.commands), expected_browser)
                self.assertIn("preflight", self.commands[-1])

    def test_unsafe_inherited_pip_and_python_overrides_are_not_used(self):
        overrides = {key: str(self.home / "unsafe") for key in
                     ("PIP_TARGET", "PIP_PREFIX", "PIP_PYTHON", "PIP_ROOT", "PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE")}
        overrides["PIP_USER"] = "1"
        with mock.patch.dict(os.environ, overrides):
            code, _, err = self.invoke()
        self.assertEqual(code, 0, err)
        self.assertFalse((self.home / "unsafe").exists())

    def test_install_redirection_is_removed_but_network_settings_stay_private(self):
        redirects = ("PIP_PYTHON", "PIP_ROOT", "PIP_TARGET", "PIP_PREFIX", "PIP_SRC",
                     "PIP_BUILD", "PIP_BUILD_TRACKER", "PIP_INSTALL_OPTION", "PIP_GLOBAL_OPTION",
                     "PIP_BUILD_OPTION", "PIP_CONFIG_SETTINGS", "PIP_LOG", "PIP_REPORT",
                     "PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE", "PYTHONPLATLIBDIR",
                     "PYTHONEXECUTABLE", "__PYVENV_LAUNCHER__", "_PYTHON_PROJECT_BASE",
                     "_PYTHON_SYSCONFIGDATA_NAME", "_PYTHON_SYSCONFIGDATA_PATH")
        settings = {key: "private-network-fixture" for key in
                    ("PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_TRUSTED_HOST", "PIP_PROXY",
                     "PIP_CERT", "PIP_CLIENT_CERT", "HTTPS_PROXY", "REQUESTS_CA_BUNDLE",
                     "PIP_FIND_LINKS", "APPLICATION_CREDENTIAL")}
        settings["PIP_NO_INDEX"] = "1"
        with mock.patch.dict(os.environ, settings | dict.fromkeys(redirects, str(self.home / "unsafe"))):
            env = bootstrap.child_environment()
            for key in redirects:
                self.assertNotIn(key, env)
            for key, value in settings.items():
                self.assertEqual(env[key], value)
            code, out, err = self.invoke()
        self.assertEqual(code, 0, err)
        self.assertNotIn("private-network-fixture", out + err)

    def test_install_paths_must_resolve_within_the_current_venv(self):
        self.fake_venv()
        outside = self.base / "outside install directory"
        outside.mkdir()
        link = self.root / ".venv" / "escaped-library"
        link.symlink_to(outside, target_is_directory=True)
        loop = self.root / ".venv" / "loop"
        loop.symlink_to(loop, target_is_directory=True)
        for name in ("purelib", "platlib", "scripts", "data"):
            for path in (str(outside), "relative/install", str(link), str(link / "not-created"), str(loop), None):
                with self.subTest(name=name, path=path):
                    self.probe = self.probe_info()
                    self.probe["paths"][name] = path
                    self.commands.clear()
                    code, out, err = self.invoke()
                    self.assertNotEqual(code, 0)
                    self.assertEqual(len(self.commands), 1)
                    self.assertIn("Invalid virtualenv Python", err)
                    self.assertNotIn("Install Python dependencies", out)
                    self.assertFalse((self.root / ".env").exists())

    def test_missing_or_malformed_install_path_probe_fails_closed(self):
        self.fake_venv()
        for paths in (None, {}, [], {"purelib": str(self.root / ".venv")}):
            with self.subTest(paths=paths):
                self.probe = self.probe_info()
                self.probe["paths"] = paths
                self.commands.clear()
                code, _, err = self.invoke()
                self.assertNotEqual(code, 0)
                self.assertEqual(len(self.commands), 1)
                self.assertIn("Invalid virtualenv Python", err)
                self.assertFalse((self.root / ".env").exists())

    def test_internal_library_links_and_base_stdlib_paths_are_allowed(self):
        self.fake_venv()
        library = self.root / ".venv" / "lib"
        library.mkdir()
        alias = self.root / ".venv" / "lib64"
        alias.symlink_to("lib", target_is_directory=True)
        self.probe = self.probe_info()
        self.probe["paths"]["platlib"] = str(alias / "python3.11/site-packages")
        code, out, err = self.invoke()
        self.assertEqual(code, 0, err)
        self.assertIn("Bootstrap complete", out)

    def test_pip_failure_stops_before_browser_env_preflight_and_bridge(self):
        self.fail_on = "pip"
        code, out, err = self.invoke("--agent", "codex")
        self.assertNotEqual(code, 0)
        self.assertEqual(self.commands[-1][1:3], ["-m", "pip"])
        self.assertFalse((self.root / ".env").exists())
        self.assertFalse(self.destination("codex").exists())
        self.assertNotIn("Bootstrap complete", out)
        self.assertNotIn("PRIVATE-ERROR-FIXTURE", out + err)
        self.assertIn("exit 12", err)

    def test_venv_and_browser_failures_stop_before_env_and_bridge(self):
        for failure in ("venv", "browser"):
            with self.subTest(failure=failure):
                self.commands.clear()
                self.fail_on = failure
                code, out, err = self.invoke("--agent", "hermes")
                self.assertNotEqual(code, 0)
                self.assertFalse((self.root / ".env").exists())
                self.assertFalse(self.destination("hermes").exists())
                self.assertNotIn("Bootstrap complete", out)

    def test_preflight_failure_preserves_real_report_and_returns_nonzero(self):
        self.preflight_code = 1
        self.report.update(ready=False, failures=["playwright_chromium"],
                           checks=[{"name": "playwright_chromium", "status": "missing", "required": True}])
        code, out, err = self.invoke("--agent", "hermes", "--skip-browser")
        self.assertNotEqual(code, 0)
        self.assertIn('"ready": false', out)
        self.assertIn('"status": "missing"', out)
        self.assertIn("did not pass", err)
        self.assertFalse(self.destination("hermes").exists())
        self.assertNotIn("Bootstrap complete", out)

    def test_false_ready_with_zero_exit_still_fails(self):
        self.report.update(ready=False, failures=["fixture-check"])
        code, out, _ = self.invoke()
        self.assertNotEqual(code, 0)
        self.assertIn('"ready": false', out)
        self.assertNotIn("Bootstrap complete", out)

    def test_true_ready_with_nonzero_exit_is_not_claimed_as_success(self):
        self.preflight_code = 9
        code, out, err = self.invoke()
        self.assertNotEqual(code, 0)
        self.assertNotIn('"ready": true', out)
        self.assertNotIn("Bootstrap complete", out)
        self.assertIn("inconsistent", err)

    def test_preflight_invalid_json_suppresses_potentially_private_output(self):
        self.preflight_code = 2
        self.raw_preflight = "PRIVATE-ERROR-FIXTURE not json"
        code, out, err = self.invoke()
        self.assertNotEqual(code, 0)
        self.assertNotIn("PRIVATE-ERROR-FIXTURE", out + err)
        self.assertIn("no valid prepare-only JSON report", err)

    def test_old_python_and_native_windows_fail_before_side_effects(self):
        with mock.patch.object(bootstrap.sys, "version_info", (3, 10, 9)):
            _, err = self.assert_conflict_untouched()
            self.assertIn("Python 3.11+", err)
        # Patch the guard while keeping pathlib's concrete PosixPath implementation.
        with mock.patch.object(bootstrap.os, "name", "nt"):
            code, out, err = self.invoke()
        self.assertNotEqual(code, 0)
        self.assertIn("WSL", err)
        self.assertEqual(self.commands, [])
        self.assertFalse((self.root / ".env").exists())

    def test_actual_cli_dry_run_finds_checkout_when_called_from_elsewhere(self):
        scripts = self.root / "scripts"
        scripts.mkdir()
        target = scripts / "bootstrap.py"
        shutil.copyfile(SOURCE, target)
        before = snapshot(self.base)
        result = subprocess.run([sys.executable, "-B", str(target), "--dry-run", "--agent", "codex"],
                                cwd=self.home, env=os.environ.copy(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot(self.base), before)
        self.assertIn(str(self.root), result.stdout)
        self.assertIn(str(self.destination("codex")), result.stdout)
        self.assertIn("Preflight NOT RUN", result.stdout)

    def test_actual_cli_with_real_isolated_venv_and_fixture_preflight(self):
        # This creates a stdlib-only venv in the fixture: no pip, browser, network,
        # actual repository config, or global agent directory is involved.
        created = subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(self.root / ".venv")],
                                 cwd=self.root, env=os.environ.copy(), capture_output=True, text=True)
        self.assertEqual(created.returncode, 0, created.stderr)
        scripts = self.root / "scripts"
        scripts.mkdir()
        target = scripts / "bootstrap.py"
        shutil.copyfile(SOURCE, target)
        (self.canonical / "scripts" / "pipeline.py").write_text(
            "import json, sys\n"
            "assert sys.argv[-4:] == ['preflight', '--mode', 'prepare-only', '--json']\n"
            "assert sys.argv[1] == '--workspace'\n"
            f"print(json.dumps({self.report!r}))\n"
        )
        result = subprocess.run([sys.executable, "-B", str(target), "--agent", "codex", "--skip-deps", "--skip-browser"],
                                cwd=self.home, env=os.environ.copy(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.destination("codex").is_file())
        self.assertIn('"ready": true', result.stdout)
        self.assertEqual(stat.S_IMODE((self.root / ".env").stat().st_mode), 0o600)
        self.assertIn("Bootstrap complete", result.stdout)

    def real_venv(self, path):
        # venv uses ensurepip's bundled wheels: no installer download is needed.
        env = os.environ.copy() | {"PIP_NO_INDEX": "1", "PIP_CONFIG_FILE": os.devnull,
                                  "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1"}
        created = subprocess.run([sys.executable, "-B", "-m", "venv", str(path)],
                                 cwd=self.root, env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(created.returncode, 0, created.stderr)
        probe = subprocess.run([str(path / "bin/python"), "-B", "-c",
                                "import json, sysconfig; print(json.dumps(sysconfig.get_paths()))"],
                               cwd=self.root, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(probe.returncode, 0, probe.stderr)
        return {key: Path(value) for key, value in json.loads(probe.stdout).items()}

    def local_wheel_install(self):
        """Build a declared test fixture wheel with stdlib only, then use real pip."""
        package = "bootstrap_isolation_fixture"
        dist = f"{package}-1.0.dist-info"
        files = {
            f"{package}.py": b"def main():\n    print('offline-wheel-fixture')\n",
            f"{dist}/METADATA": b"Metadata-Version: 2.1\nName: bootstrap-isolation-fixture\nVersion: 1.0\n",
            f"{dist}/WHEEL": b"Wheel-Version: 1.0\nGenerator: offline-test-fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            f"{dist}/entry_points.txt": b"[console_scripts]\nbootstrap-isolation-fixture = bootstrap_isolation_fixture:main\n",
            f"{package}-1.0.data/data/share/bootstrap-isolation-fixture.txt": b"offline-data-fixture\n",
        }
        record = io.StringIO(newline="")
        writer = csv.writer(record)
        for name, content in files.items():
            digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode("ascii")
            writer.writerow([name, f"sha256={digest}", len(content)])
        writer.writerow([f"{dist}/RECORD", "", ""])
        files[f"{dist}/RECORD"] = record.getvalue().encode("utf-8")
        wheel = self.base / f"{package}-1.0-py3-none-any.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        (self.root / "requirements.txt").write_text(f"--no-index\n--only-binary=:all:\n{wheel.as_uri()}\n")
        paths = self.real_venv(self.root / ".venv")
        scripts = self.root / "scripts"
        scripts.mkdir()
        target = scripts / "bootstrap.py"
        shutil.copyfile(SOURCE, target)
        (self.canonical / "scripts/pipeline.py").write_text(
            "import json\nimport bootstrap_isolation_fixture\n"
            f"print(json.dumps({self.report!r}))\n"
        )
        return target, paths

    def run_local_wheel_install(self, target, **overrides):
        env = os.environ.copy() | {"PIP_NO_INDEX": "1", "PIP_NO_DEPS": "1"} | overrides
        return subprocess.run([sys.executable, "-B", str(target), "--skip-browser"],
                              cwd=self.home, env=env, capture_output=True, text=True, timeout=90)

    def assert_local_wheel_installed(self, result, paths):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Install Python dependencies", result.stdout)
        self.assertIn("Bootstrap complete", result.stdout)
        self.assertTrue((paths["purelib"] / "bootstrap_isolation_fixture.py").is_file())
        self.assertTrue((paths["scripts"] / "bootstrap-isolation-fixture").is_file())
        self.assertEqual((paths["data"] / "share/bootstrap-isolation-fixture.txt").read_text(), "offline-data-fixture\n")

    def test_real_offline_wheel_installs_into_local_venv(self):
        target, paths = self.local_wheel_install()
        result = self.run_local_wheel_install(target)
        self.assert_local_wheel_installed(result, paths)

    def test_real_offline_pip_python_cannot_redirect_to_another_venv(self):
        target, paths = self.local_wheel_install()
        other = self.base / "other real venv"
        other_paths = self.real_venv(other)
        result = self.run_local_wheel_install(target, PIP_PYTHON=str(other / "bin/python"))
        self.assertFalse((other_paths["purelib"] / "bootstrap_isolation_fixture.py").exists(),
                         "PIP_PYTHON wrote the local wheel into the other real venv")
        self.assertFalse((other_paths["scripts"] / "bootstrap-isolation-fixture").exists())
        self.assertFalse((other_paths["data"] / "share/bootstrap-isolation-fixture.txt").exists())
        self.assert_local_wheel_installed(result, paths)

    def test_real_offline_pip_root_cannot_redirect_outside_the_checkout(self):
        target, paths = self.local_wheel_install()
        outside = self.base / "alternate install root"
        outside.mkdir()
        result = self.run_local_wheel_install(target, PIP_ROOT=str(outside))
        self.assertEqual(list(outside.iterdir()), [], "PIP_ROOT wrote outside the checkout")
        self.assert_local_wheel_installed(result, paths)

    def test_real_offline_symlinked_site_packages_is_rejected_before_pip(self):
        target, paths = self.local_wheel_install()
        outside = self.base / "outside site-packages"
        # Move pip with the directory so the vulnerable version can really run
        # pip and write the fixture wheel through the redirected site-packages.
        shutil.move(str(paths["purelib"]), str(outside))
        paths["purelib"].symlink_to(outside, target_is_directory=True)
        result = self.run_local_wheel_install(target)
        self.assertFalse((outside / "bootstrap_isolation_fixture.py").exists(),
                         "pip followed site-packages and installed outside the venv")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid virtualenv Python", result.stderr)
        self.assertNotIn("Install Python dependencies", result.stdout)
        self.assertNotIn("Bootstrap complete", result.stdout)
        self.assertFalse((self.root / ".env").exists())


if __name__ == "__main__":
    unittest.main()
