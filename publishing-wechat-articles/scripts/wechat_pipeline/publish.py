from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
from pathlib import Path
import urllib.error

from .feishu import FeishuClient
from .oss import OssClient

from .manifest import RunManifest
from .models import Stage
from .security import normalize_slug


class PublishError(RuntimeError):
    pass


class AmbiguousExternalError(PublishError):
    pass


class Publisher:
    def __init__(self, oss, feishu, *, prefix: str = "wechat", require_verification: bool = False):
        self.oss = oss
        self.feishu = feishu
        self.prefix = prefix.strip("/")
        # Old injected adapters still work, but cannot produce verified receipts.
        # Production clients can never opt out by passing False.
        self.require_verification = bool(require_verification or isinstance(oss, OssClient)
                                         or isinstance(feishu, FeishuClient)
                                         or callable(getattr(oss, "verify_artifact", None)))

    def _check_verifiers(self) -> None:
        if self.require_verification:
            for client, name in ((self.oss, "verify_artifact"), (self.feishu, "verify_handoff"),
                                 (self.feishu, "verify_tracking")):
                if not callable(getattr(client, name, None)):
                    raise PublishError(f"required production verification adapter is missing: {name}")

    def _readback(self, manifest, manifest_path, name, method, *args) -> None:
        verifier = getattr(self.feishu, method, None)
        if not callable(verifier):
            manifest.external[name] = {"verified": False, "reason": "legacy adapter has no readback"}
        else:
            try:
                receipt = verifier(manifest.account, *args)
                if not isinstance(receipt, dict) or receipt.get("verified") is not True:
                    raise PublishError("readback did not supply verified evidence")
                manifest.external[name] = receipt
            except Exception as exc:
                raise AmbiguousExternalError(f"{name} failed; exact remote target needs reconciliation") from exc
        manifest.save(manifest_path)

    @staticmethod
    @contextmanager
    def _delivery_lock(manifest_path: Path):
        # All sibling runs in the repository workspace use the same durable queue.
        with (manifest_path.parent.parent / ".delivery.lock").open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _destination(self, account: str) -> str:
        resolver = getattr(self.feishu, "destination_key", None)
        return resolver(account) if callable(resolver) else f"legacy-account:{account}"

    @staticmethod
    def _confirmed(manifest: RunManifest) -> bool:
        confirmation = manifest.external.get("downstream_confirmation", {})
        if (confirmation.get("title") != manifest.title
                or confirmation.get("message_id") != manifest.external.get("message_id")
                or confirmation.get("confirmed_by") not in {"human", "publishing-assistant"}
                or not isinstance(confirmation.get("evidence"), str) or not confirmation["evidence"].strip()):
            return False
        required = {"wechat-draft": "draft_id", "public-publication": "publication_url"}.get(confirmation.get("kind"))
        return bool(required and isinstance(confirmation.get(required), str) and confirmation[required].strip())

    def _check_serial_queue(self, manifest: RunManifest, manifest_path: Path) -> None:
        destination = self._destination(manifest.account)
        for other_path in sorted(manifest_path.parent.parent.glob("*/manifest.json")):
            if other_path.resolve() == manifest_path.resolve():
                continue
            try:
                other = RunManifest.load(other_path)
            except Exception as exc:
                raise PublishError("unresolved unreadable workspace receipt; reconcile before dispatch") from exc
            delivery = other.external.get("delivery", {})
            active = (other.external.get("message_id") or delivery.get("status")
                      or other.state == Stage.NEEDS_RECONCILE)
            if not active or self._confirmed(other):
                continue
            other_destination = delivery.get("destination_key") or self._destination(other.account)
            if other_destination == destination:
                raise PublishError(f"unresolved downstream delivery in run {other.run_id}; confirm it before the next article")

    def confirm_downstream(self, manifest_path: Path, confirmation: dict[str, object]) -> RunManifest:
        """Import explicitly supplied human/assistant evidence; never infer it from API success.

        This is local-only. The CLI must gate import on explicit confirmation and
        obtain the exact downstream draft/publication evidence before calling.
        """
        manifest_path = Path(manifest_path).resolve()
        with self._delivery_lock(manifest_path):
            manifest = RunManifest.load(manifest_path)
            if manifest.state != Stage.RECORDED:
                raise PublishError("downstream confirmation requires a verified recorded handoff")
            for key in ("handoff_verification", "tracking_verification"):
                if manifest.external.get(key, {}).get("verified") is not True:
                    raise PublishError("downstream confirmation requires verified delivery readbacks")
            candidate = dict(confirmation)
            manifest.external["downstream_confirmation"] = candidate
            if not self._confirmed(manifest):
                raise PublishError("confirmation requires exact title, message_id, source evidence and draft_id or publication URL")
            candidate["confirmed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            status = "draft-confirmed"
            if candidate["kind"] == "public-publication":
                from urllib.parse import urlsplit
                parsed = urlsplit(candidate["publication_url"])
                if parsed.scheme != "https" or parsed.hostname != "mp.weixin.qq.com" or parsed.username or parsed.password:
                    raise PublishError("public publication requires an exact HTTPS WeChat article URL")
                status = "publication-confirmed"
                manifest.transition(Stage.PUBLISHED)
            manifest.external.setdefault("delivery", {})["status"] = status
            manifest.save(manifest_path)
            return manifest

    def publish(self, manifest_path: Path) -> RunManifest:
        manifest_path = Path(manifest_path).resolve()
        with self._delivery_lock(manifest_path):
            return self._publish_locked(manifest_path)

    def _publish_locked(self, manifest_path: Path) -> RunManifest:
        manifest = RunManifest.load(manifest_path)
        run_dir = manifest_path.parent
        if manifest.authorization_mode != "publish":
            raise PublishError("manifest is not authorized for publish mode")
        if manifest.state == Stage.NEEDS_RECONCILE:
            raise PublishError("run needs manual reconciliation before retry")
        if manifest.state not in {Stage.RENDERED, Stage.UPLOADED, Stage.HANDED_OFF, Stage.RECORDED}:
            raise PublishError(f"run is not publishable from state {manifest.state.value}")
        self._check_verifiers()
        if not manifest.external.get("message_id"):
            self._check_serial_queue(manifest, manifest_path)
        if manifest.state == Stage.RECORDED and not self.require_verification:
            return manifest

        try:
            if manifest.state == Stage.RENDERED:
                self._ensure_uploads(manifest, manifest_path, run_dir)
                manifest.transition(Stage.UPLOADED)
                manifest.save(manifest_path)
            elif self.require_verification:
                self._ensure_uploads(manifest, manifest_path, run_dir)

            if manifest.state == Stage.UPLOADED:
                message_id = manifest.external.get("message_id")
                if not message_id:
                    delivery = manifest.external.setdefault("delivery", {})
                    if delivery.get("status") == "dispatching":
                        raise AmbiguousExternalError("previous handoff attempt has no durable message ID")
                    delivery.update({"status": "dispatching", "destination_key": self._destination(manifest.account)})
                    manifest.save(manifest_path)
                    message_id = self.feishu.send_handoff(
                        manifest.account,
                        manifest.title,
                        manifest.summary,
                        manifest.external["cover_url"],
                        manifest.external["html_url"],
                    )
                    manifest.external["message_id"] = message_id
                    manifest.save(manifest_path)
            if manifest.state in {Stage.UPLOADED, Stage.HANDED_OFF, Stage.RECORDED}:
                self._readback(manifest, manifest_path, "handoff_verification", "verify_handoff",
                               manifest.external["message_id"], manifest.title, manifest.summary,
                               manifest.external["cover_url"], manifest.external["html_url"])
                if manifest.state == Stage.UPLOADED:
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
            if manifest.state in {Stage.HANDED_OFF, Stage.RECORDED}:
                self._readback(manifest, manifest_path, "tracking_verification", "verify_tracking",
                               manifest.external["record_id"], self._tracking_fields(manifest))
                manifest.transition(Stage.RECORDED)
                if not self._confirmed(manifest):
                    manifest.external.setdefault("delivery", {})["status"] = "pending-downstream"
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
            artifact = manifest.artifacts.get(artifact_name)
            if not artifact:
                raise PublishError(f"required artifact missing: {artifact_name}")
            from .security import safe_output_path
            path = safe_output_path(run_dir, artifact["path"])
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != artifact.get("sha256"):
                raise PublishError(f"local artifact changed after preparation: {artifact_name}")
            url = manifest.external.get(external_name)
            if not url:
                extension = ".png" if kind == "cover" else ".html"
                digest = hashlib.sha256(data).hexdigest()[:16]
                slug = normalize_slug(manifest.title)
                key = f"{self.prefix}/{manifest.account}/{slug}-{digest}-{kind}{extension}"
                url = self.oss.upload(key, data, content_type)
                manifest.external[external_name] = url
                manifest.external[external_name.replace("_url", "_key")] = key
                manifest.save(manifest_path)
            expected = "image/" if kind == "cover" else "text/html"
            verifier = getattr(self.oss, "verify_artifact", None)
            if callable(verifier):
                receipt = verifier(url, expected, data)
                if not isinstance(receipt, dict) or receipt.get("verified") is not True or receipt.get("sha256") != hashlib.sha256(data).hexdigest():
                    raise PublishError(f"uploaded {kind} has no byte-verification evidence")
            else:
                if not self.oss.verify(url, expected):
                    raise PublishError(f"uploaded {kind} is not publicly verifiable")
                receipt = {"verified": False, "reason": "legacy adapter only checks metadata"}
            manifest.external.setdefault("upload_verification", {})[external_name] = receipt
            manifest.save(manifest_path)

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
