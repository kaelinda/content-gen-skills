from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .models import Stage


class ManifestError(RuntimeError):
    pass


TRANSITIONS = {
    Stage.PLANNED: {Stage.CAPTURED, Stage.WRITTEN},
    Stage.CAPTURED: {Stage.WRITTEN},
    Stage.WRITTEN: {Stage.CHECKED, Stage.NEEDS_REVIEW},
    Stage.CHECKED: {Stage.RENDERED, Stage.NEEDS_REVIEW},
    Stage.RENDERED: {Stage.UPLOADED, Stage.NEEDS_RECONCILE},
    Stage.UPLOADED: {Stage.HANDED_OFF, Stage.NEEDS_RECONCILE},
    Stage.HANDED_OFF: {Stage.RECORDED, Stage.NEEDS_RECONCILE},
    Stage.RECORDED: {Stage.PUBLISHED, Stage.NEEDS_RECONCILE},
    Stage.NEEDS_REVIEW: {Stage.WRITTEN},
    Stage.NEEDS_RECONCILE: {Stage.UPLOADED, Stage.HANDED_OFF, Stage.RECORDED},
    Stage.PUBLISHED: set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class RunManifest:
    run_id: str
    authorization_mode: str
    account: str
    title: str
    summary: str
    state: Stage = Stage.PLANNED
    schema_version: int = 1
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    external: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    @classmethod
    def create(cls, run_id: str, mode: str, account: str, title: str, summary: str) -> "RunManifest":
        if mode not in {"collect-only", "prepare-only", "publish"}:
            raise ManifestError(f"unknown authorization mode: {mode}")
        return cls(run_id=run_id, authorization_mode=mode, account=account, title=title, summary=summary)

    def transition(self, state: Stage) -> None:
        if state == self.state:
            return
        if state not in TRANSITIONS[self.state]:
            raise ManifestError(f"invalid transition: {self.state.value} -> {state.value}")
        self.state = state
        self.updated_at = _now()

    def record_artifact(self, name: str, path: Path, run_dir: Path) -> None:
        resolved_path = path.resolve()
        try:
            relative = resolved_path.relative_to(run_dir.resolve())
        except ValueError as exc:
            raise ManifestError(f"artifact is outside run directory: {path}") from exc
        digest = hashlib.sha256(resolved_path.read_bytes()).hexdigest()
        self.artifacts[name] = {"path": relative.as_posix(), "sha256": digest, "size": resolved_path.stat().st_size}
        self.updated_at = _now()

    def revise_title(self, title: str, summary: str | None, *, article_exists: bool) -> None:
        if self.state in {Stage.UPLOADED, Stage.HANDED_OFF, Stage.RECORDED, Stage.PUBLISHED, Stage.NEEDS_RECONCILE}:
            raise ManifestError(f"title cannot be revised from state {self.state.value}")
        clean_title = " ".join(title.split())
        if not clean_title:
            raise ManifestError("title cannot be empty")
        self.title = clean_title
        if summary is not None:
            self.summary = summary.strip()
        for name in ("title_quality_report", "quality_report", "article_html", "cover_html", "cover_png"):
            self.artifacts.pop(name, None)
        if article_exists:
            self.state = Stage.WRITTEN
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "authorization_mode": self.authorization_mode,
            "account": self.account,
            "title": self.title,
            "summary": self.summary,
            "state": self.state.value,
            "artifacts": self.artifacts,
            "external": self.external,
            "errors": self.errors,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        payload = json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    @classmethod
    def load(cls, path: Path) -> "RunManifest":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if int(data["schema_version"]) != 1:
                raise ManifestError(f"unsupported manifest schema: {data['schema_version']}")
            return cls(
                schema_version=1,
                run_id=data["run_id"],
                authorization_mode=data["authorization_mode"],
                account=data["account"],
                title=data["title"],
                summary=data["summary"],
                state=Stage(data["state"]),
                artifacts=data.get("artifacts", {}),
                external=data.get("external", {}),
                errors=data.get("errors", []),
                created_at=data["created_at"],
                updated_at=data["updated_at"],
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ManifestError(f"invalid manifest: {path}") from exc
