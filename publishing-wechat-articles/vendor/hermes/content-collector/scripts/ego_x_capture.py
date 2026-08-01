#!/usr/bin/env python3
"""
ego-lite X/Twitter capture — extracts tweet content via real browser.

As a fallback when fxtwitter fails or returns truncated content.
Uses ego-browser's real Chrome instance (reuses login state).

Usage:
    from ego_x_capture import capture_with_ego_lite
    result = capture_with_ego_lite("https://x.com/user/status/123456")

Returns:
    {
        "source_url": str,
        "capture_method": "ego-lite",
        "author": {"name": str, "handle": str},
        "text": str,
        "images": [{"index": int, "url": str, "alt": str}],
        "datetime": str,
        "engagement": {"replies": str, "retweets": str, "likes": str, "bookmarks": str, "views": str},
        "thread": {"isThread": bool, "tweets": [...]},
    }

Requires: ego-lite installed (npm skills add citrolabs/ego-lite)
"""

import json
import os as _os
import subprocess
import re
import sys


def capture_with_ego_lite(url: str, timeout: int = 120) -> dict:
    """
    Capture X/Twitter content using ego-lite browser.
    
    Args:
        url: X/Twitter tweet URL
        timeout: Max seconds to wait for ego-browser
        
    Returns:
        Parsed JSON dict with tweet content, images, engagement data
        
    Raises:
        RuntimeError: If ego-browser fails or returns no data
    """
    js_code = r'''
const task = await useOrCreateTaskSpace('ego_x_capture')
const url = 'URL_PLACEHOLDER'

// Retry loop: X pages often show "出错了" on first load
let data = null
for (let attempt = 1; attempt <= 3; attempt++) {
  await openOrReuseTab(url, { wait: true, timeout: 30 })
  await waitForNetworkIdle({ timeout: 15 })
  await wait(2)

  const check = await js(String.raw`(() => {
    const article = document.querySelector('article')
    const hasTweetText = !!article?.querySelector('[data-testid="tweetText"]')
    const hasError = !!document.querySelector('[role="status"]')
    return { hasArticle: !!article, hasTweetText, hasError }
  })()`)

  if (check.hasArticle && check.hasTweetText && !check.hasError) break

  cliLog('[attempt ' + attempt + '/3] page error, retrying...')

  // Try clicking retry button
  const clicked = await js(String.raw`(() => {
    const btns = [...document.querySelectorAll('button')]
    const retry = btns.find(b => b.innerText.includes('重试') || b.innerText.includes('Retry'))
    if (retry) { retry.click(); return true }
    return false
  })()`)

  if (!clicked) {
    await gotoAndWait(url, { timeout: 30, settle: 3 })
  }
  await wait(3)
}

data = await js(String.raw`(() => {
  const article = document.querySelector('article')
  if (!article) return { error: 'no article found after 3 retries' }
  const tweetText = article.querySelector('[data-testid="tweetText"]')
  const text = tweetText ? tweetText.innerText : ''
  const images = [...article.querySelectorAll('[data-testid="tweetPhoto"] img')]
    .map((img, i) => ({ index: i, url: img.src, alt: img.alt || '' }))
  const userName = article.querySelector('[data-testid="User-Name"]')
  const authorLines = userName ? userName.innerText.split('\n') : []
  const author = { name: authorLines[0] || '', handle: authorLines[1] || '' }
  const time = article.querySelector('time')
  const datetime = time ? time.getAttribute('datetime') : ''
  const getVal = (testId) => {
    const el = article.querySelector('[data-testid="' + testId + '"]')
    if (!el) return '0'
    const m = (el.getAttribute('aria-label') || '').match(/([\d,.]+)/)
    return m ? m[1] : '0'
  }
  const engagement = {
    replies: getVal('reply'), retweets: getVal('retweet'),
    likes: getVal('like'), bookmarks: getVal('bookmark'),
    views: (() => { const el = article.querySelector('a[href*="/analytics"]'); return el ? el.innerText.trim() : '0' })()
  }
  return { author, text, images, datetime, engagement }
})()`)

const threadData = await js(String.raw`(() => {
  const articles = document.querySelectorAll('article')
  if (articles.length <= 1) return { isThread: false, tweets: [] }
  const tweets = []
  for (const art of articles) {
    const tweetText = art.querySelector('[data-testid="tweetText"]')
    const userName = art.querySelector('[data-testid="User-Name"]')
    const authorLines = userName ? userName.innerText.split('\n') : []
    const time = art.querySelector('time')
    if (tweetText) {
      tweets.push({
        author: authorLines[0] || '', handle: authorLines[1] || '',
        text: tweetText.innerText, datetime: time ? time.getAttribute('datetime') : ''
      })
    }
  }
  return { isThread: tweets.length > 1, tweets }
})()`)

const result = { source_url: 'URL_PLACEHOLDER', captured_at: new Date().toISOString(), capture_method: 'ego-lite', ...data, thread: threadData }
cliLog(JSON.stringify(result, null, 2))
    '''.replace("URL_PLACEHOLDER", url)
    
    # Run ego-browser
    try:
        proc = subprocess.run(
            ["ego-browser", "nodejs"],
            input=js_code,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "ego-browser not found. Install with: npx skills add citrolabs/ego-lite"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ego-browser timed out after {timeout}s")
    
    if proc.returncode != 0:
        raise RuntimeError(
            f"ego-browser failed (exit {proc.returncode}): {proc.stderr[:500]}"
        )
    
    # Parse JSON from output — ego-browser writes to stderr
    output = proc.stderr + "\n" + proc.stdout
    json_match = re.search(r'\{[\s\S]*\}', output)
    if not json_match:
        raise RuntimeError(f"No JSON found in ego-browser output: {output[:500]}")
    
    try:
        result = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from ego-browser: {e}\n{json_match.group()[:500]}")
    
    if result.get("error"):
        raise RuntimeError(f"ego-lite extraction failed: {result['error']}")
    
    return result


def capture_with_ego_lite_safe(url: str, timeout: int = 120) -> dict | None:
    """Safe version — returns None on failure instead of raising."""
    try:
        return capture_with_ego_lite(url, timeout)
    except Exception as e:
        print(f"[ego-lite] Failed: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    import shutil
    
    if len(sys.argv) < 2:
        print("Usage: python3 ego_x_capture.py <tweet_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    result = None
    
    # Try ego-lite first (if installed)
    if shutil.which("ego-browser"):
        print("[capture] Trying ego-lite...", file=sys.stderr)
        result = capture_with_ego_lite_safe(url)
    
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    
    # Fallback to fxtwitter
    print("[capture] ego-lite unavailable/failed, trying fxtwitter...", file=sys.stderr)
    import re as _re
    m = _re.search(r'(?:x\.com|twitter\.com)/(\w+)/status/(\d+)', url)
    if m:
        fxt_url = f"https://api.fxtwitter.com/{m.group(1)}/status/{m.group(2)}"
        # Try curl first (more reliable with SSL/proxy)
        try:
            import subprocess as _sp
            curl = _sp.run(["curl", "-sL", "--max-time", "15", fxt_url], capture_output=True, text=True,
                          env={**_os.environ, "NO_PROXY": "api.fxtwitter.com", "no_proxy": "api.fxtwitter.com"})
            if curl.returncode == 0 and '"tweet"' in curl.stdout:
                fxt_data = json.loads(curl.stdout)
                t = fxt_data["tweet"]
                media_list = t.get("media", {})
                if isinstance(media_list, dict):
                    media_list = media_list.get("all", []) or media_list.get("photos", [])
                elif not isinstance(media_list, list):
                    media_list = []
                result = {
                    "source_url": url,
                    "capture_method": "fxtwitter",
                    "author": {"name": t.get("author", {}).get("name", ""), "handle": t.get("author", {}).get("screen_name", "")},
                    "text": t.get("text", ""),
                    "images": [{"index": i, "url": m.get("url", ""), "alt": ""} for i, m in enumerate(media_list)],
                    "datetime": t.get("created_at", ""),
                    "engagement": {"likes": str(t.get("likes", 0)), "retweets": str(t.get("retweets", 0)), "bookmarks": str(t.get("bookmarks", 0)), "views": str(t.get("views", 0))},
                    "thread": {"isThread": bool(t.get("thread")), "tweets": [{"text": x.get("text", "")} for x in t.get("thread", [])]}
                }
                print(json.dumps(result, ensure_ascii=False, indent=2))
                sys.exit(0)
        except Exception as e:
            print(f"[capture] curl fxtwitter failed: {e}", file=sys.stderr)
        # Fallback to urllib
        try:
            import urllib.request
            req = urllib.request.Request(fxt_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                fxt_data = json.loads(resp.read())
                if "tweet" in fxt_data:
                    t = fxt_data["tweet"]
                    media_list = t.get("media", {})
                    if isinstance(media_list, dict):
                        media_list = media_list.get("all", []) or media_list.get("photos", [])
                    elif not isinstance(media_list, list):
                        media_list = []
                    result = {
                        "source_url": url,
                        "capture_method": "fxtwitter",
                        "author": {"name": t.get("author", {}).get("name", ""), "handle": t.get("author", {}).get("screen_name", "")},
                        "text": t.get("text", ""),
                        "images": [{"index": i, "url": m.get("url", ""), "alt": ""} for i, m in enumerate(media_list)],
                        "datetime": t.get("created_at", ""),
                        "engagement": {"likes": str(t.get("likes", 0)), "retweets": str(t.get("retweets", 0)), "bookmarks": str(t.get("bookmarks", 0)), "views": str(t.get("views", 0))},
                        "thread": {"isThread": bool(t.get("thread")), "tweets": [{"text": x.get("text", "")} for x in t.get("thread", [])]}
                    }
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    sys.exit(0)
        except Exception as e:
            print(f"[capture] urllib fxtwitter failed: {e}", file=sys.stderr)
    
    print("[capture] All methods failed", file=sys.stderr)
    sys.exit(1)
