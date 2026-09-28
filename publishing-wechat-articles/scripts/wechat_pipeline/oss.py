from __future__ import annotations

import base64
from email.utils import formatdate
import hashlib
import hmac
from html.parser import HTMLParser
from pathlib import PurePosixPath
import re
import ssl
import urllib.parse
import urllib.error
import urllib.request

from .config import RepositoryConfig
from .security import validate_public_url


class OssError(RuntimeError):
    pass


class OssClient:
    def __init__(self, bucket: str, endpoint: str, access_key_id: str, access_key_secret: str, *, transport=None):
        self.bucket = bucket
        self.endpoint = endpoint.removeprefix("https://").removeprefix("http://").rstrip("/")
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.transport = transport or self._default_transport

    @classmethod
    def from_repository_config(cls, config: RepositoryConfig, *, transport=None) -> "OssClient":
        return cls(
            config.oss.bucket,
            config.oss.endpoint,
            config.runtime.oss_access_key_id,
            config.runtime.oss_access_key_secret,
            transport=transport,
        )

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        key = str(PurePosixPath(key)).lstrip("/")
        if not key or key.startswith("../") or "/../" in key:
            raise OssError("invalid OSS object key")
        date = formatdate(usegmt=True)
        content_md5 = base64.b64encode(hashlib.md5(data).digest()).decode("ascii")
        canonical = f"PUT\n{content_md5}\n{content_type}\n{date}\n/{self.bucket}/{key}"
        signature = base64.b64encode(
            hmac.new(self.access_key_secret.encode(), canonical.encode(), hashlib.sha1).digest()
        ).decode("ascii")
        url = f"https://{self.bucket}.{self.endpoint}/{urllib.parse.quote(key, safe='/')}"
        request = urllib.request.Request(url, data=data, method="PUT")
        request.add_header("Date", date)
        request.add_header("Content-MD5", content_md5)
        request.add_header("Content-Type", content_type)
        request.add_header("Authorization", f"OSS {self.access_key_id}:{signature}")
        status, _, body = self.transport(request, 30)
        if status < 200 or status >= 300:
            raise OssError(f"OSS upload failed with HTTP {status}: {body[:200]!r}")
        return url

    def verify(self, url: str, expected: str) -> bool:
        validate_public_url(url)
        request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "content-gen-skills/1.0"})
        status, headers, _ = self.transport(request, 15)
        content_type = headers.get("content-type", "").lower()
        return status == 200 and content_type.startswith(expected.lower())

    def is_absent(self, url: str) -> bool:
        """Read the exact public object address for a failed pre-handoff upload."""
        validate_public_url(url)
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "content-gen-skills/1.0"})
        try:
            status, _, _ = self.transport(request, 15)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return True
            raise OssError(f"object absence could not be verified: HTTP {exc.code}") from exc
        if status == 404:
            return True
        if status == 200:
            return False
        raise OssError(f"object absence could not be verified: HTTP {status}")

    def verify_artifact(self, url: str, expected: str, local_bytes: bytes) -> dict[str, object]:
        """Read public bytes, not HEAD metadata; never claim browser preview."""
        receipt, remote_bytes = self._read_public(url, expected)
        if remote_bytes != local_bytes:
            raise OssError("public artifact bytes differ from the local artifact")
        receipt["images"] = []
        if expected.split(";", 1)[0].lower() == "text/html":
            parser = _ImageReferences()
            parser.feed(remote_bytes.decode("utf-8"))
            base = urllib.parse.urljoin(url, parser.base or url)
            references = sorted({urllib.parse.urljoin(base, source) for source in parser.sources})
            for image_url in references:
                image_receipt, _ = self._read_public(image_url, "image/")
                receipt["images"].append(image_receipt)
        return receipt

    def _read_public(self, url: str, expected: str) -> tuple[dict[str, object], bytes]:
        validate_public_url(url)
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "content-gen-skills/1.0"})
        status, headers, body = self.transport(request, 25)
        headers = {key.lower(): value for key, value in headers.items()}
        content_type = headers.get("content-type", "").lower().split(";", 1)[0].strip()
        expected = expected.lower().split(";", 1)[0].strip()
        matches = content_type.startswith(expected) if expected.endswith("/") else content_type == expected
        if status != 200 or not matches or not body:
            raise OssError("public GET did not return nonempty bytes with the expected MIME type")
        return {
            "url": url, "method": "GET", "status": status,
            "content_type": content_type, "content_disposition": headers.get("content-disposition", ""),
            "sha256": hashlib.sha256(body).hexdigest(), "size": len(body),
            "verified": True, "browser_preview": "not-claimed",
        }, body

    @staticmethod
    def _default_transport(request: urllib.request.Request, timeout: int):
        # Reject redirects rather than following an unvalidated destination.
        import certifi
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(
            context=ssl.create_default_context(cafile=certifi.where())))
        with opener.open(request, timeout=timeout) as response:
            return int(response.status), {key.lower(): value for key, value in response.headers.items()}, response.read()


class _ImageReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources: list[str] = []
        self.base: str | None = None
        self.in_style = False

    def _css(self, value: str) -> None:
        self.sources.extend(match[1].strip() for match in re.findall(r"url\(\s*(['\"]?)(.*?)\1\s*\)", value, re.I))

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "base" and self.base is None:
            self.base = values.get("href")
        if tag in {"img", "image"}:
            source = values.get("src") or values.get("href") or values.get("xlink:href")
            if not source:
                raise OssError("embedded image has no verifiable source")
            self.sources.append(source)
        if tag in {"img", "source"} and values.get("srcset"):
            for entry in values["srcset"].split(","):
                if not entry.strip():
                    raise OssError("empty embedded image candidate")
                self.sources.append(entry.strip().split()[0])
        if values.get("style"):
            self._css(values["style"])
        if tag == "style":
            self.in_style = True
        if tag == "link" and "stylesheet" in (values.get("rel") or "").lower():
            raise OssError("external stylesheet images cannot be verified; inline styles first")

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self._css(data)
