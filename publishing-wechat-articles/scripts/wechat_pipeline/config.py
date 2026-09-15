from __future__ import annotations

from dataclasses import dataclass, field
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
    return RepositoryConfig(
        skill_root=resolved_skill,
        repository_root=resolved_skill.parent,
        runtime_path=runtime_path,
        voice_author_path=Path("config/voice/author.toml"),
        voice_accounts_root=Path("config/voice/accounts"),
        schema_version=int(data["schema_version"]),
        oss=OssConfig(**data["oss"]),
        runtime=RuntimeConfig(
            oss_access_key_id=runtime_data["oss"]["access_key_id"],
            oss_access_key_secret=runtime_data["oss"]["access_key_secret"],
            feishu_mode=runtime_data["feishu"]["mode"],
            primary_chat_id=runtime_data["feishu"]["primary_chat_id"],
            tech_app_id=runtime_data["feishu"]["tech_app_id"],
            tech_app_secret=runtime_data["feishu"]["tech_app_secret"],
            parenting_app_id=runtime_data["feishu"]["parenting_app_id"],
            parenting_app_secret=runtime_data["feishu"]["parenting_app_secret"],
            accounts={name: RuntimeAccount(**raw) for name, raw in runtime_data["accounts"].items()},
            image_generation=ImageGenerationConfig(
                enabled=runtime_data.get("image_generation", {}).get("enabled", False),
                endpoint=runtime_data.get("image_generation", {}).get(
                    "endpoint", "https://api.openai.com/v1/images/generations"),
                api_key=runtime_data.get("image_generation", {}).get("api_key", ""),
                model=runtime_data.get("image_generation", {}).get("model", "gpt-image-2"),
                timeout_seconds=runtime_data.get("image_generation", {}).get("timeout_seconds", 120),
                allowed_download_hosts=tuple(runtime_data.get("image_generation", {}).get(
                    "allowed_download_hosts", ())),
            ),
        ),
        accounts=accounts,
    )
