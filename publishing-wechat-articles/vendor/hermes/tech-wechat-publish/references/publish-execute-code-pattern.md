# Verified execute_code Publish Script (2026-07-13)

This script was verified working end-to-end in a single `execute_code` block. It handles: cover render → OSS upload (cover + HTML) → Feishu send → table record write.

## When to use

When you have:
- A rendered HTML article at `/tmp/<slug>.html`
- A cover HTML template at `/tmp/cover-<slug>.html` (already edited with content)
- Need to publish to 技术号 (hermes-ali-ecs)

## Script

```python
import subprocess, json, re, sys, os, hashlib, hmac, datetime, base64, urllib.request, ssl

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

# ========== CONFIG ==========
SLUG = "xcode27-agent-skills"
DATE = "20260713"
TITLE = "Apple 把「编程规范」喂给了 AI：Xcode 27 官方 Agent Skills 深度解读"
SUMMARY = "Apple 亲自下场教 AI 写 iOS 代码。7 个官方 Skill 覆盖 SwiftUI、UIKit 现代化、Swift Testing、C 边界安全、Xcode 安全加固。"
CHAT_ID = "oc_a8a9c19552135fec945d861a967bb465"  # hermes-ali-ecs (首选)
# =============================

# Step 1: Render cover
from playwright.sync_api import sync_playwright
html_path = os.path.abspath(f'/tmp/cover-{SLUG}.html')
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1200, 'height': 540}, device_scale_factor=2)
    page.goto(f'file://{html_path}', wait_until='networkidle')
    page.wait_for_timeout(2000)
    page.screenshot(path=f'/tmp/cover-{SLUG}.png', type='png')
    browser.close()

# Step 2: OSS upload helper
ak = '__MIGRATED_TO_RUNTIME_LOCAL__'
sk = '__MIGRATED_TO_RUNTIME_LOCAL__'
bucket_name = 'kaelblog'
region = 'cn-beijing'

def oss_upload(local_path, key, content_type='image/png'):
    with open(local_path, 'rb') as f:
        body = f.read()
    date_str = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    string_to_sign = f'PUT\n\n{content_type}\n{date_str}\n/{bucket_name}/{key}'
    signature = base64.b64encode(
        hmac.new(sk.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    url = f'https://{bucket_name}.oss-{region}.aliyuncs.com/{key}'
    req = urllib.request.Request(url, data=body, method='PUT')
    req.add_header('Authorization', f'AWS {ak}:{signature}')
    req.add_header('Content-Type', content_type)
    req.add_header('Date', date_str)
    resp = urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context())
    return url

cover_url = oss_upload(f'/tmp/cover-{SLUG}.png', f'wechat/{SLUG}-{DATE}.png')
html_url = oss_upload(f'/tmp/{SLUG}.html', f'wechat/{SLUG}-{DATE}.html', 'text/html; charset=utf-8')

# Step 3: Feishu send (single message with all links)
feishu_msg = f"""📄 **{TITLE}**

📝 {SUMMARY}

📎 封面图：{cover_url}

📄 HTML 完整版：{html_url}

> 助理请打开 HTML 链接 → Ctrl+A 全选 → 复制 → 粘贴到公众号编辑器"""

result = subprocess.run(
    ['lark-cli', 'im', '+messages-send', '--chat-id', CHAT_ID,
     '--as', 'user', '--markdown', feishu_msg],
    capture_output=True, text=True, timeout=30
)
stdout = re.sub(r'^\[lark-cli\].*?\n', '', result.stdout, flags=re.MULTILINE)
resp = json.loads(stdout)
mid = resp['data']['message_id'] if resp.get('ok') else 'FAILED'

# Step 4: Write to Feishu table
table_result = subprocess.run(
    ['lark-cli', 'base', '+record-batch-create',
     '--base-token', 'B4kUbyJxeaSw1Xszsf1c0rARn0d',
     '--table-id', 'tbl20LZ82JPLOnpM',
     '--as', 'user',
     '--json', json.dumps({
         "fields": ["内容", "是否已发布", "标题", "摘要", "封面"],
         "rows": [[html_url, False, TITLE, SUMMARY, cover_url]]
     })],
    capture_output=True, text=True, timeout=30
)

print(f"✅ Cover: {cover_url}")
print(f"✅ HTML: {html_url}")
print(f"✅ Feishu: {mid}")
print(f"✅ Table: {'ok' if '\"ok\": true' in table_result.stdout else 'check'}")
```

## Key points

- `device_scale_factor=2` is mandatory for retina-quality cover
- OSS upload uses HTTP PUT + V1 signature (no oss2 SDK dependency)
- Feishu message is a single `--markdown` with all links (no segmented body)
- Table record uses `--as user` (bot has no `base:field:read` permission)
- "是否已发布" is checkbox (boolean), default `false`
- Field order for 技术号: 内容, 是否已发布, 标题, 摘要, 封面
