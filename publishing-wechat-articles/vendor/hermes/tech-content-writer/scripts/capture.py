#!/usr/bin/env python3
"""
Unified content capture script — one entry point for all source types.

Handles:
  1. X/Twitter tweets (fxtwitter API, no auth needed)
  2. X/Twitter Articles (draft.js blocks → markdown)
  3. Blog/article URLs (HTTP fetch → markdown)
  4. WWDC session pages (Apple Developer → markdown)

Auto-downloads images from captured content and uploads to OSS.

Usage:
  python3 capture.py <URL> [--output-dir /tmp/capture_<slug>]

  # Tweet/Article
  python3 capture.py "https://x.com/handle/status/123456"
  python3 capture.py "https://twitter.com/handle/status/123456"

  # Blog post
  python3 capture.py "https://swift.org/blog/some-post/"

  # WWDC session
  python3 capture.py "https://developer.apple.com/videos/play/wwdc2026/123/"

Output structure:
  /tmp/capture_<slug>/
    raw.json          # Full API response (tweets) or page source
    content.md        # Extracted markdown content
    images.yaml       # Image mapping: [{index, url, local_path, oss_url, context}]
    frontmatter.yaml  # Standardized metadata
    images/           # Downloaded images

Requires: Python 3.11+, urllib (stdlib), no external deps.
OSS upload uses HTTP PUT + V1 signature (no oss2 SDK needed).

Tested: 2026-07-11 (tweet, Article, blog URL types)
"""

import argparse
import gzip
import hashlib
import hmac
import json
import os
import re
import ssl
import sys
import time
import base64
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── OSS Config ──────────────────────────────────────────────────────────────
OSS_AK = "__MIGRATED_TO_RUNTIME_LOCAL__"
OSS_SK = "__MIGRATED_TO_RUNTIME_LOCAL__"
OSS_BUCKET = "kaelblog"
OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"
OSS_BASE_URL = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}"

# ── SSL Context (company proxy intercepts HTTPS) ────────────────────────────
SSL_CTX = ssl._create_unverified_context()


