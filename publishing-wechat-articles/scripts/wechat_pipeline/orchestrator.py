from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

from .capture import archive_capture, capture_source
from .config import RepositoryConfig
from .cover import build_cover_html, render_cover_png
from .manifest import ManifestError, RunManifest
from .local_media import resolve_local_images
from .models import Stage
from .quality import check_article
from .render import render_markdown
from .security import normalize_slug, safe_output_path
from .title_quality import check_title
from .voice import (
    VoiceError,
    load_evidence_ids,
    load_voice_profile,
    validate_article_personal_claims,
    validate_author_brief,
    validate_voice_review,
)


class PipelineError(RuntimeError):
    pass


class Pipeline:
    def __init__(
        self,
        config: RepositoryConfig,
        workspace_root: Path | None = None,
        external_hook=None,
        cover_renderer=render_cover_png,
    ):
        self.config = config
        self.workspace_root = (workspace_root or config.repository_root / "workspace").resolve()
        self.runs_root = self.workspace_root / "runs"
        self._external_hook = external_hook
        self._cover_renderer = cover_renderer

    def _run_dir(self, run_id: str) -> Path:
        return safe_output_path(self.runs_root, run_id)

    def _manifest_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "manifest.json"

    def plan(
        self,
        title: str,
        summary: str,
        account: str = "auto",
        *,
        tags: str = "",
        mode: str = "prepare-only",
        run_id: str | None = None,
        author_voice: bool = False,
    ) -> RunManifest:
        routed = self.config.route_account(account, title, tags)
        if author_voice and mode == "collect-only":
            raise PipelineError("author voice requires prepare-only or publish mode")
        voice_profile = load_voice_profile(self.config, routed) if author_voice else None
        identifier = run_id or self._new_run_id(title)
        run_dir = self._run_dir(identifier)
        if run_dir.exists():
            raise PipelineError(f"run already exists: {identifier}")
        run_dir.mkdir(parents=True)
        manifest = RunManifest.create(identifier, mode, routed, title, summary)
        if voice_profile is not None:
            context_path = run_dir / "voice-context.json"
            self._write_json(context_path, voice_profile.to_dict())
            manifest.enable_author_voice(voice_profile.profile_version, voice_profile.profile_sha256)
            manifest.record_artifact("voice_context", context_path, run_dir)
        manifest.save(run_dir / "manifest.json")
        return manifest

    def ingest_brief(self, run_id: str, input_path: Path) -> RunManifest:
        manifest = self.status(run_id)
        self._require_voice_editable(manifest)
        payload = self._read_json(input_path, "author brief")
        voice_root = self.workspace_root / "vaults" / manifest.account / "voice"
        try:
            normalized = validate_author_brief(
                payload,
                expected_profile_sha256=manifest.editorial["profile_sha256"],
                evidence_ids=load_evidence_ids(voice_root),
            )
        except VoiceError as exc:
            raise PipelineError(str(exc)) from exc

        run_dir = self._run_dir(run_id)
        output_path = run_dir / "author-brief.json"
        self._write_json(output_path, normalized)
        manifest.record_artifact("author_brief", output_path, run_dir)
        manifest.editorial["brief_status"] = "ready"
        manifest.editorial["review_status"] = "missing"
        manifest.artifacts.pop("voice_review", None)
        (run_dir / "voice-review.json").unlink(missing_ok=True)
        manifest.save(run_dir / "manifest.json")
        return manifest

    def ingest_voice_review(self, run_id: str, input_path: Path) -> RunManifest:
        manifest = self.status(run_id)
        self._require_voice_editable(manifest)
        if manifest.editorial.get("brief_status") != "ready":
            raise PipelineError("author brief is required before voice review")
        run_dir = self._run_dir(run_id)
        article_path = run_dir / "article.md"
        if not article_path.is_file():
            raise PipelineError(f"editorial Markdown is required: {article_path}")
        article_hash = self._sha256(article_path)
        payload = self._read_json(input_path, "voice review")
        try:
            normalized = validate_voice_review(
                payload,
                expected_article_sha256=article_hash,
                article_markdown=article_path.read_text(encoding="utf-8"),
            )
        except VoiceError as exc:
            raise PipelineError(str(exc)) from exc

        output_path = run_dir / "voice-review.json"
        self._write_json(output_path, normalized)
        manifest.record_artifact("voice_review", output_path, run_dir)
        manifest.editorial["review_status"] = normalized["decision"]
        manifest.save(run_dir / "manifest.json")
        return manifest

    def capture(self, run_id: str, url: str, *, fetcher=None) -> RunManifest:
        manifest = self.status(run_id)
        if manifest.state != Stage.PLANNED:
            raise PipelineError(f"capture requires planned state, got {manifest.state.value}")
        kwargs = {} if fetcher is None else {"fetcher": fetcher}
        captured = capture_source(url, **kwargs)
        run_dir = self._run_dir(run_id)
        outputs = archive_capture(captured, run_dir / "source")
        for name, path in outputs.items():
            manifest.record_artifact(f"source_{name}", path, run_dir)
        manifest.transition(Stage.CAPTURED)
        manifest.save(run_dir / "manifest.json")
        return manifest

    def prepare(self, run_id: str, *, render_png: bool = True) -> RunManifest:
        manifest = self.status(run_id)
        if manifest.state == Stage.RENDERED:
            return manifest
        if manifest.state not in {Stage.PLANNED, Stage.CAPTURED, Stage.WRITTEN, Stage.NEEDS_REVIEW}:
            raise PipelineError(f"prepare cannot run from {manifest.state.value}")
        run_dir = self._run_dir(run_id)
        article_path = run_dir / "article.md"
        if not article_path.is_file():
            raise PipelineError(f"editorial Markdown is required: {article_path}")

        if manifest.state == Stage.NEEDS_REVIEW:
            manifest.transition(Stage.WRITTEN)
        else:
            manifest.transition(Stage.WRITTEN)
        manifest.record_artifact("article_markdown", article_path, run_dir)
        manifest.save(run_dir / "manifest.json")

        research_path = run_dir / "research.json"
        if research_path.exists() or "research_dossier" in manifest.artifacts:
            from .research import check_research
            try:
                report = check_research(json.loads(research_path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                report = {"passed": False, "findings": ["research.json is missing or invalid"]}
            report_path = run_dir / "research-quality.json"
            self._write_json(report_path, report)
            manifest.record_artifact("research_quality_report", report_path, run_dir)
            if research_path.is_file():
                manifest.record_artifact("research_dossier", research_path, run_dir)
            if not report["passed"]:
                manifest.transition(Stage.NEEDS_REVIEW)
                manifest.save(run_dir / "manifest.json")
                raise PipelineError("research evidence checks contain blocking findings")
            manifest.save(run_dir / "manifest.json")

        if manifest.requires_voice:
            self._verify_voice_gate(manifest, run_dir, article_path)

        markdown = article_path.read_text(encoding="utf-8")
        markdown, media = resolve_local_images(
            markdown, run_dir, bucket=self.config.oss.bucket, endpoint=self.config.oss.endpoint,
            prefix=self.config.oss.prefix, account=manifest.account, title=manifest.title,
        )
        media_path = run_dir / "media.json"
        if media:
            self._write_json(media_path, {"images": media})
            manifest.record_artifact("media_manifest", media_path, run_dir)
        else:
            media_path.unlink(missing_ok=True)
            manifest.artifacts.pop("media_manifest", None)
        manifest.save(run_dir / "manifest.json")
        title_report = check_title(manifest.title, markdown)
        title_quality_path = run_dir / "title-quality.json"
        title_quality_path.write_text(
            json.dumps(title_report.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        manifest.record_artifact("title_quality_report", title_quality_path, run_dir)
        manifest.save(run_dir / "manifest.json")
        if not title_report.passed:
            manifest.transition(Stage.NEEDS_REVIEW)
            manifest.save(run_dir / "manifest.json")
            raise PipelineError("title quality checks contain blocking findings")

        profile = self.config.accounts[manifest.account]
        theme_css = (self.config.skill_root / profile.theme_file).read_text(encoding="utf-8")
        rendered = render_markdown(markdown, theme_css, title=manifest.title)
        article_html = run_dir / "article.html"
        article_html.write_text(rendered, encoding="utf-8")
        report = check_article(
            markdown,
            rendered,
            author_voice=manifest.requires_voice,
            account=manifest.account,
        )
        quality_path = run_dir / "quality.json"
        quality_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest.record_artifact("quality_report", quality_path, run_dir)
        if not report.passed:
            manifest.transition(Stage.NEEDS_REVIEW)
            manifest.save(run_dir / "manifest.json")
            raise PipelineError("quality checks contain blocking findings")
        manifest.transition(Stage.CHECKED)
        manifest.save(run_dir / "manifest.json")

        design_path = run_dir / "cover-design.html"
        if design_path.is_file():
            template = design_path.read_text(encoding="utf-8")
            manifest.record_artifact("cover_design", design_path, run_dir)
        else:
            template = (self.config.skill_root / profile.cover_template).read_text(encoding="utf-8")
        cover_html_text = build_cover_html(
            template,
            title=manifest.title,
            summary=manifest.summary,
            tag=profile.theme_name,
            brand=profile.display_name,
            accent=manifest.account,
        )
        cover_html = run_dir / "cover.html"
        cover_html.write_text(cover_html_text, encoding="utf-8")
        if render_png:
            cover_png = self._cover_renderer(cover_html_text, run_dir / "cover.png")
            manifest.record_artifact("cover_png", cover_png, run_dir)
        manifest.record_artifact("article_html", article_html, run_dir)
        manifest.record_artifact("cover_html", cover_html, run_dir)
        manifest.transition(Stage.RENDERED)
        manifest.save(run_dir / "manifest.json")
        return manifest

    def retitle(self, run_id: str, title: str, summary: str | None = None) -> RunManifest:
        manifest = self.status(run_id)
        run_dir = self._run_dir(run_id)
        try:
            manifest.revise_title(title, summary, article_exists=(run_dir / "article.md").is_file())
        except ManifestError as exc:
            raise PipelineError(str(exc)) from exc
        for name in ("title-quality.json", "quality.json", "article.html", "cover.html", "cover.png"):
            (run_dir / name).unlink(missing_ok=True)
        manifest.save(run_dir / "manifest.json")
        return manifest

    def status(self, run_id: str) -> RunManifest:
        path = self._manifest_path(run_id)
        if not path.is_file():
            raise PipelineError(f"run not found: {run_id}")
        return RunManifest.load(path)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _read_json(path: Path, label: str) -> object:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PipelineError(f"invalid {label} input: {path}") from exc

    @staticmethod
    def _sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _verify_voice_gate(self, manifest: RunManifest, run_dir: Path, article_path: Path) -> None:
        if manifest.editorial.get("brief_status") != "ready" or "author_brief" not in manifest.artifacts:
            self._fail_voice_gate(manifest, run_dir, "author brief is required", brief_status="missing")
        if manifest.editorial.get("review_status") == "revise":
            self._fail_voice_gate(manifest, run_dir, "voice review must pass before prepare")
        if manifest.editorial.get("review_status") != "pass" or "voice_review" not in manifest.artifacts:
            self._fail_voice_gate(manifest, run_dir, "voice review is required", review_status="missing")

        for name in ("voice_context", "author_brief", "voice_review"):
            self._verify_recorded_artifact(manifest, run_dir, name)

        brief_path = run_dir / manifest.artifacts["author_brief"]["path"]
        review_path = run_dir / manifest.artifacts["voice_review"]["path"]
        brief = self._read_json(brief_path, "author brief")
        review = self._read_json(review_path, "voice review")
        voice_root = self.workspace_root / "vaults" / manifest.account / "voice"
        try:
            normalized_brief = validate_author_brief(
                brief,
                expected_profile_sha256=manifest.editorial["profile_sha256"],
                evidence_ids=load_evidence_ids(voice_root),
            )
            validate_article_personal_claims(
                article_path.read_text(encoding="utf-8"),
                normalized_brief,
            )
            validate_voice_review(
                review,
                expected_article_sha256=self._sha256(article_path),
                article_markdown=article_path.read_text(encoding="utf-8"),
            )
        except VoiceError as exc:
            if "article_sha256" in str(exc):
                self._fail_voice_gate(manifest, run_dir, "stale voice review", review_status="stale")
            self._fail_voice_gate(manifest, run_dir, str(exc))
        if review["decision"] != "pass":
            self._fail_voice_gate(manifest, run_dir, "voice review must pass before prepare")

    def _verify_recorded_artifact(self, manifest: RunManifest, run_dir: Path, name: str) -> None:
        artifact = manifest.artifacts.get(name)
        if not artifact or not isinstance(artifact.get("path"), str):
            self._fail_voice_gate(manifest, run_dir, f"{name} artifact is missing")
        path = (run_dir / artifact["path"]).resolve()
        try:
            path.relative_to(run_dir.resolve())
        except ValueError:
            self._fail_voice_gate(manifest, run_dir, f"{name} artifact path is invalid")
        if not path.is_file() or self._sha256(path) != artifact.get("sha256"):
            self._fail_voice_gate(manifest, run_dir, f"{name} artifact changed after validation")

    @staticmethod
    def _fail_voice_gate(
        manifest: RunManifest,
        run_dir: Path,
        message: str,
        *,
        brief_status: str | None = None,
        review_status: str | None = None,
    ) -> None:
        if brief_status is not None:
            manifest.editorial["brief_status"] = brief_status
        if review_status is not None:
            manifest.editorial["review_status"] = review_status
        manifest.transition(Stage.NEEDS_REVIEW)
        manifest.errors.append({"stage": "author_voice", "message": message})
        manifest.save(run_dir / "manifest.json")
        raise PipelineError(message)

    @staticmethod
    def _require_voice_editable(manifest: RunManifest) -> None:
        if not manifest.requires_voice:
            raise PipelineError("author voice is not enabled for this run")
        if manifest.state in {
            Stage.RENDERED,
            Stage.UPLOADED,
            Stage.HANDED_OFF,
            Stage.RECORDED,
            Stage.PUBLISHED,
            Stage.NEEDS_RECONCILE,
        }:
            raise PipelineError(f"author voice cannot be revised from {manifest.state.value}")

    @staticmethod
    def _new_run_id(title: str) -> str:
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{date}-{normalize_slug(title)}-{uuid.uuid4().hex[:8]}"
