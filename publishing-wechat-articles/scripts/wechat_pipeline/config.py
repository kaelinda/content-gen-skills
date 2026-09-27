from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class OssConfig:
    bucket: str
    endpoint: str
    prefix: str


@dataclass(frozen=True)
class AccountProfile:
    name: str
    display_name: str
    theme_name: str
    theme_file: Path
    cover_template: Path
    vault_default: Path
    keywords: tuple[str, ...]

    def vault_path(self, repository_root: Path) -> Path:
        return repository_root / self.vault_default


@dataclass(frozen=True)
class RuntimeAccount:
    chat_id: str
    base_token: str
    table_id: str


@dataclass(frozen=True)
class ImageGenerationConfig:
    enabled: bool = False
    endpoint: str = "https://api.openai.com/v1/images/generations"
    api_key: str = field(default="", repr=False)
    model: str = "gpt-image-2"
    timeout_seconds: float = 120
    allowed_download_hosts: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeConfig:
    oss_access_key_id: str
    oss_access_key_secret: str
    feishu_mode: str
    primary_chat_id: str
    tech_app_id: str
    tech_app_secret: str
    parenting_app_id: str
    parenting_app_secret: str
    accounts: dict[str, RuntimeAccount]
    image_generation: ImageGenerationConfig = field(default_factory=ImageGenerationConfig)


@dataclass(frozen=True)
class RepositoryConfig:
    skill_root: Path
    repository_root: Path
    runtime_path: Path
    voice_author_path: Path
    voice_accounts_root: Path
    schema_version: int
    oss: OssConfig
    runtime: RuntimeConfig
    accounts: dict[str, AccountProfile]
    runtime_source: str = "file"

    def route_account(self, requested: str, title: str, tags: str) -> str:
        if requested != "auto":
            if requested not in self.accounts:
                raise ValueError(f"unknown account: {requested}")
            return requested
        haystack = f"{title} {tags}".lower()
        scores = {
            name: sum(keyword.lower() in haystack for keyword in profile.keywords)
            for name, profile in self.accounts.items()
        }
        best = max(scores, key=lambda name: (scores[name], name == "tech"))
        return best if scores[best] else "tech"


