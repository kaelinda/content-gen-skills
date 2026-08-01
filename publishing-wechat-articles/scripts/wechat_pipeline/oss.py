from __future__ import annotations

import base64
from email.utils import formatdate
import hashlib
import hmac
from pathlib import PurePosixPath
import urllib.parse
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

    @staticmethod
    def _default_transport(request: urllib.request.Request, timeout: int):
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), {key.lower(): value for key, value in response.headers.items()}, response.read()
