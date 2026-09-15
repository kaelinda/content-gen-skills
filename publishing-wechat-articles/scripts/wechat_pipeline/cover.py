from __future__ import annotations

import html
from pathlib import Path


COVER_WIDTH = 1200
COVER_HEIGHT = 540


def build_cover_html(
    template: str,
    *,
    title: str,
    summary: str,
    tag: str,
    brand: str,
    accent: str = "",
) -> str:
    values = {
        "TITLE": title,
        "SUMMARY": summary,
        "TAG": tag,
        "BRAND": brand,
        "ACCENT": accent,
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", html.escape(value, quote=True))
    return rendered


def render_cover_png(html_document: str, output: Path, *, browser_factory=None) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if browser_factory is not None:
        browser = browser_factory()
        try:
            page = browser.new_page(viewport={"width": COVER_WIDTH, "height": COVER_HEIGHT})
            page.set_content(html_document, wait_until="networkidle")
            page.screenshot(path=str(output), type="png")
        finally:
            browser.close()
    else:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required for PNG cover rendering") from exc
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": COVER_WIDTH, "height": COVER_HEIGHT})
                page.set_content(html_document, wait_until="networkidle")
                page.screenshot(path=str(output), type="png")
            finally:
                browser.close()
    if not output.is_file() or not output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("cover renderer did not produce a PNG")
    return output


def normalize_generated_cover(image_bytes: bytes) -> tuple[bytes, bytes]:
    """Return metadata-free source and aspect-preserving center-cropped PNGs."""
    from io import BytesIO
    from PIL import Image

    if not isinstance(image_bytes, bytes) or not 0 < len(image_bytes) <= 20 * 1024 * 1024:
        raise ValueError("generated image is empty or exceeds 20 MiB")
    with Image.open(BytesIO(image_bytes)) as image:
        if image.format not in {"PNG", "JPEG", "WEBP"} or image.size != (1536, 1024) or getattr(image, "n_frames", 1) != 1:
            raise ValueError("generated image must be a single-frame 1536x1024 PNG, JPEG, or WebP")
        image.verify()
    with Image.open(BytesIO(image_bytes)) as image:
        image.load()
        source = image.convert("RGB")
        source.info.clear()
    resized = source.resize((COVER_WIDTH, 800), Image.Resampling.LANCZOS)
    cover = resized.crop((0, 130, COVER_WIDTH, 670))
    buffers = []
    for image in (source, cover):
        stream = BytesIO()
        image.save(stream, format="PNG")
        buffers.append(stream.getvalue())
    return buffers[0], buffers[1]
