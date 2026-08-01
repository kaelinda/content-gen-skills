#!/usr/bin/env python3
"""WeChat 20:9 cover renderer — HTML + Playwright + optional OSS upload + Feishu post.

Usage:
    # Basic render
    python3 render_cover.py --html /tmp/cover.html --output /tmp/cover.png

    # Render from template with auto-fill placeholders
    python3 render_cover.py --template code-card-purple --output /tmp/cover.png \
        --tag "AI · Agent" --title "给 AI 装一个专家大脑" --subtitle "3.1k Stars 的实战指南" \
        --code "const skill = await loadSkill('swiftui')"

    # Render + upload + send to Feishu
    python3 render_cover.py --html /tmp/cover.html --output /tmp/cover.png \
        --upload --slug foo-20260623 \
        --feishu-chat-id oc_xxx --title "..." --summary "..."
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

# ---------- OSS config ----------
OSS_AK = os.environ.get("OSS_AK", "__MIGRATED_TO_RUNTIME_LOCAL__")
OSS_SK = os.environ.get("OSS_SK", "__MIGRATED_TO_RUNTIME_LOCAL__")
OSS_BUCKET = "kaelblog"
OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"
OSS_BASE_URL = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}"

# ---------- Template directory ----------
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

TEMPLATE_MAP = {
    "code-card-blue": "code-card-blue.html",
    "code-card-purple": "code-card-purple.html",
    "code-card-orange": "code-card-orange.html",
    "code-card-green": "code-card-green.html",
    "code-card-cyan": "code-card-cyan.html",
    "text-only-blue": "text-only-blue.html",
}


def render(html_path: str, output_path: str, width: int = 1200, height: int = 540, scale: int = 2) -> str:
    """Render an HTML file to a PNG via Playwright. Returns absolute output path."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright not installed. pip install playwright && playwright install chromium")

    abs_html = os.path.abspath(html_path)
    if not os.path.isfile(abs_html):
        sys.exit(f"HTML not found: {abs_html}")

    abs_output = os.path.abspath(output_path)
    Path(abs_output).parent.mkdir(parents=True, exist_ok=True)

    file_url = f"file://{abs_html}"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
        )
        page.goto(file_url, wait_until="networkidle")
        # Extra wait for Google Fonts CDN to settle
        page.wait_for_timeout(2000)
        page.screenshot(path=abs_output, type="png")
        browser.close()

    size_kb = os.path.getsize(abs_output) / 1024
    print(f"✓ Rendered: {abs_output} ({size_kb:.1f} KB, {width*scale}x{height*scale})")
    return abs_output