def load_repository_config(skill_root: Path | None = None) -> RepositoryConfig:
    resolved_skill = (skill_root or Path(__file__).resolve().parents[2]).resolve()
    config_path = resolved_skill / "config" / "accounts.toml"
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    private_runtime_path = resolved_skill / "config" / "runtime.local.toml"
    runtime_path = (
        private_runtime_path
        if private_runtime_path.is_file()
        else resolved_skill / "config" / "runtime.example.toml"
    )
    runtime_data = tomllib.loads(runtime_path.read_text(encoding="utf-8"))
    env_used = False

    def env_value(*names: str, default: str = "") -> str:
        nonlocal env_used
        for name in names:
            value = os.getenv(name)
            if value is not None:
                env_used = True
                return value
        return default

    def env_bool(*names: str, default: bool = False) -> bool:
        raw = env_value(*names, default="")
        if not raw:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    def env_float(*names: str, default: float) -> float:
        raw = env_value(*names, default="")
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError as exc:
            raise ValueError(f"invalid numeric environment variable: {names[0]}") from exc

    def env_hosts(*names: str, default: tuple[str, ...]) -> tuple[str, ...]:
        raw = env_value(*names, default="")
        if not raw:
            return default
        return tuple(item.strip() for item in raw.split(",") if item.strip())
    accounts = {
        name: AccountProfile(
            name=name,
            display_name=raw["display_name"],
            theme_name=raw["theme_name"],
            theme_file=Path(raw["theme_file"]),
            cover_template=Path(raw["cover_template"]),
            vault_default=Path(raw["vault_default"]),
            keywords=tuple(raw["keywords"]),
        )
        for name, raw in data["accounts"].items()
    }
    endpoint_override = env_value("OSS_ENDPOINT", "WECHAT_OSS_ENDPOINT", default="")
    region_override = env_value("OSS_REGION", "WECHAT_OSS_REGION", default="")
    oss_endpoint = endpoint_override or (
        f"oss-{region_override}.aliyuncs.com" if region_override else data["oss"]["endpoint"]
    )
    return RepositoryConfig(
        skill_root=resolved_skill,
        repository_root=resolved_skill.parent,
        runtime_path=runtime_path,
        voice_author_path=Path("config/voice/author.toml"),
        voice_accounts_root=Path("config/voice/accounts"),
        schema_version=int(data["schema_version"]),
        oss=OssConfig(
            bucket=env_value("OSS_BUCKET", "WECHAT_OSS_BUCKET", default=data["oss"]["bucket"]),
            endpoint=oss_endpoint,
            prefix=env_value("OSS_PREFIX", "WECHAT_OSS_PREFIX", default=data["oss"]["prefix"]),
        ),
        runtime=RuntimeConfig(
            oss_access_key_id=env_value("OSS_ACCESS_KEY_ID", "WECHAT_OSS_ACCESS_KEY_ID", default=runtime_data["oss"]["access_key_id"]),
            oss_access_key_secret=env_value("OSS_ACCESS_KEY_SECRET", "WECHAT_OSS_ACCESS_KEY_SECRET", default=runtime_data["oss"]["access_key_secret"]),
            feishu_mode=env_value("FEISHU_MODE", "WECHAT_FEISHU_MODE", default=runtime_data["feishu"]["mode"]),
            primary_chat_id=env_value("FEISHU_PRIMARY_CHAT_ID", "WECHAT_FEISHU_PRIMARY_CHAT_ID", default=runtime_data["feishu"]["primary_chat_id"]),
            tech_app_id=env_value("FEISHU_TECH_APP_ID", "WECHAT_FEISHU_TECH_APP_ID", default=runtime_data["feishu"]["tech_app_id"]),
            tech_app_secret=env_value("FEISHU_TECH_APP_SECRET", "WECHAT_FEISHU_TECH_APP_SECRET", default=runtime_data["feishu"]["tech_app_secret"]),
            parenting_app_id=env_value("FEISHU_PARENTING_APP_ID", "WECHAT_FEISHU_PARENTING_APP_ID", default=runtime_data["feishu"]["parenting_app_id"]),
            parenting_app_secret=env_value("FEISHU_PARENTING_APP_SECRET", "WECHAT_FEISHU_PARENTING_APP_SECRET", default=runtime_data["feishu"]["parenting_app_secret"]),
            accounts={
                "tech": RuntimeAccount(
                    chat_id=env_value("FEISHU_TECH_CHAT_ID", "WECHAT_TECH_CHAT_ID", default=runtime_data["accounts"]["tech"]["chat_id"]),
                    base_token=env_value("FEISHU_TECH_BASE_ID", "FEISHU_TECH_BASE_TOKEN", "FEISHU_BASE_ID", "WECHAT_TECH_BASE_TOKEN", default=runtime_data["accounts"]["tech"]["base_token"]),
                    table_id=env_value("FEISHU_TECH_TABLE_ID", "WECHAT_TECH_TABLE_ID", default=runtime_data["accounts"]["tech"]["table_id"]),
                ),
                "parenting": RuntimeAccount(
                    chat_id=env_value("FEISHU_PARENTING_CHAT_ID", "WECHAT_PARENTING_CHAT_ID", default=runtime_data["accounts"]["parenting"]["chat_id"]),
                    base_token=env_value("FEISHU_PARENTING_BASE_ID", "FEISHU_PARENTING_BASE_TOKEN", "FEISHU_BASE_ID", "WECHAT_PARENTING_BASE_TOKEN", default=runtime_data["accounts"]["parenting"]["base_token"]),
                    table_id=env_value("FEISHU_PARENTING_TABLE_ID", "WECHAT_PARENTING_TABLE_ID", default=runtime_data["accounts"]["parenting"]["table_id"]),
                ),
            },
            image_generation=ImageGenerationConfig(
                enabled=env_bool("IMAGE_ENABLED", "WECHAT_IMAGE_ENABLED", default=runtime_data.get("image_generation", {}).get("enabled", False)),
                endpoint=env_value("IMAGE_API_BASE", "IMAGE_ENDPOINT", "WECHAT_IMAGE_ENDPOINT", default=runtime_data.get("image_generation", {}).get("endpoint", "https://api.openai.com/v1/images/generations")),
                api_key=env_value("OPENAI_API_KEY", "IMAGE_API_KEY", "WECHAT_IMAGE_API_KEY", default=runtime_data.get("image_generation", {}).get("api_key", "")),
                model=env_value("IMAGE_MODEL", "WECHAT_IMAGE_MODEL", default=runtime_data.get("image_generation", {}).get("model", "gpt-image-2")),
                timeout_seconds=env_float("IMAGE_TIMEOUT_SECONDS", "WECHAT_IMAGE_TIMEOUT_SECONDS", default=runtime_data.get("image_generation", {}).get("timeout_seconds", 120)),
                allowed_download_hosts=env_hosts("IMAGE_ALLOWED_DOWNLOAD_HOSTS", "WECHAT_IMAGE_ALLOWED_DOWNLOAD_HOSTS", default=tuple(runtime_data.get("image_generation", {}).get("allowed_download_hosts", ()))),
            ),
        ),
        accounts=accounts,
        runtime_source="environment" if env_used else "file",
    )
