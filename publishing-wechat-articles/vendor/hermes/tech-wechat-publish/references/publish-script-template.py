#!/usr/bin/env python3
"""
End-to-end publishing script: OSS cover upload + Feishu article send.
Copy this to /tmp/ and adapt the ARTICLE_PATH, COVER_PATH, TITLE, SUMMARY vars.

Usage: /Users/nowcoder/miniconda3/bin/python3 /tmp/publish.py

Tested: 2026-06-23 (Swift 6.4 Concurrency + SwiftUI Agent Skill articles)
"""
import oss2, subprocess, json, re, time, os

# === CONFIG — adapt these per article ===
ARTICLE_PATH = "/tmp/article.md"
COVER_PATH = "/tmp/cover.png"
OSS_KEY = "wechat/<slug>-<date>.png"  # e.g. wechat/swift-6-4-concurrency-20260623.png
TITLE = "文章标题"
SUMMARY = "一句话摘要（用于飞书 post 请求里的摘要字段）"
CHAT_ID = "oc_cde2971ca05c08d8b36f4a3f86a6544a"  # AICoder 内容助手

# OSS credentials (from config.yaml)
OSS_AK = "__MIGRATED_TO_RUNTIME_LOCAL__"
OSS_SK = "__MIGRATED_TO_RUNTIME_LOCAL__"
OSS_BUCKET = "kaelblog"
OSS_ENDPOINT = "https://oss-cn-beijing.aliyuncs.com"
# === END CONFIG ===


def upload_cover():
    """Upload cover PNG to OSS, return public URL."""
    auth = oss2.Auth(OSS_AK, OSS_SK)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)
    with open(COVER_PATH, "rb") as f:
        bucket.put_object(OSS_KEY, f, headers={
            "Content-Type": "image/png",
            "Cache-Control": "max-age=86400",
        })
    url = f"https://{OSS_BUCKET}.oss-cn-beijing.aliyuncs.com/{OSS_KEY}"
    print(f"Cover uploaded: {url}")
    return url


def send_post_request(cover_url):
    """Send post message with title + summary + cover URL."""
    post_content = {
        "zh_cn": {
            "title": "公众号文章发布请求",
            "content": [
                [{"tag": "text", "text": "请帮忙发布公众号文章\n\n"}],
                [{"tag": "text", "text": f"标题：{TITLE}\n\n"}],
                [{"tag": "text", "text": f"摘要：{SUMMARY}\n\n"}],
                [{"tag": "text", "text": f"封面图：{cover_url}\n\n"}],
                [{"tag": "text", "text": "完整文案见下方消息。"}],
            ],
        }
    }
    content_str = json.dumps(post_content, ensure_ascii=False)
    result = subprocess.run(
        ["lark-cli", "im", "+messages-send", "--chat-id", CHAT_ID,
         "--as", "user", "--msg-type", "post", "--content", content_str],
        capture_output=True, text=True, timeout=30,
    )
    ok = '"ok": true' in result.stdout or '"code": 0' in result.stdout
    if not ok:
        print(f"Post request FAILED: {result.stdout[:300]}")
        raise RuntimeError("Post request failed")
    print("Post request sent (title + summary + cover)")


def send_article_body():
    """Split article into ≤900 char chunks and send each as markdown."""
    article = open(ARTICLE_PATH).read()
    # Remove horizontal rules (Feishu renders them as breaks)
    article = article.replace("\n---\n", "\n\n").replace("\n---", "\n\n").replace("---\n", "\n\n")

    # Paragraph-aware chunking
    chunks = []
    current = ""
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

    print(f"Article split into {len(chunks)} chunks")
    time.sleep(1)

    for i, chunk in enumerate(chunks, 1):
        result = subprocess.run(
            ["lark-cli", "im", "+messages-send", "--chat-id", CHAT_ID,
             "--as", "user", "--markdown", chunk],
            capture_output=True, text=True, timeout=30,
        )
        ok = '"ok": true' in result.stdout or '"code": 0' in result.stdout
        if not ok:
            print(f"Chunk {i}/{len(chunks)} FAILED: {result.stdout[:200]}")
            raise RuntimeError(f"Chunk {i} failed")
        print(f"  Chunk {i}/{len(chunks)} sent ({len(chunk)} chars)")
        time.sleep(0.5)

    print(f"\nAll {len(chunks)} chunks sent successfully")


if __name__ == "__main__":
    cover_url = upload_cover()
    send_post_request(cover_url)
    send_article_body()
    print(f"\nDone. Title: {TITLE}")
    print(f"Cover: {cover_url}")