def fetch_url(url: str, timeout: int = 30) -> bytes:
    """Fetch URL content with proxy-aware SSL and gzip decompression."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/html, */*",
        "Accept-Encoding": "gzip, deflate",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
        data = resp.read()
        # Auto-decompress gzip
        if resp.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data


def fetch_url_text(url: str, timeout: int = 30) -> str:
    """Fetch URL as text."""
    return fetch_url(url, timeout).decode("utf-8", errors="replace")


# ── URL Type Detection ──────────────────────────────────────────────────────

def detect_url_type(url: str) -> str:
    """Detect source type from URL pattern."""
    url_lower = url.lower()
    # X/Twitter patterns
    if re.search(r'(twitter\.com|x\.com)/\w+/status/\d+', url_lower):
        return "tweet"
    if re.search(r'(twitter\.com|x\.com)/\w+/article/', url_lower):
        return "tweet_article"
    # WWDC session
    if 'developer.apple.com/videos/play/wwdc' in url_lower:
        return "wwdc"
    # Generic blog/article
    return "blog"


def extract_tweet_id(url: str) -> tuple[str, str]:
    """Extract (handle, tweet_id) from X/Twitter URL."""
    m = re.search(r'(?:twitter\.com|x\.com)/(\w+)/status/(\d+)', url)
    if not m:
        raise ValueError(f"Cannot extract tweet ID from: {url}")
    return m.group(1), m.group(2)


# ── fxtwitter Capture ──────────────────────────────────────────────────────

def capture_tweet(url: str) -> dict:
    """Capture tweet/Article via fxtwitter API."""
    handle, tweet_id = extract_tweet_id(url)
    api_url = f"https://api.fxtwitter.com/{handle}/status/{tweet_id}"
    print(f"[fxtwitter] Fetching: {api_url}")
    
    try:
        raw_text = fetch_url_text(api_url, timeout=15)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"fxtwitter API returned HTTP {e.code} for {url}") from e
    
    data = json.loads(raw_text)
    
    if "tweet" not in data:
        raise RuntimeError(f"fxtwitter returned no tweet data: {raw_text[:500]}")
    
    tweet = data["tweet"]
    
    # Build result
    result = {
        "source_url": url,
        "api_url": api_url,
        "type": "tweet",
        "author": tweet.get("author", {}),
        "created_at": tweet.get("created_at", ""),
        "text": tweet.get("text", ""),
        "likes": tweet.get("likes", 0),
        "retweets": tweet.get("retweets", 0),
        "images": [],
        "media": [],
    }
    
    # Check if it's a Twitter Article (long-form)
    article = tweet.get("article")
    if article and article.get("content", {}).get("blocks"):
        result["type"] = "tweet_article"
        result["article"] = {
            "title": article.get("title", ""),
            "subtitle": article.get("subtitle", ""),
            "blocks": article["content"]["blocks"],
        }
        
        # Extract images from media_entities (NOT entityMap — that's a list without URLs)
        media_entities = article.get("media_entities", [])
        for i, me in enumerate(media_entities):
            info = me.get("media_info", {})
            img_url = info.get("original_img_url", "")
            if img_url:
                result["images"].append({
                    "index": i,
                    "url": img_url,
                    "context": f"Article image {i+1}",
                })
        
        # Cover image
        cover_media = article.get("cover_media", {})
        cover_info = cover_media.get("media_info", {})
        cover_url = cover_info.get("original_img_url", "")
        if cover_url:
            result["cover_image"] = cover_url
        
        # Convert blocks to markdown
        result["content_md"] = _blocks_to_md(article["content"]["blocks"])
        print(f"[fxtwitter] Article: {len(article['content']['blocks'])} blocks, {len(result['images'])} images")
    
    else:
        # Regular tweet
        result["content_md"] = tweet.get("text", "")
        
        # Extract images from regular tweet media
        media_list = tweet.get("media", [])
        if not media_list:
            # Try external URLs pattern
            media_list = tweet.get("mediaDetails", [])
        for i, m in enumerate(media_list):
            if isinstance(m, dict):
                img_url = m.get("url", "") or m.get("media_url_https", "")
                if img_url:
                    # Try to get original size
                    if "?name=" not in img_url:
                        img_url += "?name=orig"
                    result["images"].append({
                        "index": i,
                        "url": img_url,
                        "context": f"Tweet image {i+1}",
                    })
        
        # Check for thread
        thread = tweet.get("thread", [])
        if thread and len(thread) > 1:
            result["type"] = "tweet_thread"
            result["thread"] = []
            for t in thread:
                result["thread"].append({
                    "text": t.get("text", ""),
                    "author": t.get("author", {}).get("screen_name", ""),
                })
            result["content_md"] = "\n\n---\n\n".join(
                t.get("text", "") for t in thread
            )
            print(f"[fxtwitter] Thread: {len(thread)} tweets")
        else:
            print(f"[fxtwitter] Single tweet: {len(result['text'])} chars")
    
    return result


def _blocks_to_md(blocks: list) -> str:
    """Convert Twitter Article draft.js blocks to markdown."""
    out = []
    for b in blocks:
        block_type = b.get("type", "")
        
        # Extract text from various field locations
        text = ""
        if isinstance(b.get("text"), str):
            text = b["text"]
        elif isinstance(b.get("content"), list):
            for c in b["content"]:
                if isinstance(c, dict):
                    text += c.get("text", "")
        text = text.strip()
        
        if block_type == "header-one":
            out.append(f"# {text}")
        elif block_type == "header-two":
            out.append(f"## {text}")
        elif block_type == "header-three":
            out.append(f"### {text}")
        elif block_type == "unordered-list-item":
            out.append(f"- {text}")
        elif block_type == "ordered-list-item":
            out.append(f"1. {text}")
        elif block_type == "blockquote":
            out.append(f"> {text}")
        elif block_type == "code-block":
            lang = b.get("language", "")
            out.append(f"```{lang}\n{text}\n```")
        elif block_type == "atomic":
            # Media block — skip (images handled separately via media_entities)
            continue
        elif block_type == "unstyled" and text:
            out.append(text)
        elif text:
            out.append(text)
    
    return "\n\n".join(out)


# ── Blog/Article Capture ───────────────────────────────────────────────────

def capture_blog(url: str) -> dict:
    """Capture blog/article via HTTP fetch."""
    print(f"[blog] Fetching: {url}")
    
    html = fetch_url_text(url, timeout=20)
    
    # Basic HTML → markdown extraction
    content_md = _html_to_md(html)
    
    # Extract title
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
    title = title_match.group(1).strip() if title_match else ""
    
    # Extract images
    images = []
    img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)
    for i, m in enumerate(img_pattern.finditer(html)):
        img_url = m.group(1)
        # Make absolute URL
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        elif img_url.startswith("/"):
            parsed = urllib.parse.urlparse(url)
            img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
        
        # Skip tracking pixels, icons, small images
        if any(skip in img_url.lower() for skip in [
            "pixel", "track", "1x1", "spacer", "blank",
            "favicon", "icon", "logo", "avatar", "badge",
            ".svg", "analytics",
        ]):
            continue
        
        # Get alt text for context
        alt_match = re.search(
            r'<img[^>]+alt=["\']([^"\']*)["\']', 
            html[max(0, m.start()-200):m.end()+200], re.I
        )
        alt = alt_match.group(1) if alt_match else f"Article image {i+1}"
        
        images.append({
            "index": len(images),
            "url": img_url,
            "context": alt,
        })
    
    result = {
        "source_url": url,
        "type": "blog",
        "title": title,
        "content_md": content_md,
        "images": images,
    }
    
    print(f"[blog] Title: {title[:60]}")
    print(f"[blog] Content: {len(content_md)} chars, {len(images)} images")
    
    return result


def _html_to_md(html: str) -> str:
    """Simple HTML to markdown conversion with content-area detection."""
    # Remove script/style/nav/header/footer blocks
    html = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.I)
    html = re.sub(r'<style[\s\S]*?</style>', '', html, flags=re.I)
    html = re.sub(r'<nav[\s\S]*?</nav>', '', html, flags=re.I)
    html = re.sub(r'<header[\s\S]*?</header>', '', html, flags=re.I)
    html = re.sub(r'<footer[\s\S]*?</footer>', '', html, flags=re.I)
    
    # Try to find main content area (in order of specificity)
    content = ""
    for selector in [
        r'<article[\s\S]*?</article>',
        r'<main[\s\S]*?</main>',
        r'<div[^>]*class="[^"]*post[_-]?content[^"]*"[\s\S]*?</div>',
        r'<div[^>]*class="[^"]*article[_-]?body[^"]*"[\s\S]*?</div>',
        r'<div[^>]*class="[^"]*entry[_-]?content[^"]*"[\s\S]*?</div>',
        r'<div[^>]*class="[^"]*content[^"]*"[\s\S]*?</div>',
    ]:
        m = re.search(selector, html, re.I)
        if m:
            content = m.group(0)
            break
    
    if not content:
        content = html
    
    # Convert common HTML elements to markdown
    # Headers
    for level in range(1, 7):
        tag = f"h{level}"
        prefix = "#" * level
        content = re.sub(
            rf'<{tag}[^>]*>(.*?)</{tag}>',
            lambda m, p=prefix: f"\n\n{p} {m.group(1).strip()}\n\n",
            content, flags=re.I | re.S
        )
    
    # Code blocks
    content = re.sub(
        r'<pre[^>]*><code[^>]*>(.*?)</code></pre>',
        lambda m: f"\n```\n{m.group(1)}\n```\n",
        content, flags=re.I | re.S
    )
    
    # Paragraphs
    content = re.sub(r'<p[^>]*>(.*?)</p>', lambda m: f"\n{m.group(1).strip()}\n", content, flags=re.I | re.S)
    
    # Lists
    content = re.sub(r'<li[^>]*>(.*?)</li>', lambda m: f"- {m.group(1).strip()}\n", content, flags=re.I | re.S)
    
    # Blockquotes
    content = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', lambda m: f"\n> {m.group(1).strip()}\n", content, flags=re.I | re.S)
    
    # Links
    content = re.sub(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'[\2](\1)', content, flags=re.I | re.S)
    
    # Bold / italic
    content = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'**\2**', content, flags=re.I | re.S)
    content = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'*\2*', content, flags=re.I | re.S)
    
    # Strip remaining HTML tags
    content = re.sub(r'<[^>]+>', '', content)
    
    # Decode HTML entities
    content = content.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    content = content.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    
    # Clean up whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()
    
    return content


# ── Image Download + OSS Upload ────────────────────────────────────────────

def download_image(url: str, local_path: str) -> bool:
    """Download image from URL to local path."""
    try:
        # URL-encode non-ASCII characters in the URL
        parsed = urllib.parse.urlsplit(url)
        # Encode the path component (handles unicode chars like \u202f)
        path_encoded = urllib.parse.quote(parsed.path, safe="/:@!$&'()*+,;=-._~")
        # Encode query component separately
        query_encoded = urllib.parse.quote(parsed.query, safe="=&+%")
        encoded_url = urllib.parse.urlunsplit((
            parsed.scheme, parsed.netloc, path_encoded, query_encoded, parsed.fragment
        ))
        data = fetch_url(encoded_url, timeout=30)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"  [WARN] Download failed: {url[:80]} — {e}")
        return False


def oss_upload_v1(local_path: str, oss_key: str, content_type: str = "image/png") -> str:
    """Upload to OSS via HTTP PUT + V1 signature. Returns public URL."""
    with open(local_path, "rb") as f:
        body = f.read()
    
    date_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    string_to_sign = f"PUT\n\n{content_type}\n{date_str}\n/{OSS_BUCKET}/{oss_key}"
    signature = base64.b64encode(
        hmac.new(OSS_SK.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    
    url = f"{OSS_BASE_URL}/{oss_key}"
    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Authorization", f"AWS {OSS_AK}:{signature}")
    req.add_header("Content-Type", content_type)
    req.add_header("Date", date_str)
    
    resp = urllib.request.urlopen(req, timeout=60, context=SSL_CTX)
    return url


def oss_upload_oss2(local_path: str, oss_key: str, content_type: str = "image/png") -> str:
    """Upload to OSS via oss2 SDK (with sys.path isolation). Returns public URL."""
    import sys
    original_path = sys.path[:]
    sys.path = [p for p in sys.path if "hermes-agent/venv" not in p]
    try:
        import oss2
        auth = oss2.Auth(OSS_AK, OSS_SK)
        bucket = oss2.Bucket(auth, f"https://{OSS_ENDPOINT}", OSS_BUCKET)
        with open(local_path, "rb") as f:
            bucket.put_object(oss_key, f, headers={"Content-Type": content_type})
        return f"{OSS_BASE_URL}/{oss_key}"
    finally:
        sys.path = original_path


def upload_image(local_path: str, oss_key: str, content_type: str = "image/png") -> str:
    """Upload image to OSS. HTTP PUT first (pure stdlib, no cffi conflict), fallback to oss2."""
    try:
        return oss_upload_v1(local_path, oss_key, content_type)
    except Exception as e:
        print(f"  [INFO] HTTP PUT failed ({e}), trying oss2 SDK...")
        return oss_upload_oss2(local_path, oss_key, content_type)


def detect_content_type(url: str, local_path: str = "") -> str:
    """Guess content type from URL or file extension."""
    url_lower = url.lower().split("?")[0]
    if url_lower.endswith(".png"):
        return "image/png"
    elif url_lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    elif url_lower.endswith(".gif"):
        return "image/gif"
    elif url_lower.endswith(".webp"):
        return "image/webp"
    elif url_lower.endswith(".svg"):
        return "image/svg+xml"
    
    # Check local file
    if local_path and os.path.exists(local_path):
        with open(local_path, "rb") as f:
            header = f.read(16)
        if header[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        elif header[:2] == b"\xff\xd8":
            return "image/jpeg"
        elif header[:4] == b"GIF8":
            return "image/gif"
        elif header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "image/webp"
    
    return "image/png"  # default


def get_extension(content_type: str) -> str:
    """Get file extension from content type."""
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }.get(content_type, ".png")


def make_oss_key(topic: str, filename: str) -> str:
    """Generate OSS key for image."""
    return f"aicoder/{topic}/{filename}"


# ── Main Capture Pipeline ──────────────────────────────────────────────────

def capture(url: str, output_dir: str = None, topic: str = None, skip_upload: bool = False) -> dict:
    """
    Main capture pipeline.
    
    Returns:
        {
            "output_dir": str,
            "source_type": str,
            "content_md": str,
            "images": [{"index", "url", "local_path", "oss_url", "context"}],
            "metadata": dict,
        }
    """
    # Detect type and capture
    url_type = detect_url_type(url)
    print(f"\n{'='*60}")
    print(f"[capture] URL type: {url_type}")
    print(f"[capture] Source: {url}")
    print(f"{'='*60}\n")
    
    if url_type in ("tweet", "tweet_article"):
        result = capture_tweet(url)
    elif url_type == "blog":
        result = capture_blog(url)
    elif url_type == "wwdc":
        # WWDC uses browser-based capture — return instruction
        print("[wwdc] WWDC sessions require browser-based capture.")
        print("[wwdc] Use browser_navigate + browser_console IIFE extraction.")
        return {
            "output_dir": None,
            "source_type": "wwdc",
            "content_md": None,
            "images": [],
            "metadata": {"url": url, "note": "Use browser capture for WWDC"},
            "requires_browser": True,
        }
    else:
        raise ValueError(f"Unknown URL type: {url_type}")
    
    # Generate output directory
    if not output_dir:
        slug = _make_slug(url, result)
        output_dir = f"/tmp/capture_{slug}"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
    
    # Save raw JSON
    raw_path = os.path.join(output_dir, "raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"[save] Raw JSON: {raw_path}")
    
    # Save content markdown
    md_path = os.path.join(output_dir, "content.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(result.get("content_md", ""))
    print(f"[save] Content MD: {md_path} ({len(result.get('content_md', ''))} chars)")
    
    # Download and upload images
    images_out = []
    if result.get("images"):
        print(f"\n[images] Processing {len(result['images'])} images...")
        for img in result["images"]:
            img_url = img["url"]
            idx = img["index"]
            ct = detect_content_type(img_url)
            ext = get_extension(ct)
            filename = f"img_{idx:02d}{ext}"
            local_path = os.path.join(output_dir, "images", filename)
            
            # Download
            ok = download_image(img_url, local_path)
            if not ok:
                images_out.append({
                    "index": idx,
                    "url": img_url,
                    "local_path": None,
                    "oss_url": None,
                    "context": img.get("context", ""),
                    "status": "download_failed",
                })
                continue
            
            file_size = os.path.getsize(local_path)
            print(f"  [{idx}] Downloaded: {filename} ({file_size:,} bytes)")
            
            # Upload to OSS
            oss_url = None
            upload_status = "ok"
            if not skip_upload:
                oss_key = make_oss_key(topic or "capture", filename)
                try:
                    oss_url = upload_image(local_path, oss_key, ct)
                    print(f"  [{idx}] Uploaded: {oss_url}")
                except Exception as e:
                    print(f"  [{idx}] Upload failed: {e}")
                    upload_status = "upload_failed"
            
            images_out.append({
                "index": idx,
                "url": img_url,
                "local_path": local_path,
                "oss_url": oss_url,
                "context": img.get("context", ""),
                "status": upload_status,
            })
        
        # Save images.yaml
        images_yaml_path = os.path.join(output_dir, "images.yaml")
        _save_images_yaml(images_out, images_yaml_path)
    
    # Save frontmatter
    metadata = {
        "source_url": url,
        "source_type": result.get("type", url_type),
        "captured_at": datetime.now().isoformat(),
        "author": result.get("author", {}),
        "title": result.get("title", ""),
        "image_count": len(images_out),
        "content_chars": len(result.get("content_md", "")),
    }
    # Add article-specific metadata
    if result.get("type") == "tweet_article":
        article = result.get("article", {})
        metadata["article_title"] = article.get("title", "")
        metadata["article_subtitle"] = article.get("subtitle", "")
    
    fm_path = os.path.join(output_dir, "frontmatter.yaml")
    _save_yaml(metadata, fm_path)
    print(f"[save] Frontmatter: {fm_path}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"[capture] ✅ Done!")
    print(f"  Output: {output_dir}")
    print(f"  Type: {result.get('type', url_type)}")
    print(f"  Content: {len(result.get('content_md', ''))} chars")
    print(f"  Images: {len([i for i in images_out if i['status'] == 'ok'])}/{len(images_out)} uploaded")
    if images_out:
        print(f"  Image mapping:")
        for img in images_out:
            status = "✅" if img["status"] == "ok" else "❌"
            oss = img.get("oss_url", "N/A")
            print(f"    {status} [{img['index']}] {img['context'][:40]} → {oss}")
    print(f"{'='*60}\n")
    
    return {
        "output_dir": output_dir,
        "source_type": result.get("type", url_type),
        "content_md": result.get("content_md", ""),
        "images": images_out,
        "metadata": metadata,
    }


def _make_slug(url: str, result: dict) -> str:
    """Generate a URL-safe slug for the output directory."""
    # Try to use tweet ID or article title
    if result.get("type") in ("tweet", "tweet_article", "tweet_thread"):
        handle, tid = extract_tweet_id(url)
        return f"{handle}_{tid}"
    
    # For blog URLs, use domain + path
    parsed = urllib.parse.urlparse(url)
    path_part = parsed.path.strip("/").split("/")[-1] if parsed.path else "article"
    slug = f"{parsed.netloc.split('.')[0]}_{path_part}"
    slug = re.sub(r'[^a-zA-Z0-9_-]', '_', slug)[:60]
    return slug


def _save_images_yaml(images: list, path: str):
    """Save images mapping as YAML-like format (no PyYAML dependency)."""
    lines = ["# Auto-generated image mapping", "# Format: index | url | local_path | oss_url | context", ""]
    for img in images:
        lines.append(f"- index: {img['index']}")
        lines.append(f"  url: \"{img['url']}\"")
        lines.append(f"  local_path: \"{img.get('local_path', '')}\"")
        lines.append(f"  oss_url: \"{img.get('oss_url', '')}\"")
        lines.append(f"  context: \"{img.get('context', '')}\"")
        lines.append(f"  status: {img.get('status', 'unknown')}")
        lines.append("")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[save] Images YAML: {path}")


def _save_yaml(data: dict, path: str):
    """Save dict as simple YAML-like format (no PyYAML dependency)."""
    lines = ["# Auto-generated metadata", ""]
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"{k}:")
            for sk, sv in v.items():
                lines.append(f"  {sk}: \"{sv}\"")
        elif isinstance(v, str):
            lines.append(f'{k}: "{v}"')
        else:
            lines.append(f"{k}: {v}")
    lines.append("")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Unified content capture — tweets, articles, blogs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 capture.py "https://x.com/user/status/123456"
  python3 capture.py "https://x.com/user/status/123456" --topic multi-agent
  python3 capture.py "https://swift.org/blog/some-post/" --no-upload
  python3 capture.py "https://x.com/user/article/123" --output-dir /tmp/my_capture
        """
    )
    parser.add_argument("url", help="URL to capture")
    parser.add_argument("--output-dir", "-o", help="Output directory (auto-generated if not set)")
    parser.add_argument("--topic", "-t", help="Topic for OSS path (e.g. 'multi-agent', 'wwdc26')")
    parser.add_argument("--no-upload", action="store_true", help="Skip OSS upload (download only)")
    
    args = parser.parse_args()
    
    result = capture(
        url=args.url,
        output_dir=args.output_dir,
        topic=args.topic,
        skip_upload=args.no_upload,
    )
    
    # Print final status
    if result.get("requires_browser"):
        print("\n⚠️  This URL type requires browser-based capture.")
        print("   Use browser_navigate + browser_console in Hermes Agent.")
        sys.exit(2)
    
    if result["images"]:
        uploaded = len([i for i in result["images"] if i.get("oss_url")])
        failed = len([i for i in result["images"] if i["status"] != "ok"])
        if failed:
            print(f"\n⚠️  {failed} image(s) failed to download/upload.")
            sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
