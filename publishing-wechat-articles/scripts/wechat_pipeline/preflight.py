from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
from pathlib import Path

from .config import RepositoryConfig
from .voice import VoiceError, load_voice_profile


RECORD_FIELDS = {
    "tech": ["内容", "是否已发布", "标题", "摘要", "封面"],
    "parenting": ["是否已发布", "标题", "摘要", "封面", "内容"],
}


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    status: str
    required: bool
    detail: str = ""


@dataclass(frozen=True)
class PreflightReport:
    mode: str
    account: str
    checks: tuple[PreflightCheck, ...]

    @property
    def failures(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.checks if item.required and item.status != "ok")

    @property
    def ready(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "account": self.account,
            "record_fields": RECORD_FIELDS[self.account],
            "ready": self.ready,
            "failures": list(self.failures),
            "checks": [asdict(item) for item in self.checks],
        }


def _path_check(name: str, path: Path) -> PreflightCheck:
    return PreflightCheck(name, "ok" if path.is_file() else "missing", True, str(path))


def playwright_available() -> bool:
    if importlib.util.find_spec("playwright") is None:
        return False
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            return Path(playwright.chromium.executable_path).is_file()
    except Exception:
        return False


def run_preflight(
    config: RepositoryConfig,
    mode: str,
    account: str,
    *,
    author_voice: bool = False,
    playwright_available: bool | None = None,
) -> PreflightReport:
    if mode not in {"collect-only", "prepare-only", "publish"}:
        raise ValueError(f"unknown mode: {mode}")
    if account not in config.accounts:
        raise ValueError(f"unknown account: {account}")
    if author_voice and mode == "collect-only":
        raise ValueError("author voice requires prepare-only or publish mode")
    profile = config.accounts[account]
    module_root = config.skill_root / "scripts" / "wechat_pipeline"
    checks = [
        _path_check("accounts_config", config.skill_root / "config" / "accounts.toml"),
        _path_check("capture_module", module_root / "capture.py"),
        _path_check("quality_module", module_root / "quality.py"),
        _path_check("title_quality_module", module_root / "title_quality.py"),
    ]
    if mode in {"prepare-only", "publish"}:
        checks.extend(
            [
                _path_check("render_module", module_root / "render.py"),
                _path_check("cover_module", module_root / "cover.py"),
                _path_check("theme_file", config.skill_root / profile.theme_file),
                _path_check("cover_template", config.skill_root / profile.cover_template),
            ]
        )
        available = globals()["playwright_available"]() if playwright_available is None else playwright_available
        checks.append(PreflightCheck("playwright_chromium", "ok" if available else "missing", True))
        if author_voice:
            author_check = _path_check("voice_profile", config.skill_root / config.voice_author_path)
            account_check = _path_check(
                "voice_account_profile",
                config.skill_root / config.voice_accounts_root / f"{account}.toml",
            )
            if author_check.status == "ok" and account_check.status == "ok":
                try:
                    load_voice_profile(config, account)
                except VoiceError:
                    author_check = PreflightCheck("voice_profile", "invalid", True)
            checks.extend([author_check, account_check])
    if mode == "publish":
        runtime = config.runtime
        target = runtime.accounts.get(account)
        oss_ready = bool(runtime.oss_access_key_id and runtime.oss_access_key_secret)
        app_id = runtime.tech_app_id if account == "tech" else runtime.parenting_app_id
        app_secret = runtime.tech_app_secret if account == "tech" else runtime.parenting_app_secret
        checks.extend(
            [
                PreflightCheck("runtime_permissions", "ok" if config.runtime_path.stat().st_mode & 0o777 == 0o600 else "invalid", True),
                PreflightCheck("oss_credentials", "ok" if oss_ready else "missing", True),
                PreflightCheck("feishu_credentials", "ok" if app_id and app_secret else "missing", True),
                PreflightCheck(
                    "feishu_target",
                    "ok" if target and target.base_token and target.table_id and (target.chat_id or runtime.primary_chat_id) else "missing",
                    True,
                ),
            ]
        )
        if config.runtime_source == "environment":
            checks = tuple(
                PreflightCheck(
                    item.name,
                    "ok" if item.name == "runtime_permissions" else item.status,
                    item.required,
                    "environment variables" if item.name == "runtime_permissions" else item.detail,
                )
                for item in checks
            )
    return PreflightReport(mode, account, tuple(checks))
