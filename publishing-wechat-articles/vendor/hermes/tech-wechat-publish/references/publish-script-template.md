# Reusable end-to-end publish script

This template consolidates the four-step pipeline that has been hand-written
four+ times across recent sessions (covers, OSS, post request, chunked body
send):

1. HTML cover rendered via Playwright (1200×540 retina PNG)
2. Upload cover to Aliyun OSS (`kaelblog` bucket, `wechat/` prefix)
3. Send a Feishu **post** request (title + summary + cover URL) to the target chat
4. Send the article body in paragraph-aware markdown chunks (≤900 chars each)

Copy this to `/tmp/publish_<slug>.py`, edit the CONFIG block, and run with
`/Users/nowcoder/miniconda3/bin/python3` (the conda env has `playwright` and
`oss2` already).

The CONFIG block is the only section you need to edit per article. Everything
else is the same across articles — including the lark-cli flag pitfall
(`--chat-id`, not `--chat`).

```python
#!/usr/bin/env python3
"""End-to-end WeChat publish: HTML cover → OSS → Feishu post + chunked body."""
import oss2, subprocess, json, re, time

# ====== CONFIG — edit per article ======
ARTICLE_PATH = "/tmp/article.md"        # final markdown to publish
COVER_HTML   = "/tmp/cover.html"       # local HTML for Playwright to render
OSS_KEY      = "wechat/my-article-20260623.png"  # path under bucket root
TITLE        = "My article title"
SUMMARY      = "One-line teaser shown above the cover."
CHAT_ID      = "oc_xxxx"               # AICoder (tech) or 育儿育己 (parenting)

OSS_AK = "__MIGRATED_TO_RUNTIME_LOCAL__"
OSS_SK = "__MIGRATED_TO_RUNTIME_LOCAL__"
OSS_BUCKET = "kaelblog"
OSS_ENDPOINT = "https://oss-cn-beijing.aliyuncs.com"
# ====== END CONFIG ======

# 1. Render HTML cover via Playwright
from playwright.sync_api import sync_playwright
import os
html_abs = os.path.abspath(COVER_HTML)
png_path = COVER_HTML.replace(".html", ".png")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1200, "height": 540}, device_scale_factor=2)
    page.goto(f"file://{html_abs}", wait_until="networkidle")
    page.wait_for_timeout(2000)  # let Google Fonts load
    page.screenshot(path=png_path, type="png")
    browser.close()
print(f"✓ Cover rendered: {os.path.getsize(png_path)} bytes")

# 2. Upload cover to OSS
auth = oss2.Auth(OSS_AK, OSS_SK)
bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)
with open(png_path, "rb") as f:
    bucket.put_object(OSS_KEY, f, headers={"Content-Type": "image/png",
                                           "Cache-Control": "max-age=86400"})
COVER_URL = f"https://{OSS_BUCKET}.oss-cn-beijing.aliyuncs.com/{OSS_KEY}"
print(f"✓ Cover uploaded: {COVER_URL}")

# 3. Send Feishu post request (title + summary + cover)
post_content = {
    "zh_cn": {
        "title": "公众号文章发布请求",
        "content": [
            [{"tag": "text", "text": "请帮忙发布公众号文章\n\n"}],
            [{"tag": "text", "text": f"标题：{TITLE}\n\n"}],
            [{"tag": "text", "text": f"摘要：{SUMMARY}\n\n"}],
            [{"tag": "text", "text": f"封面图：{COVER_URL}\n\n"}],
            [{"tag": "text", "text": "完整文案见下方消息。"}]
        ]
    }
}
result = subprocess.run(
    ["lark-cli", "im", "+messages-send", "--chat-id", CHAT_ID,
     "--as", "user", "--msg-type", "post",
     "--content", json.dumps(post_content, ensure_ascii=False)],
    capture_output=True, text=True, timeout=30
)
ok = '"ok": true' in result.stdout or '"code": 0' in result.stdout
if not ok:
    print(f"❌ Post failed: {result.stdout[:300]}")
    raise SystemExit(1)
print("✓ Post request sent")

# 4. Send article body in paragraph-aware chunks
article = open(ARTICLE_PATH).read()
# Strip --- separators (Feishu renders them as <hr>)
article = article.replace("\n---\n", "\n\n").replace("\n---", "\n\n").replace("---\n", "\n\n")

chunks, current = [], ""
for para in re.split(r"\n\n+", article):
    para = para.strip()
    if not para:
        continue
    if len(current) + len(para) + 2 > 900 and current:
        chunks.append(current.strip())
        current = para + "\n\n"
    else:
        current += para + "\n\n"
if current.strip():
    chunks.append(current.strip())

print(f"Split into {len(chunks)} chunks")
time.sleep(1)

for i, chunk in enumerate(chunks, 1):
    result = subprocess.run(
        ["lark-cli", "im", "+messages-send", "--chat-id", CHAT_ID,
         "--as", "user", "--markdown", chunk],
        capture_output=True, text=True, timeout=30
    )
    ok = '"ok": true' in result.stdout or '"code": 0' in result.stdout
    if not ok:
        print(f"❌ Chunk {i}/{len(chunks)} failed: {result.stdout[:200]}")
        raise SystemExit(1)
    print(f"  ✓ Chunk {i}/{len(chunks)} sent ({len(chunk)} chars)")
    time.sleep(0.5)

print(f"\n✅ Published: {TITLE}")
print(f"   Cover: {COVER_URL}")
print(f"   Chunks: {len(chunks)}")
```

