from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .capture import archive_capture, capture_source
from .config import RepositoryConfig
from .cover import build_cover_html, render_cover_png
from .manifest import ManifestError, RunManifest
from .models import Stage
from .quality import check_article
from .render import render_markdown
from .security import normalize_slug, safe_output_path
from .title_quality import check_title


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
    ) -> RunManifest:
        routed = self.config.route_account(account, title, tags)
        identifier = run_id or self._new_run_id(title)
        run_dir = self._run_dir(identifier)
        if run_dir.exists():
            raise PipelineError(f"run already exists: {identifier}")
        run_dir.mkdir(parents=True)
        manifest = RunManifest.create(identifier, mode, routed, title, summary)
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

        markdown = article_path.read_text(encoding="utf-8")
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
        report = check_article(markdown, rendered)
        quality_path = run_dir / "quality.json"
        quality_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest.record_artifact("quality_report", quality_path, run_dir)
        if not report.passed:
            manifest.transition(Stage.NEEDS_REVIEW)
            manifest.save(run_dir / "manifest.json")
            raise PipelineError("quality checks contain blocking findings")
        manifest.transition(Stage.CHECKED)
        manifest.save(run_dir / "manifest.json")

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
    def _new_run_id(title: str) -> str:
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{date}-{normalize_slug(title)}-{uuid.uuid4().hex[:8]}"
