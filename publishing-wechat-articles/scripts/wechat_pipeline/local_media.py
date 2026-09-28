"""Resolve run-local Markdown images to immutable OSS URLs before rendering."""
from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
import re
from urllib.parse import quote, urlsplit

from PIL import Image

from .security import normalize_slug, safe_output_path


IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MIME = {"PNG": (".png", "image/png"), "JPEG": (".jpg", "image/jpeg"), "WEBP": (".webp", "image/webp")}


def resolve_local_images(markdown: str, run_dir: Path, *, bucket: str, endpoint: str,
                         prefix: str, account: str, title: str) -> tuple[str, list[dict[str, str]]]:
    """Keep the source Markdown local; render only verified public image URLs."""
    media: list[dict[str, str]] = []
    output: list[str] = []
    fenced = False
    for line in markdown.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if fenced:
            output.append(line)
            continue

        def replace(match: re.Match[str]) -> str:
            url = match.group(2).strip()
            if urlsplit(url).scheme in {"http", "https"}:
                return match.group(0)
            if urlsplit(url).scheme or url.startswith(("/", "\\")) or "?" in url or "#" in url:
                raise ValueError(f"unsupported local image reference: {url}")
            path = safe_output_path(run_dir, url)
            if not path.is_file():
                raise ValueError(f"local image is missing: {url}")
            data = path.read_bytes()
            if not data or len(data) > 10 * 1024 * 1024:
                raise ValueError(f"local image size is invalid: {url}")
            try:
                with Image.open(BytesIO(data)) as image:
                    kind = image.format
                    image.verify()
            except Exception as exc:
                raise ValueError(f"local image is invalid: {url}") from exc
            if kind not in MIME:
                raise ValueError(f"unsupported local image type: {url}")
            extension, content_type = MIME[kind]
            digest = hashlib.sha256(data).hexdigest()
            key = f"{prefix.strip('/')}/{account}/{normalize_slug(title)}-{digest[:16]}-media{extension}"
            public_url = f"https://{bucket}.{endpoint.removeprefix('https://').removeprefix('http://').rstrip('/')}/{quote(key, safe='/')}"
            entry = {"path": path.relative_to(run_dir.resolve()).as_posix(), "sha256": digest,
                     "key": key, "url": public_url, "content_type": content_type}
            if entry not in media:
                media.append(entry)
            return f"![{match.group(1)}]({public_url})"

        output.append(IMAGE.sub(replace, line))
    return "".join(output), media
