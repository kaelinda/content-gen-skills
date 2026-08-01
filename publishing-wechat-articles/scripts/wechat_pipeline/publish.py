from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
import urllib.error

from .manifest import RunManifest
from .models import Stage
from .security import normalize_slug


class PublishError(RuntimeError):
    pass


class AmbiguousExternalError(PublishError):
    pass


class Publisher:
    def __init__(self, oss, feishu, *, prefix: str = "wechat"):
        self.oss = oss
        self.feishu = feishu
        self.prefix = prefix.strip("/")

    def publish(self, manifest_path: Path) -> RunManifest:
        manifest = RunManifest.load(manifest_path)
        run_dir = manifest_path.parent
        if manifest.authorization_mode != "publish":
            raise PublishError("manifest is not authorized for publish mode")
        if manifest.state == Stage.NEEDS_RECONCILE:
            raise PublishError("run needs manual reconciliation before retry")
        if manifest.state not in {Stage.RENDERED, Stage.UPLOADED, Stage.HANDED_OFF, Stage.RECORDED}:
            raise PublishError(f"run is not publishable from state {manifest.state.value}")
        if manifest.state == Stage.RECORDED:
            return manifest

        try:
            if manifest.state == Stage.RENDERED:
                self._ensure_uploads(manifest, manifest_path, run_dir)
                manifest.transition(Stage.UPLOADED)
                manifest.save(manifest_path)

            if manifest.state == Stage.UPLOADED:
                message_id = manifest.external.get("message_id")
                if not message_id:
                    message_id = self.feishu.send_handoff(
                        manifest.account,
                        manifest.title,
                        manifest.summary,
                        manifest.external["cover_url"],
                        manifest.external["html_url"],
                    )
                    manifest.external["message_id"] = message_id
                    manifest.save(manifest_path)
                manifest.transition(Stage.HANDED_OFF)
                manifest.save(manifest_path)

            if manifest.state == Stage.HANDED_OFF:
                record_id = manifest.external.get("record_id")
                if not record_id:
                    record_id = self.feishu.create_tracking(
                        manifest.account,
                        self._tracking_fields(manifest),
                    )
                    manifest.external["record_id"] = record_id
                    manifest.save(manifest_path)
                manifest.transition(Stage.RECORDED)
                manifest.save(manifest_path)
            return manifest
        except (AmbiguousExternalError, TimeoutError, urllib.error.URLError) as exc:
            if manifest.state != Stage.NEEDS_RECONCILE:
                manifest.transition(Stage.NEEDS_RECONCILE)
                manifest.errors.append({"type": "ambiguous-external-result", "message": str(exc)})
                manifest.save(manifest_path)
            raise PublishError("external result is ambiguous; manual reconciliation required") from exc

    def _ensure_uploads(self, manifest: RunManifest, manifest_path: Path, run_dir: Path) -> None:
        entries = (
            ("cover_url", "cover_png", "cover", "image/png"),
            ("html_url", "article_html", "article", "text/html; charset=utf-8"),
        )
        for external_name, artifact_name, kind, content_type in entries:
            url = manifest.external.get(external_name)
            if not url:
                artifact = manifest.artifacts.get(artifact_name)
                if not artifact:
                    raise PublishError(f"required artifact missing: {artifact_name}")
                path = run_dir / artifact["path"]
                data = path.read_bytes()
                extension = ".png" if kind == "cover" else ".html"
                digest = hashlib.sha256(data).hexdigest()[:16]
                slug = normalize_slug(manifest.title)
                key = f"{self.prefix}/{manifest.account}/{slug}-{digest}-{kind}{extension}"
                url = self.oss.upload(key, data, content_type)
                manifest.external[external_name] = url
                manifest.external[external_name.replace("_url", "_key")] = key
                manifest.save(manifest_path)
            expected = "image/" if kind == "cover" else "text/html"
            if not self.oss.verify(url, expected):
                raise PublishError(f"uploaded {kind} is not publicly verifiable")

    @staticmethod
    def _tracking_fields(manifest: RunManifest) -> dict[str, object]:
        values = {
            "内容": manifest.external["html_url"],
            "是否已发布": False,
            "标题": manifest.title,
            "摘要": manifest.summary,
            "封面": manifest.external["cover_url"],
        }
        order = (
            ("内容", "是否已发布", "标题", "摘要", "封面")
            if manifest.account == "tech"
            else ("是否已发布", "标题", "摘要", "封面", "内容")
        )
        return {name: values[name] for name in order}