def upload_to_oss(png_path: str, slug: str) -> str:
    """Upload PNG to kaelblog bucket via HTTP PUT + V1 signature. Returns public URL."""
    with open(png_path, "rb") as f:
        body = f.read()

    content_type = "image/png"
    date_str = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    object_key = f"wechat/{slug}.png"
    string_to_sign = f"PUT\n\n{content_type}\n{date_str}\n/{OSS_BUCKET}/{object_key}"
    signature = base64.b64encode(
        hmac.new(OSS_SK.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()

    url = f"{OSS_BASE_URL}/{object_key}"
    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Authorization", f"OSS {OSS_AK}:{signature}")
    req.add_header("Content-Type", content_type)
    req.add_header("Date", date_str)

    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    resp = urllib.request.urlopen(req, timeout=60, context=ctx)
    print(f"✓ Uploaded: {url}")
    return url


def send_feishu_post(chat_id: str, title: str, summary: str, cover_url: str) -> bool:
    """Send a post message to Feishu with title + summary + cover URL.
    
    Pitfalls:
    - Don't use --as user flag (doesn't exist for im +messages-send)
    - Use stdin pipe for JSON (avoid shell arg truncation)
    - Add LARK_CLI_NO_PROXY=1 to bypass proxy TLS issues
    """
    post_content = {
        "zh_cn": {
            "title": "公众号文章发布请求",
            "content": [
                [{"tag": "text", "text": f"标题：{title}\n\n"}],
                [{"tag": "text", "text": f"摘要：{summary}\n\n"}],
                [{"tag": "text", "text": f"📎 封面图：{cover_url}\n\n"}],
                [{"tag": "text", "text": "完整文案见下方消息。"}],
            ],
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(post_content, f, ensure_ascii=False)
        tmp_path = f.name

    try:
        env = {**os.environ, "LARK_CLI_NO_PROXY": "1"}
        result = subprocess.run(
            f"cat {tmp_path} | lark-cli im +messages-send --chat-id {chat_id} --msg-type post --content -",
            shell=True, capture_output=True, text=True, timeout=30, env=env,
        )
        ok = '"ok": true' in result.stdout or '"code": 0' in result.stdout
        if ok:
            print(f"✓ Feishu post sent to {chat_id}")
            return True
        else:
            print(f"❌ Feishu post failed: {result.stdout[:200]}")
            return False
    except Exception as exc:
        print(f"❌ Feishu post error: {exc}")
        return False
    finally:
        os.unlink(tmp_path)


def render_template(template_name: str, tag: str = "", title: str = "",
                    subtitle: str = "", code: str = "", output_html: str = "") -> str:
    """Render a cover template by replacing div content.
    
    Finds <div class="tag">, <div class="title">, <div class="subtitle">
    and replaces their inner text. For code-card templates, also replaces
    the code block content.
    
    Args:
        template_name: Template key (e.g., "code-card-purple") or full path
        tag: Category tag (e.g., "AI · Agent")
        title: Main title (use \n for line breaks)
        subtitle: Subtitle text
        code: Code snippet for code-card templates
        output_html: Output HTML path
    
    Returns:
        Path to generated HTML file
    """
    # Resolve template path
    if os.path.isfile(template_name):
        template_path = template_name
    elif template_name in TEMPLATE_MAP:
        template_path = os.path.join(TEMPLATE_DIR, TEMPLATE_MAP[template_name])
    else:
        template_path = template_name
    
    if not os.path.isfile(template_path):
        sys.exit(f"Template not found: {template_path}")
    
    with open(template_path, "r") as f:
        html = f.read()
    
    # Replace tag div content
    if tag:
        html = re.sub(
            r'(<div class="tag">)[^<]*(</div>)',
            rf'\g<1>{tag}\2',
            html,
        )
    
    # Replace title div content (may contain <br> and <span>)
    if title:
        # Convert \n to <br>
        title_html = title.replace("\\n", "<br>").replace("\n", "<br>")
        html = re.sub(
            r'(<div class="title">\s*)(.*?)(\s*</div>)',
            rf'\g<1>{title_html}\3',
            html,
            flags=re.DOTALL,
        )
    
    # Replace subtitle div content
    if subtitle:
        subtitle_html = subtitle.replace("\\n", "<br>").replace("\n", "<br>")
        html = re.sub(
            r'(<div class="subtitle">\s*)(.*?)(\s*</div>)',
            rf'\g<1>{subtitle_html}\3',
            html,
            flags=re.DOTALL,
        )
    
    # Replace code block content (for code-card templates)
    if code:
        code_html = code.replace("\\n", "\n").replace("\n", "<br>")
        # Find the code-content div and replace
        html = re.sub(
            r'(<div class="code-content"[^>]*>)(.*?)(</div>)',
            rf'\g<1>{code_html}\3',
            html,
            flags=re.DOTALL,
        )
    
    # Output path
    if not output_html:
        output_html = f"/tmp/cover_{template_name.replace('/', '_')}.html"
    
    with open(output_html, "w") as f:
        f.write(html)
    
    print(f"✓ Template rendered: {output_html}")
    return output_html


def main():
    parser = argparse.ArgumentParser(description="Render WeChat cover from HTML and optionally upload + send.")
    parser.add_argument("--html", help="Input HTML file path")
    parser.add_argument("--template", help=f"Template name: {', '.join(TEMPLATE_MAP.keys())}")
    parser.add_argument("--tag", default="", help="Category tag for template (e.g., 'AI · Agent')")
    parser.add_argument("--title", default="", help="Main title for template")
    parser.add_argument("--subtitle", default="", help="Subtitle for template")
    parser.add_argument("--code", default="", help="Code snippet for code-card templates")
    parser.add_argument("--output", required=True, help="Output PNG file path")
    parser.add_argument("--width", type=int, default=1200, help="Viewport width (default 1200)")
    parser.add_argument("--height", type=int, default=540, help="Viewport height (default 540)")
    parser.add_argument("--scale", type=int, default=2, help="device_scale_factor (default 2 = retina)")
    parser.add_argument("--upload", action="store_true", help="Upload to OSS kaelblog bucket")
    parser.add_argument("--slug", help="OSS object key slug (e.g. swiftui-skill-20260623)")
    parser.add_argument("--feishu-chat-id", help="If set, send post message to this Feishu chat")
    parser.add_argument("--feishu-title", help="Title for Feishu post (use with --feishu-chat-id)")
    parser.add_argument("--feishu-summary", help="Summary for Feishu post (use with --feishu-chat-id)")
    args = parser.parse_args()

    # Resolve HTML source: --template or --html
    if args.template:
        html_path = render_template(
            args.template, tag=args.tag, title=args.title,
            subtitle=args.subtitle, code=args.code,
        )
    elif args.html:
        html_path = args.html
    else:
        sys.exit("Must specify either --html or --template")

    if not os.path.isfile(html_path):
        sys.exit(f"HTML file not found: {html_path}")

    # 1. Render
    render(html_path, args.output, args.width, args.height, args.scale)

    # 2. Upload (if requested)
    cover_url = None
    if args.upload:
        if not args.slug:
            stem = Path(args.output).stem
            slug = f"{stem}-{datetime.now().strftime('%Y%m%d')}"
        else:
            slug = args.slug
        cover_url = upload_to_oss(args.output, slug)

    # 3. Send Feishu post (if requested)
    if args.feishu_chat_id:
        title = args.feishu_title or args.title or "未命名"
        summary = args.feishu_summary or args.subtitle or ""
        if not cover_url:
            sys.exit("--upload --slug required when using --feishu-chat-id")
        send_feishu_post(args.feishu_chat_id, title, summary, cover_url)


if __name__ == "__main__":
    main()
