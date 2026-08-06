from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import tomllib
from typing import Any

from .config import RepositoryConfig


class VoiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class VoiceProfile:
    schema_version: int
    profile_version: str
    account: str
    author: dict[str, object]
    language: dict[str, object]
    overlay: dict[str, object]
    profile_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "profile_version": self.profile_version,
            "account": self.account,
            "author": self.author,
            "language": self.language,
            "overlay": self.overlay,
            "profile_sha256": self.profile_sha256,
        }


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise VoiceError(f"invalid voice configuration: {path}") from exc


def load_voice_profile(config: RepositoryConfig, account: str) -> VoiceProfile:
    if account not in config.accounts:
        raise VoiceError(f"unknown account: {account}")
    author_path = config.skill_root / config.voice_author_path
    overlay_path = config.skill_root / config.voice_accounts_root / f"{account}.toml"
    author = _read_toml(author_path)
    overlay = _read_toml(overlay_path)
    if int(author.get("schema_version", 0)) != 1 or int(overlay.get("schema_version", 0)) != 1:
        raise VoiceError("unsupported voice profile schema")
    if not isinstance(author.get("author"), dict) or not isinstance(author.get("language"), dict):
        raise VoiceError("author voice profile is incomplete")
    if not isinstance(overlay.get("account"), dict):
        raise VoiceError(f"account voice overlay is incomplete: {account}")

    canonical = json.dumps(
        {"author": author, "account": account, "overlay": overlay},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return VoiceProfile(
        schema_version=1,
        profile_version=str(author.get("profile_version", "")),
        account=account,
        author=dict(author["author"]),
        language=dict(author["language"]),
        overlay=dict(overlay["account"]),
        profile_sha256=hashlib.sha256(canonical).hexdigest(),
    )


def _require_keys(payload: dict[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(payload))
    extra = sorted(set(payload) - expected)
    if missing or extra:
        raise VoiceError(f"invalid {label} keys: missing={missing}, extra={extra}")


def _require_string(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise VoiceError(f"{name} must be a non-empty string")
    return value.strip()


def _require_string_list(payload: dict[str, Any], name: str) -> list[str]:
    value = payload.get(name)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise VoiceError(f"{name} must be a list of non-empty strings")
    return [item.strip() for item in value]


def _require_hash(value: object, name: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise VoiceError(f"{name} must be a SHA-256 digest")
    return value


def load_evidence_ids(voice_root: Path) -> set[str]:
    index_path = voice_root / "evidence.toml"
    if not index_path.is_file():
        return set()
    data = _read_toml(index_path)
    if int(data.get("schema_version", 0)) != 1 or not isinstance(data.get("evidence", []), list):
        raise VoiceError("invalid evidence index schema")

    resolved_root = voice_root.resolve()
    identifiers: set[str] = set()
    for raw in data.get("evidence", []):
        if not isinstance(raw, dict):
            raise VoiceError("invalid evidence entry")
        identifier = raw.get("id")
        relative = raw.get("path")
        if not isinstance(identifier, str) or not identifier.strip():
            raise VoiceError("evidence id must be a non-empty string")
        if identifier in identifiers:
            raise VoiceError(f"duplicate evidence id: {identifier}")
        if not isinstance(relative, str) or not relative.strip() or Path(relative).is_absolute():
            raise VoiceError(f"invalid evidence path: {identifier}")
        evidence_path = (voice_root / relative).resolve()
        try:
            evidence_path.relative_to(resolved_root)
        except ValueError as exc:
            raise VoiceError(f"evidence path is outside voice vault: {identifier}") from exc
        if not evidence_path.is_file():
            raise VoiceError(f"evidence file is missing: {identifier}")
        identifiers.add(identifier)
    return identifiers


def validate_author_brief(
    payload: object,
    *,
    expected_profile_sha256: str,
    evidence_ids: set[str],
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise VoiceError("author brief must be a JSON object")
    expected = {
        "schema_version",
        "profile_sha256",
        "reader_problem",
        "source_baseline",
        "incremental_value",
        "thesis",
        "tension",
        "reasoning_moves",
        "evidence_refs",
        "personal_claims",
        "counterpoint",
        "excluded_directions",
        "title_candidates",
    }
    _require_keys(payload, expected, "author brief")
    if payload.get("schema_version") != 1:
        raise VoiceError("unsupported author brief schema")
    profile_hash = _require_hash(payload.get("profile_sha256"), "profile_sha256")
    if profile_hash != expected_profile_sha256:
        raise VoiceError("profile_sha256 does not match this run")

    for name in (
        "reader_problem",
        "source_baseline",
        "incremental_value",
        "thesis",
        "tension",
        "counterpoint",
    ):
        _require_string(payload, name)
    reasoning_moves = _require_string_list(payload, "reasoning_moves")
    if len(reasoning_moves) < 2:
        raise VoiceError("reasoning_moves must contain at least two items")
    evidence_refs = _require_string_list(payload, "evidence_refs")
    missing_refs = sorted(set(evidence_refs) - evidence_ids)
    if missing_refs:
        raise VoiceError(f"unknown evidence reference: {missing_refs[0]}")
    _require_string_list(payload, "excluded_directions")
    titles = _require_string_list(payload, "title_candidates")
    if len(titles) != 3 or len(set(titles)) != 3:
        raise VoiceError("title_candidates must contain three distinct titles")

    claims = payload.get("personal_claims")
    if not isinstance(claims, list):
        raise VoiceError("personal_claims must be a list")
    for claim in claims:
        if not isinstance(claim, dict):
            raise VoiceError("personal_claims entries must be objects")
        _require_keys(claim, {"claim", "evidence_id"}, "personal claim")
        _require_string(claim, "claim")
        evidence_id = _require_string(claim, "evidence_id")
        if evidence_id not in evidence_ids:
            raise VoiceError(f"unknown personal-claim evidence: {evidence_id}")
    return json.loads(json.dumps(payload, ensure_ascii=False))


def validate_article_personal_claims(article_markdown: str, brief: dict[str, object]) -> None:
    code_free = re.sub(r"```[\s\S]*?```", "", article_markdown)
    code_free = re.sub(r"`[^`\n]+`", "", code_free)
    experience_pattern = re.compile(r"(?:我|我们)(?:曾经|曾|亲自|遇到过|做过|踩过)")
    approved = [
        str(item["claim"]).strip()
        for item in brief.get("personal_claims", [])
        if isinstance(item, dict) and isinstance(item.get("claim"), str)
    ]
    for sentence in re.split(r"[。！？\n]+", code_free):
        clean = sentence.strip()
        if not clean or experience_pattern.search(clean) is None:
            continue
        if not any(claim in clean or clean in claim for claim in approved):
            raise VoiceError(f"undeclared personal experience in article: {clean}")


def validate_voice_review(
    payload: object,
    *,
    expected_article_sha256: str,
    article_markdown: str,
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise VoiceError("voice review must be a JSON object")
    expected = {
        "schema_version",
        "article_sha256",
        "decision",
        "dimensions",
        "blockers",
        "anonymous_paragraphs",
    }
    _require_keys(payload, expected, "voice review")
    if payload.get("schema_version") != 1:
        raise VoiceError("unsupported voice review schema")
    article_hash = _require_hash(payload.get("article_sha256"), "article_sha256")
    if article_hash != expected_article_sha256:
        raise VoiceError("article_sha256 does not match the current article")
    decision = payload.get("decision")
    if decision not in {"pass", "revise"}:
        raise VoiceError("decision must be pass or revise")

    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, list):
        raise VoiceError("dimensions must be a list")
    expected_names = {"attention", "judgment", "reasoning", "evidence", "language"}
    seen: set[str] = set()
    all_present = True
    for dimension in dimensions:
        if not isinstance(dimension, dict):
            raise VoiceError("dimension entries must be objects")
        _require_keys(dimension, {"name", "status", "excerpts", "note"}, "review dimension")
        name = _require_string(dimension, "name")
        if name not in expected_names or name in seen:
            raise VoiceError(f"invalid or duplicate review dimension: {name}")
        seen.add(name)
        status = dimension.get("status")
        if status not in {"present", "weak", "missing"}:
            raise VoiceError(f"invalid review dimension status: {name}")
        all_present = all_present and status == "present"
        excerpts = _require_string_list(dimension, "excerpts")
        if not excerpts:
            raise VoiceError(f"excerpts are required for review dimension: {name}")
        for excerpt in excerpts:
            if excerpt not in article_markdown:
                raise VoiceError(f"review excerpt is not in article: {name}")
        _require_string(dimension, "note")
    if seen != expected_names:
        raise VoiceError("all five review dimensions are required")

    blockers = _require_string_list(payload, "blockers")
    anonymous = _require_string_list(payload, "anonymous_paragraphs")
    if decision == "pass" and (not all_present or blockers or anonymous):
        raise VoiceError("pass decision requires present dimensions and no blockers")
    return json.loads(json.dumps(payload, ensure_ascii=False))