## Why this script is worth a template

This four-step pipeline has been hand-written **four+ times across recent
sessions** (swiftui-agent-skill v1+v2 re-publish, Swift 6.4 concurrency,
AsyncImage iOS 27, UI Skills, LLDB MCP, Bazel+iOS-from-Linux). Every
rewrite re-introduced the same minor bugs:

- Quoting issue on the `'"ok": true" in result.stdout or '"code": 0' in result.stdout'` check
  (one session had a syntax error from a missing close quote — wasted ~1 min)
- Forgetting `lark-cli im +messages-send` flag differences
  (`--image` not allowed; `--chat-id` not `--chat`)
- `---` horizontal-rule leak from markdown body into Feishu posts (breaks post layout)
- Paragraph-aware chunking off-by-one at the boundary (last paragraph dropped or merged wrong)
- OSS object key typos (e.g. `wechat/...png` vs `wechat/...PNG`)
- Forgetting `device_scale_factor=2` for retina cover (Chinese text looked blurry in the rendered PNG)

The template above pins all of these once, so the per-article diff stays at
the CONFIG block (~6 lines) and the rest is reusable.

## Per-article changes (the CONFIG block only)

| Field | What to set | Common values |
|---|---|---|
| `ARTICLE_PATH` | `/tmp/article-<slug>.md` | Always absolute path under `/tmp/` |
| `COVER_HTML`   | `/tmp/cover-<slug>.html`     | Use Playwright-renderable HTML (no JS deps, Google Fonts OK) |
| `OSS_KEY`      | `wechat/<slug>-YYYYMMDD.png` | Add `-v2` / `-v3` for re-publishes (see `republish-same-project.md`) |
| `TITLE`        | 公众号标题 | Front-load the punchline; avoid colon-prefixed title |
| `SUMMARY`      | 1-2 sentence teaser | Includes project + key numbers + "为什么值得读" |
| `CHAT_ID`      | Routing target (per article type) | Tech → `oc_cde2971ca05c08d8b36f4a3f86a6544a`, Parent → `oc_4e795533760520c636df4e7a0260c29f` |

## Variations to add when needed

- **Re-publish version banner** — add `(v4.0.0 重新发布)` to the SUMMARY so
  the 助理 knows it's a re-publish, not a duplicate. Combine with the
  versioned OSS key and cover-color change from
  `republish-same-project.md`.
- **Image-bearing article** — after step 3, also upload the tweet/image asset
  to OSS at `aicoder/<topic>/<asset>.jpg` and prepend a `📷 原文图` line to
  the post content block.
- **Multi-asset article** — split into a single post + N body chunks; the
  post lists all asset URLs, the body uses markdown without images (Feishu
  strips them).

## Don't write inline in chat

The script should be saved to `/tmp/publish_<slug>.py` and run via
`/Users/nowcoder/miniconda3/bin/python3`, not pasted as a heredoc into the
chat. Heredoc-in-chat loses indentation, breaks the `'''` quoting, and
makes debugging impossible. **Always file-then-run.**

## Pitfalls captured by this template

- The `'"ok": true" in result.stdout` check is the most common typo when typing the
  script inline (mismatched quote types). The template has it right.
- `time.sleep(1)` before the first chunk and `time.sleep(0.5)` between
  chunks avoids Feishu rate limiting on bulk sends.
- `os.path.abspath()` is required for the file:// URL because Playwright
  doesn't resolve relative paths from CWD in subprocess context.
- Same-shell-script oss2 client creation uses `bucket.put_object(key, file, headers=...)`
  — the third positional arg is `headers` (dict), and passing
  `{'Cache-Control': 'max-age=86400'}` lets the browser cache the cover
  for 24 hours, avoiding CDN misses on re-publishes.