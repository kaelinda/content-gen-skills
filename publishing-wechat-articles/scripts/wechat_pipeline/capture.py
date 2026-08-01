from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import ssl
import urllib.parse
import urllib.request

from .security import SecurityError, sanitize_resource_url, validate_public_url


MAX_CAPTURE_BYTES = 8 * 1024 * 1024
USER_AGENT = "content-gen-skills/1.0"


@dataclass(frozen=True)
class FetchResponse:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes


@dataclass(frozen=True)
class CapturedSource:
    source_url: str
    final_url: str
    method: str
    title: str
    content_md: str
    images: tuple[dict[str, str], ...]
    captured_at: str
    raw_text: str

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["images"] = list(self.images)
        return value


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _https_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    if context.get_ca_certs():
        return context
    try:
        import certifi
    except ImportError:
        return context
    return ssl.create_default_context(cafile=certifi.where())


def fetch_public_url(url: str, max_bytes: int = MAX_CAPTURE_BYTES) -> FetchResponse:
    validate_public_url(url)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.5"},
    )
    opener = urllib.request.build_opener(_SafeRedirect(), urllib.request.HTTPSHandler(context=_https_context()))
    with opener.open(request, timeout=25) as response:
        final_url = validate_public_url(response.geturl())
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > max_bytes:
            raise SecurityError(f"response exceeds {max_bytes} bytes")
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise SecurityError(f"response exceeds {max_bytes} bytes")
        return FetchResponse(
            final_url,
            int(response.status),
            {key.lower(): value for key, value in response.headers.items()},
            body,
        )


class _ArticleParser(HTMLParser):
    BLOCKED = {"script", "style", "nav", "header", "footer", "noscript", "svg"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.parts: list[str] = []
        self.images: list[dict[str, str]] = []
        self._title = False
        self._blocked_depth = 0

    def handle_starttag(self, tag: str, attrs):
        attrs_map = dict(attrs)
        if tag in self.BLOCKED:
            self._blocked_depth += 1
            return
        if self._blocked_depth:
            return
        if tag == "title":
            self._title = True
        elif tag in {"h1", "h2", "h3", "h4"}:
            self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in {"p", "div", "article", "main", "section", "blockquote"}:
            self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "img":
            raw_url = attrs_map.get("src", "")
            absolute = urllib.parse.urljoin(self.base_url, raw_url)
            safe_url = sanitize_resource_url(absolute)
            if safe_url:
                alt = attrs_map.get("alt", "").strip() or f"Article image {len(self.images) + 1}"
                self.images.append({"url": safe_url, "context": alt})

    def handle_endtag(self, tag: str):
        if tag in self.BLOCKED:
            self._blocked_depth = max(0, self._blocked_depth - 1)
            return
        if tag == "title":
            self._title = False

    def handle_data(self, data: str):
        if self._blocked_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._title:
            self.title_parts.append(text)
        else:
            self.parts.append(text + " ")

    def result(self) -> tuple[str, str, tuple[dict[str, str], ...]]:
        lines = [line.strip() for line in "".join(self.parts).splitlines()]
        markdown = "\n".join(line for line in lines if line).strip()
        return " ".join(self.title_parts).strip(), markdown, tuple(self.images)


def capture_source(url: str, *, fetcher=fetch_public_url) -> CapturedSource:
    validated = validate_public_url(url)
    x_match = re.search(r"https?://(?:www\.)?(?:x|twitter)\.com/([^/]+)/status/(\d+)", validated, re.IGNORECASE)
    request_url = (
        f"https://api.fxtwitter.com/{x_match.group(1)}/status/{x_match.group(2)}"
        if x_match
        else validated
    )
    response = fetcher(validate_public_url(request_url), MAX_CAPTURE_BYTES)
    if response.status < 200 or response.status >= 300:
        raise RuntimeError(f"capture returned HTTP {response.status}")
    final_url = validate_public_url(response.url)
    text = response.body.decode("utf-8", errors="replace")
    if x_match:
        return _capture_fxtwitter(validated, response, text)
    parser = _ArticleParser(final_url)
    parser.feed(text)
    title, content_md, images = parser.result()
    return CapturedSource(
        source_url=validated,
        final_url=final_url,
        method="https-html",
        title=title,
        content_md=content_md,
        images=images,
        captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        raw_text=text,
    )


def _capture_fxtwitter(source_url: str, response: FetchResponse, text: str) -> CapturedSource:
    try:
        tweet = json.loads(text)["tweet"]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("fxtwitter response did not contain tweet data") from exc
    article = tweet.get("article") or {}
    content = tweet.get("text", "")
    title = article.get("title", "")
    blocks = article.get("content", {}).get("blocks", [])
    if blocks:
        content = "\n\n".join(
            str(block.get("text", "")).strip()
            for block in blocks
            if str(block.get("text", "")).strip()
        )
    images: list[dict[str, str]] = []
    media = tweet.get("media") or tweet.get("mediaDetails") or []
    for item in media:
        if not isinstance(item, dict):
            continue
        value = item.get("url") or item.get("media_url_https") or ""
        safe_url = sanitize_resource_url(value)
        if safe_url:
            images.append({"url": safe_url, "context": item.get("altText") or f"Post image {len(images) + 1}"})
    for item in article.get("media_entities", []):
        value = item.get("media_info", {}).get("original_img_url", "")
        safe_url = sanitize_resource_url(value)
        if safe_url:
            images.append({"url": safe_url, "context": f"Article image {len(images) + 1}"})
    author = tweet.get("author") or {}
    return CapturedSource(
        source_url=source_url,
        final_url=response.url,
        method="fxtwitter",
        title=title or author.get("name", ""),
        content_md=content.strip(),
        images=tuple(images),
        captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        raw_text=text,
    )


def archive_capture(capture: CapturedSource, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "raw": output_dir / "raw.html",
        "content": output_dir / "content.md",
        "metadata": output_dir / "metadata.json",
        "images": output_dir / "images.json",
    }
    paths["raw"].write_text(capture.raw_text, encoding="utf-8")
    paths["content"].write_text(capture.content_md + "\n", encoding="utf-8")
    metadata = capture.to_dict()
    metadata.pop("raw_text")
    metadata.pop("content_md")
    metadata.pop("images")
    paths["metadata"].write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["images"].write_text(json.dumps(list(capture.images), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths
