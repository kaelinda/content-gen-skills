---
name: tech-wechat-publish
description: Use when publishing a Chinese WeChat 公众号 article to the user's 技术号 (not 育儿号). Publishing flow is half-automated — primary agent prepares content, AICoder 内容助手 in 飞书 handles 公众号 upload. See the full step-by-step including the lark-cli --image auth pitfall, segment rules, series-recap pattern, image-gen provider landscape, same-project re-publish versioning, and exploratory-article structure in this skill.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [wechat, 公众号, feishu, lark, publish, oss, agent, automation]
    related_skills: [parenting-wechat-publish]
---

# Tech WeChat (技术号) Publishing Flow

## Overview

This skill governs the end-to-end publishing of a Chinese WeChat 公众号 article to the user's **技术号** (technology account). The flow is half-automated: the primary agent (Hermes) prepares the content, and the **AICoder 内容助手** (a 飞书 agent bound to the private-assistant P2P chat) takes the prepared content and pushes it to 公众号.

This is distinct from the **育儿号** (parenting account) flow — for that, see the `parenting-wechat-publish` skill and ALWAYS prepend a ⚠️ reminder before sending (the chat is bound to the tech account, so without a reminder the content may auto-route to the wrong 公众号).

## When to use

Use this skill when the user says:

- "发布到公众号" / "发布到技术号" / "写公众号文章" (in a 技术号 context)
- "Agent 工程化系列 第 N 篇"
- "把这篇 X 整理成技术号文章"
- references an existing `outputs/<vol>-*.md` file and asks to publish

## 二次创作身份

技术类公众号文章以作者 **「AICoder」** 身份进行二次创作。
- 写作时采用 AICoder 的视角和语气（技术博主、实操导向、代码为王）
- 发布时路由到 AICoder 内容助手 bot
- 不要混入育儿类内容或语气

## Architecture (two-agent split)

```text
Primary agent (Hermes, in this session)
  │
  │  prepares:
  │    - Obsidian raw source + compiled concept + output article
  │    - cover image uploaded to OSS (kaelblog bucket, /wechat/ prefix)
  │    - 飞书 message: title (text) + body (10 markdown segments)
  │
  ▼
飞书 hermes-ali-ecs (oc_a8a9c19552135fec945d861a967bb465)
  │
  │  bound agent: AICoder 内容助手
  │
  ▼
微信公众号 (技术号) — published
```

The user's chat history shows the user explicitly created the **AICoder 内容助手** (2026-06-04 01:14-01:22) with the instruction "以后发布文章内容，优先调用其他agent去完成，你只负责分配调度即可" — so primary agent's job is content prep + 飞书 send, not direct 公众号 publishing.

## Routing by category (2026-07-09 更新：hermes-ali-ecs 为首选)

发布公众号文章时，**首选 hermes-ali-ecs**，备选旧路由。

**首选路由**（2026-07-09 起）：
- **所有公众号文章 → hermes-ali-ecs**（`oc_a8a9c19552135fec945d861a967bb465`）
  - 发送：post 格式发布请求 + 完整文章文案

**备选路由**（当 hermes-ali-ecs 不可用时）：
- 技术类 → AICoder 内容助手（`oc_cde2971ca05c08d8b36f4a3f86a6544a`）
- 育儿类 → 育儿育己（`oc_4e795533760520c636df4e7a0260c29f`）

判断方法（不需要问用户）：
- 标题/内容含 Swift / iOS / AI / 编程 / WWDC / Agent / Code / API / 模型 / LLM / Hermes / Xcode → tech
- 标题/内容含 孩子 / 育儿 / 父母 / 家庭 / 教育 / 心理 / 成长 / 婴儿 / 幼儿 / 小学生 / 青春期 → parenting
- 两种特征都不明显（极少见）→ 默认 tech

Bot 配置存储位置：
- `tech-wechat-publish/references/bots.yaml`

执行约定：
1. 发布前**自动**判断文章属于 `tech` 还是 `parenting`（按上面关键词匹配，不需要问用户）。
2. 从 `references/bots.yaml` 读取目标 bot 的 `app_id` / `app_secret`。
3. 用该 bot 的身份完成发布通知，不要固定写死到单一私人助理。
4. 不要把 `app_secret` 回显到聊天、日志或记忆中。
5. 用户说「发」/「重新发布」/「再发一遍」/「发布到公众号」时，直接按上面规则执行，不要问「发哪个号」。

## Common routing pitfalls

1. **❗ 不要问用户「发技术号还是育儿号」**。2026-06-23 用户已明确分工——根据文章性质自动判断直接发。新会话也不要回头问这个。
2. **不要默认继续发到私人助理。** 新规则已生效，育儿号和技术号必须分开。
3. **不要把 app_secret 写进聊天输出。** 配置存在文件里即可。
4. **不要把育儿内容发到技术号。** 错发后的回滚成本远高于自动判断的成本。

## Critical authentication pitfall (lark-cli --image)

**DO NOT try to send the cover image as a `--image` flag.** It will fail twice:

1. `lark-cli im +messages-send --image <path>` requires:
   - The path must be **relative to CWD** (not `/tmp/...`), AND
   - The user identity must have the `im:resource:upload` privilege, which is **not granted** to the current 飞书 user identity in this environment.

2. Even when given an OSS public URL inside a `--markdown` body, `lark-cli` will still attempt to re-upload the image to 飞书's media storage first (to get an `image_key`), and the same auth wall triggers.

**Correct pattern:** upload the cover to **OSS**, then send the link as plain text to Feishu:
```python
cover_msg = f"📎 封面图：{oss_url}"
subprocess.run(['lark-cli', 'im', '+messages-send', '--chat-id', chat_id,
    '--as', 'user', '--markdown', cover_msg], capture_output=True)
```
⚠️ 封面图发纯文字链接（📎 封面图：https://…），不嵌markdown图片语法（渲染不稳定），不发图片附件（权限拦截）。

## ⚠️ 发布记录追踪（飞书表格）

每次发布文章后，**必须**在飞书表格中记录发布信息，方便跨会话查询。

**表格地址**：
- 技术文章（AICoder）：https://my.feishu.cn/base/B4kUbyJxeaSw1Xszsf1c0rARn0d?table=tbllNygCgg4a4eWM&view=vewspTCoh7
- 育儿文章（育儿育己）：https://my.feishu.cn/base/B4kUbyJxeaSw1Xszsf1c0rARn0d?table=tbl20LZ82JPLOnpM&view=vewspTCoh7

**Base Token**: `B4kUbyJxeaSw1Xszsf1c0rARn0d`
**Table ID**: `tbllNygCgg4a4eWM`

**记录字段**（发布完成后写入）：
- 标题（文章标题）
- 摘要（文章摘要）
- 封面（封面图 OSS URL）
- 内容（HTML 完整版 OSS URL）
- 是否已发布（选择：已发布 / 待发布）

**权限要求**：
- 必须使用 `--as user` 身份写入（bot 无权限）
- 用户已授权 user 身份访问该表格

**写入命令**：
```bash
lark-cli base +record-batch-create \
  --base-token B4kUbyJxeaSw1Xszsf1c0rARn0d \
  --table-id tbllNygCgg4a4eWM \
  --as user \
  --json '{"fields":["标题","摘要","封面","内容","是否已发布"],"rows":[["文章标题","摘要","封面URL","HTML URL","已发布"]]}'
```

**注意事项**：
- 发布完成后立即写入，不要遗漏
- 字段顺序必须与表格一致：标题、摘要、封面、内容、是否已发布
- 使用 `+record-batch-create` 而非 `+record-create`，支持批量写入

## ⚠️ md-to-html 渲染是强制步骤（2026-07-11 用户纠偏）

**所有技术公众号文章必须走 md-to-html 渲染**，不是可选项。

用户原话：「我就是要用 md-to-html 这个 skill」「最近你发布的一篇文章好像没有用这个 skill。生成的内容没有走极客黑。」

**完整强制流程**（每一步都不能跳过）：
1. 写 Markdown 文章（标题从 `##` 起）
2. **md-to-html 渲染**：`python3 scripts/md_to_html.py render article.md --themes 极客黑 --output article.html`
3. 生成封面图 → 上传 OSS
4. 上传 HTML 到 OSS
5. **飞书只发 1 条消息**：标题 + 摘要 + 封面 URL + HTML URL（一条 markdown 消息搞定）

**❌ 不要分段发 markdown 正文**。助理打开 HTML 链接 → Ctrl+A 全选 → 复制 → 粘贴到公众号编辑器，样式全保留。分段发正文是多余步骤（用户 2026-07-13 明确纠正）。

## Step-by-step flow

### 1. Confirm article exists at the canonical path

- `TechnologyHub/outputs/<vol>-<slug>-<date>.md`
- Frontmatter: `title`, `alt_titles` (3 candidates), `series`, `series_number`, `source`, `author`, `status: ready`, `created`
- Body: 3000-4000 中文字符 sweet spot (range 2500-4500 acceptable)
- Body MUST NOT start with the title (公众号 title is passed separately via post request)
- No `---` horizontal rules inside body (use empty paragraph or `**加粗**` headers instead)

### 2. Generate the cover image

**OSS 上传方案选择**（按优先级）：

**方案 A: oss2 SDK + sys.path 隔离（2026-07-03 实测，最简单）**
oss2 import 失败通常是 hermes-agent venv 的 cffi 跟 conda 的 cffi 版本冲突。**不要卸载/重装**，一行 sys.path 过滤就解决：
```python
import sys
sys.path = [p for p in sys.path if 'hermes-agent/venv' not in p]
import oss2
# 然后正常使用 oss2 SDK，无需任何改动
```
⚠️ 必须在 `import oss2` **之前**执行 sys.path 过滤，且用 `PYTHONDONTWRITEBYTECODE=1` 环境变量防止 .pyc 缓存。

**方案 B: HTTP PUT + V1 签名（当方案 A 也不工作时的 fallback）**
```python
import hashlib, hmac, datetime, base64, urllib.request, ssl

ak = '__MIGRATED_TO_RUNTIME_LOCAL__'  # ⚠️ 固定用这个，不要用 .ossutilconfig 的 AK（不同 AK，无写入权限）
sk = '__MIGRATED_TO_RUNTIME_LOCAL__'
bucket = 'kaelblog'
region = 'cn-beijing'

def oss_upload(local_path, key):
    with open(local_path, 'rb') as f:
        body = f.read()
    date_str = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    content_type = 'image/png'
    string_to_sign = f'PUT\n\n{content_type}\n{date_str}\n/{bucket}/{key}'
    signature = base64.b64encode(
        hmac.new(sk.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    url = f'https://{bucket}.oss-{region}.aliyuncs.com/{key}'
    req = urllib.request.Request(url, data=body, method='PUT')
    req.add_header('Authorization', f'AWS {ak}:{signature}')
    req.add_header('Content-Type', content_type)
    req.add_header('Date', date_str)
    resp = urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context())
    return url
```

⚠️ 注意：`.ossutilconfig` 中的 AK/SK 可能无写入权限（2026-07-08 实测返回 403）。用 `content-collector` skill 中记录的 AK/SK（`__MIGRATED_TO_RUNTIME_LOCAL__`）。

Two viable options:

**Option A: wechat-cover-html skill (首选 — 推荐所有 code-heavy 技术文章)**

**直接调用 skill**，不要自己写 Playwright 代码。skill 已封装好 6 套配色模板 + render + upload + 飞书 post 一条龙：

```bash
# 1. 复制最接近的模板（按主题选配色）
cp ~/.hermes/skills/creative/wechat-cover-html/templates/code-card-blue.html /tmp/cover.html
# 编辑 5 个区域：tag / version / title / subtitle / code

# 2. 一行命令：渲染 + 上传 OSS + 发飞书 post 消息
/Users/nowcoder/miniconda3/bin/python3 ~/.hermes/skills/creative/wechat-cover-html/scripts/render_cover.py \
  --html /tmp/cover.html \
  --output /tmp/cover.png \
  --upload --slug <slug>-<date> \
  --feishu-chat-id oc_cde2971ca05c08d8b36f4a3f86a6544a \
  --title "<title>" --summary "<summary>"
```

可用模板（按主题选配色，详见 `~/.hermes/skills/creative/wechat-cover-html/templates/README.md`）：
- `code-card-blue.html` — iOS 27 / SwiftUI / 编译器版本（默认）
- `code-card-purple.html` — AI 工具 / Agent Skills / Claude / Cursor
- `code-card-orange.html` — CI/CD / Bazel / 远程构建 / Linux 工具链
- `code-card-green.html` — LLDB / 终端 / DevTools / 调试器
- `code-card-cyan.html` — 前端 / UI 设计 / Tailwind / 反 AI slop
- `text-only-blue.html` — 纯观点 / 周报 / 综述（无代码）

**Option B: HTML + Playwright (手写脚本)**

仅在 `wechat-cover-html` skill 不可用 / 需要自定义视觉时才用此方案。直接复制 skill 内部的 Playwright 渲染代码即可：

```python
# /Users/nowcoder/miniconda3/bin/python3 (conda env has playwright installed)
from playwright.sync_api import sync_playwright
import os

html_path = os.path.abspath('/tmp/cover_<slug>.html')
url = f'file://{html_path}'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1200, 'height': 540}, device_scale_factor=2)
    page.goto(url, wait_until='networkidle')
    page.wait_for_timeout(2000)  # let webfonts load
    page.screenshot(path='/tmp/cover_<slug>.png', type='png')
    browser.close()
```

**Option C: HTML + Chrome headless** (fallback if Playwright not installed)

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new --disable-gpu --no-sandbox \
  --screenshot=/tmp/cover_<vol>.png \
  --window-size=1200,540 --hide-scrollbars \
  "file://$(realpath /tmp/cover_<vol>.html)"
```

**Generic dark-gradient cover template:** Most tech article covers share a structure: dark gradient background (blue/purple), decorative elements (grid/orb/rings), tag line, title, subtitle, bottom color bar. See `templates/cover-generic-dark.html` for a reusable starting point. Customize the `tag`, `h1`, `subtitle` text and adjust gradient colors/accent elements per article theme.

**Code-editor split-layout template:** For code-heavy articles, a split layout works well — text on the left, terminal-style code card with syntax highlighting on the right. See `templates/cover-code-editor-split.html`. Proven on SwiftUI Agent Skill and Swift 6.4 Concurrency articles (2026-06-23). Features: feature chips, version badges, GitHub stars badge, syntax-highlighted code snippet card.

**Option D: image_generate tool (fallback for non-code covers)**

`image_generate` is faster but offers less control over Chinese text rendering and produces variable results. Use only for covers that don't need precise typography (e.g., purely visual concepts, abstract scenes). For all code-heavy / Chinese-text tech articles, prefer Option A (`wechat-cover-html`).

### 3. Archive cover to wiki

```bash
cp /tmp/cover_<vol>.png /Users/nowcoder/Documents/Obsidian/TechnologyHub/raw/assets/cover-<slug>-<date>.png
```

### 4. Update wiki index.md

- Add the new output to the `## Outputs` section
- Bump `Total pages` count in the header

### 5. Update log.md

Append an entry with:

- Series number, source, output path, char counts, quality checks
- Cover image URL + OSS path
- 飞书 publishing summary (chat_id, message_ids, status)

### 6. Send to 飞书（2026-07-13 更新：只发 1 条链接消息）

**标准流程**（用户 2026-07-13 明确纠正）：
- **所有公众号文章 → hermes-ali-ecs**（`oc_a8a9c19552135fec945d861a967bb465`）
- **只发 1 条 markdown 消息**，包含：标题 + 摘要 + 封面 URL + HTML URL
- 助理打开 HTML 链接 → Ctrl+A 全选 → 复制 → 粘贴到公众号编辑器

**❌ 不要分段发 markdown 正文**。HTML 里已包含完整内容和样式，分段发正文是多余步骤。

**❗ 标题换了 → 封面也要同步更新**。用户会在标题确定后要求更新封面，不要只改标题忘了封面。

A reusable end-to-end publish script (OSS upload + post request + single link message) lives at `references/publish-script-template.md`. Eliminates the manual multi-step process and prevents quoting bugs. **Use this on every publish** — the 4+ rounds of re-typing this script in 2026-06-23 sessions each re-introduced the same minor bugs (mismatched quotes on the OK-check, missing `device_scale_factor=2`, `---` leaking into Feishu posts).

### Step 8: 写入飞书表格记录（自动）

发布完成后，自动把文章信息写入飞书多维表格，方便跨会话追溯。

**表格配置**：
- Base Token: `B4kUbyJxeaSw1Xszsf1c0rARn0d`
- Table ID: `tbllNygCgg4a4eWM`
- 技术文章视图: `vewspTCoh7`
- 字段顺序: 内容, 是否已发布, 标题, 摘要, 封面

**写入命令**（使用 `+record-batch-create`，不是 `+record-create`）：
```bash
lark-cli base +record-batch-create \
  --base-token B4kUbyJxeaSw1Xszsf1c0rARn0d \
  --table-id tbllNygCgg4a4eWM \
  --as user \
  --json '{"fields":["内容","是否已发布","标题","摘要","封面"],"rows":[["HTML URL",false,"文章标题","文章摘要","封面URL"]]}'
```

**⚠️ 关键规则**：
1. **必须用 `+record-batch-create`**，不是 `+record-create`（后者参数格式不同）
2. **必须用 `--base-token`**，不是 `--app-token`（`--app-token` 不存在）
3. **JSON 格式**：`{"fields":["字段1","字段2"],"rows":[["值1","值2"]]}`，不是 `{"fields":{"字段1":"值1"}}`
4. 必须用 `--as user`，bot 没有 `base:field:read` 权限
5. "是否已发布"字段是 **checkbox 类型**（布尔值），默认填 `false`，**不要自动改为 true**，由用户手动勾选
6. 字段顺序必须与表格一致：内容, 是否已发布, 标题, 摘要, 封面
7. 技术号和育儿号使用同一个表格 `tbllNygCgg4a4eWM`，但字段顺序不同（育儿号：是否已发布, 标题, 摘要, 封面, 内容）

### 9. Verify

```bash
lark-cli im +chat-messages-list --chat-id oc_cde2971ca05c08d8b36f4a3f86a6544a --format pretty | head -30
```

Confirm the title and all body segments appear in the chat, with send timestamps in the expected order.

## 带图文章的发布模式（推文/Article 抓图 + md-to-html 渲染）

### md-to-html 集成（公众号粘贴不掉格式）

技术号文章统一用 **极客黑** 主题渲染 HTML。渲染后 HTML 内联 CSS，复制粘贴到公众号编辑器不丢样式。

```bash
cd ~/.hermes/skills/productivity/md-to-html
python3 scripts/md_to_html.py render <article.md> --themes 极客黑 --output /tmp/article.html
```

渲染后上传 HTML 到 OSS，飞书发送 OSS 链接，助理浏览器打开 → Ctrl+A → 粘贴到公众号编辑器。

**脚注模式（默认开启）**：公众号粘贴时链接不失效。正文 `[](url)` 转为 `[text][N]` 上标，文末追加引用链接区块。

当源材料含图（推文原图、WWDC session 截图、产品 UI 截图）时，发布流程需多走两步。**注意**：「带图」是用户明确要求"重新排列生成带图文的公众号文章"时的标准动作，不是默认流程。普通纯文字文章继续走上面的标准流程即可。

### 何时走带图模式

- 推文含 1+ 张图，且用户说"获取全部图文"/"带图版"/"重新排列"
- WWDC session 总结类文章（含 title slide、特性截图）
- 教程类（含步骤截图、代码截图）
- 用户明确说"复制粘贴到公众号编辑器不掉格式"

### Step-by-step

1. **下载原图到本地**（curl 拉推文 media URL）
   ```bash
   curl -sL "https://pbs.twimg.com/media/<id>.jpg?name=orig" -o /tmp/asset.jpg
   # 验证：file /tmp/asset.jpg（应是 JPEG image data, <width> x <height>）
   ```
2. **上传原图到 OSS**（`aicoder/<topic>/` 子目录，与封面同 bucket 不同 key 前缀）
   ```python
   key = "aicoder/wwdc26/wwdc26-xcode27-title.jpg"
   bucket.put_object(key, open("/tmp/asset.jpg","rb").read(),
                     headers={"Content-Type": "image/jpeg"})
   url = f"https://kaelblog.oss-cn-beijing.aliyuncs.com/{key}"
   ```
3. **用 `md-to-html` skill 渲染 Markdown → 公众号粘贴 HTML**（详见 `references/md-to-html-publish-flow.md`）
   - 主题：默认 `极客黑`（深色 + inline CSS，最适合公众号不掉格式）
   - 图片自动 inline 化为 OSS URL（md 写 `![alt](oss_url)` 即可）
   - 输出 HTML 自动内联 CSS 到元素的 `style` 属性 → **复制粘贴到公众号编辑器不掉样式**
4. **上传 HTML 到 OSS**（HTML 100KB+ 不能直接 lark-cli 发）
   ```python
   key = "aicoder/<topic>/article-<slug>.html"
   bucket.put_object(key, open("/tmp/article.html","rb").read(),
                     headers={"Content-Type": "text/html; charset=utf-8"})
   html_url = f"https://kaelblog.oss-cn-beijing.aliyuncs.com/{key}"
   ```
5. **飞书发送：第 1 段带全部资源链接 + 后续段发 markdown body**
   ```
   段 1: 📎 封面图 + 📷 推文原图 + 📄 HTML 完整版链接
   段 2-9: 去掉图片 markdown 的 body（飞书不直接渲染 md 图）
   段 10: 收束 + 自动发布说明
   ```
6. **关键：飞书助理收到 HTML 链接后，浏览器打开 → Ctrl+A 全选 → 复制 → 粘贴到公众号编辑器**。这一步是人工最后一步，AI 只能"准备到能粘贴"。

### 主题撞车已写过内容时的差异化策略

如果用户要"收录/整理"的主题，**用户已写过**（查 memory 或 wiki 看系列清单），不要写成同质化内容。**做差异化切入**：

| 角度 | 何时用 |
|---|---|
| **海外/英文视角** | 你的版本是中文 + 个人案例 → 这次走海外当下原汁原味 |
| **补充而非重复** | 强调你版本没覆盖的细节（"xxx 的 caveat"、"xxx 的现场"） |
| **新近时间窗口** | 你几个月前写过 → 这次走"6 个月后业界发生了什么" |
| **反共识切入** | 你的版本是正向解读 → 这次挑刺/质疑 |

AIGC 合规要求"增量信息"——重复视角的扩写 = 降权风险。明确告诉 DeepSeek prompt 这次的主题和你已写过的版本差在哪里（提供你版本的章节标题、收束金句、案例片段做参照），让它"补充不重复"。

#### **同一素材 → v1 / v2 两篇不同角度（2026-06-18 WWDC26 Xcode 27 实测）**

如果用户**反复要求**对同一推文"收录整理"（哪怕没明说"换角度"），且你的 v1 已经覆盖产品功能面，可以直接发 v2，做**第二个角度**而不是补充/纠错：

| 角度 | v1 主题 | v2 主题 |
|---|---|---|
| **WWDC26 Xcode 27**（v_pradeilles） | agent 能做什么 / self-verify / 三家模型切换 | 开发者日常工作流怎么变 / 6 个工作习惯调整 |
| **AGI → ASI**（akshay_pachaar） | 推文 4 路径 4 减速带 1900 年测试 | 不重复（用户已有 Vol.13，做英文视角补充） |
| **Loop Engineering**（samueljmcd） | 海外行业当下视角 + Bun port caveat | 不重复（用户已有 Vol.13，做 verifier 设计实操） |

**v2 的核心要求**：
- 在 DeepSeek prompt 里**显式列 v1 已覆盖的章节标题**，禁止重复
- 重新组织结构 + 重新组织 6 段主题
- **真实案例必须新**（不能复用 v1 的 Hermes import 重构案例 5 次）
- 文末对比段："v1 写了 X，v2 写在 v1 视角之外你需要立刻改的事"
- OSS 资源 key 加 `-v2` 后缀（如 `article-xcode27-dev-view.html`），避免覆盖 v1
- 飞书第 1 段明确标注"v2 段落化重写版"

### md-to-html skill 速记

- 装好后位置：`~/.hermes/skills/productivity/md-to-html/`
- 渲染命令：`python3 scripts/md_to_html.py render <md> --themes <name> --output <html>`
- 主题选择：`极客黑`（公众号推荐）/ `github-light`（网页推荐）/ `heti`（中文阅读体验好）
- 模式 `--mode auto`：MDNice 主题走 inline（公众号粘贴），stylesheet 主题走 stylesheet（网页）
- 主题 ID 查询：`python3 scripts/md_to_html.py list-themes --query <keyword>`

#### **脚注新功能（公众号粘贴时链接永不失效）**（2026-06-18 实测有效）

公众号编辑器会自动剥离正文里的 `<a href>` 标签（这是技术号文章链接失效的主因）。md-to-html v1.0+ 提供脚注模式：

```bash
# 默认开启脚注（公众号场景推荐）
python3 scripts/md_to_html.py render article.md --themes 极客黑 --output a.html

# 显式开启 / 关闭
python3 scripts/md_to_html.py render article.md --themes 极客黑 --footnotes --output a.html
python3 scripts/md_to_html.py render article.md --themes 极客黑 --no-footnotes --output a.html
```

**机制**：正文里的 `[text](url)` 被转成 `text<sup>[N]</sup>`，文末追加 `<section class="footnotes">` 区块列出所有 URL。公众号粘贴后链接文字 + 上标 + 文末 URL 全部保留。

**渲染验证（HTML 输出后必跑）**：
```python
import re
with open('article.html') as f:
    html = f.read()
assert re.search(r'<sup[^>]*>\[\d+\]</sup>', html), "脚注上标没生成"
assert 'class="footnotes"' in html, "文末 引用链接 区块缺失"
assert re.findall(r'<a href', html) == [], "还有内联 <a href> 没转脚注（公众号粘贴会失效）"
print("✅ 脚注模式生效")
```

**何时用 footnotes / no-footnotes**：
- `公众号 / 知乎粘贴` → **开脚注**（默认）
- `网页 / 博客 / Typora` → 关脚注（链接保持可点）

- 完整带图发布流程 + HTML 渲染 + 飞书发链接范本见 `references/md-to-html-publish-flow.md`。
- 飞书表写入踩坑（lark-cli POST/PUT 截断、字段类型、重复记录防御）见 `references/lark-cli-feishu-table-traps.md`。
- Image generation providers 架构 + 第三方 codex-image 插件评估结论（**当前 Codex CLI 不再生成图片，codex-image 项目不可用；用 Hermes 内置 `openai-codex` provider**）见 `references/image-gen-providers.md`。
- 同一项目「重新发布」工作流 + OSS 资源版本化 + 封面配色区分见 `references/republish-same-project.md`（2026-06-23 swiftui-agent-skill 重新发布实测）。

## AIGC 内容合规红线（2026-06-09 微信官方治理公告）

微信公众号平台明确打击「低创作度内容」，以下行为会导致降权/限流：

| 违规类型 | 具体表现 | 合规做法 |
|---------|---------|---------|
| AIGC 原文照搬 | AI 生成后不做修改直接发布 | 必须人工编辑，融入个人观点和经验 |
| 同质化内容 | 短期内主题/标题/封面高度相似 | 每篇差异化标题、封面、切入角度 |
| 洗稿/搬运 | 大篇幅复述站内外内容 | 引用必须标注来源，且需有增量分析 |
| 低信息量 | 简单拼凑、图文无关、存疑数据 | 每个观点有依据，数据标注出处 |

**核心原则：「增量信息」是合规的关键区分。**
- ✅ AI 辅助创作 + 个人实操经验 + 独到观点 = 合规
- ❌ AI 生成原文照搬、批量低成本产出 = 违规

**执行要求：**
1. 每篇文章必须包含至少 1 个个人真实案例或实操经验
2. AI 生成的初稿必须经过人工编辑——调整语气、补充细节、加入个人观点
3. 技术文章要包含「我在实际项目中的做法」或「踩过的坑」
4. 不要连续多篇使用相同的结构模板，适当变化切入方式
5. 引用研究/数据必须标注来源，不使用存疑数据

## Article quality checklist

Before sending, verify:

- [ ] Frontmatter is valid YAML; series_number is correct
- [ ] Body first line is NOT a title
- [ ] No `---` horizontal rules inside body
- [ ] Disabled words: 0 hits for 首先 / 其次 / 最后 / 值得注意的是 / 总的来说 / 在当今 / 赋能 / 总而言之 / 综上所述 / 随着
- [ ] Chinese char count 3000-4000 (acceptable 2500-4500)
- [ ] At least 2 wikilinks to other compiled concepts in the wiki
- [ ] Personal anecdotes / specific examples (not abstract statements)
- [ ] Series callback: ends with `**前 N-1 篇:**` list and the unifying mantra
- [ ] 3 candidate titles in `alt_titles`

## X/Twitter Article capture → 公众号 pipeline

When the user asks to "收入这篇X/技术文章并发布到公众号", the workflow has two phases: **capture** then **publish**.

完整 capture 子流程（含 Twitter Article draft.js blocks 抽取 + 用户抓取偏好 + DeepSeek prompt 模板）见 `tech-content-writer/references/x-twitter-capture.md`。本节只列快速命令。

### Capture phase

**统一抓取脚本**（推荐所有来源类型）：
```bash
python3 ~/.hermes/skills/creative/tech-content-writer/scripts/capture.py "<URL>" --topic <topic>
# 输出：/tmp/capture_<slug>/raw.json + content.md + images.yaml + images/
# 自动处理：推文/Article/博客 URL → 内容提取 → 图片下载 → OSS 上传
```
脚本自动判断 URL 类型（tweet / Article / blog），提取内容 + 下载图片 + 上传 OSS + 生成 `images.yaml` 映射表。写文章时直接引用 `images.yaml` 中的 OSS URL 嵌入 `![描述](oss_url)`。

**⚠️ 用户明确要求（2026-07-11 确认）：抓取内容时必须同步抓取原文图片，写文章时尽可能嵌入原图。** 这是标准流程，不是可选项。当源文章含图时（截图、UI 示例、架构图等），必须：下载图片上传 OSS + 在文章中用 `![描述](oss_url)` 嵌入对应位置。纯文字文章（无正文配图，只有 YouTube 缩略图或跟踪像素）可以在摘要中说明「原文无正文配图」，但大多数推文/Article 都有配图。

1. **Extract tweet ID** from the URL (last path segment before query params).
2. **Fetch via fxtwitter API** (no auth needed, returns full tweet text):
   ```bash
   curl -sL "https://api.fxtwitter.com/{handle}/status/{tweet_id}" | python3 -c "
   import sys, json
   data = json.load(sys.stdin)
   if 'tweet' in data:
       t = data['tweet']
       print(f'Author: {t.get(\"author\",{}).get(\"name\",\"\")} @{t.get(\"author\",{}).get(\"screen_name\",\"\")}')
       print(f'Date: {t.get(\"created_at\",\"\")}')
       print(f'Likes: {t.get(\"likes\",0)}  RTs: {t.get(\"retweets\",0)}')
       print('---')
       print(t.get('text',''))
   else:
       print(json.dumps(data, indent=2))
   "
   ```
3. **Handle Twitter Articles** (long-form posts): `tweet.article.content.blocks[]` has `type` field — `header-two` → `## `, `header-three` → `### `, `unstyled` → plain paragraph. Iterate blocks, map types to markdown, join with `\n\n`.

   **⚠️ Article 内插图提取（2026-07-11 实测关键发现）**：Article 的图片 URL **不在** `blocks[]` 的 atomic entity 里（atomic 只有 `mediaId` 引用），**在** `tweet.article.media_entities[]` 数组里：
   ```python
   art = data['tweet']['article']
   cover_url = art['cover_media']['media_info']['original_img_url']  # 封面
   for me in art['media_entities']:  # 正文插图（8-20 张常见）
       url = me['media_info']['original_img_url']
       # curl 拉原始尺寸：url + '?name=orig'
   ```
   `entityMap` 是一个 **list**（不是 dict），每个 `type=MEDIA` 的 entity 有 `mediaItems[].mediaId`，但没有 URL。必须从 `media_entities[]` 拿 URL。
4. **Handle regular tweets**: `tweet.text` is the content; usually short enough to use directly. If thread exists, `tweet.thread` array has all tweets in order.
5. **Enrich with web research**: Search for the original paper/source behind the tweet. Use `web_search` + `web_extract` on arXiv papers, blog posts, or official docs. The tweet is a summary — the article needs depth from primary sources.
6. **Save raw source** to `TechnologyHub/raw/` with `capture_method: fxtwitter` and the original X URL.

### Write phase

Translate/adapt the English content into a Chinese tech article following the standard article quality checklist. Key adjustments:
- Tone: practical, direct, no filler words (check disabled word list)
- Structure: keep the original's logical flow but reorganize for Chinese readers
- Add series context if applicable (series name, number, unifying mantra)
- 2200-2500 Chinese characters sweet spot for tweet adaptations

**⚠️ English→Chinese adaptation pitfall:** The "不是X，而是Y" banned phrase is an almost automatic translation of English contrast structures ("not X, but Y", "X is not about Y, it's about Z"). Expect 5-7 instances in a 2500-char adapted article. Run the banned word scan IMMEDIATELY after drafting the first pass — do not wait until the full article is done. Fix all instances before expanding word count.

### Publish phase

Follow the standard step-by-step flow (cover image → 飞书 send → verify). For the 飞书 segment splitting, use a Python helper script (see `references/publish_wechat_volXX.py` pattern):

```python
# Split body by \n\n boundaries, max ~880 chars/segment (safety margin under 900)
# Send title as --text, body segments as --markdown
# Target chat from bots.yaml routing table
```

### Pitfalls specific to X capture

1. **Twitter Articles vs regular tweets**: Articles use `tweet.article.content.blocks[]` (draft.js format), regular tweets use `tweet.text`. Check for `tweet.article` existence first.
2. **fxtwitter truncation**: For very long articles (15k+ chars), the API may truncate. If blocks count seems low, try fetching twice or use Jina reader as fallback.
3. **Cover image from tweet**: `tweet.article.cover_media.media_info.original_img_url` gives the article's cover — useful as reference but don't use it directly as the 公众号 cover (design your own).
3a. **❗ fxtwitter entityMap 不是 dict，是 list（2026-07-11 实测）**：`article.content.entityMap` 返回的是 `list` 类型（每个元素有 `key`/`value` 字段），直接 `.keys()` 会报 `AttributeError`。更关键的是：entityMap 里的 `type=MEDIA` entity 只有 `mediaItems[].mediaId`（数字 ID），**没有图片 URL**。要拿图片 URL 必须从 `article.media_entities[]` 数组取（每项有 `media_info.original_img_url`）。不要在 entityMap 里浪费时间找 URL。
5. **Initial draft will be short**: Tweet content is ~300-800 English words. Chinese adaptation typically lands at 1500-2000 chars — well below the 2500 minimum. Plan for a substantial expansion phase: add analysis, examples, context from the research you gathered in the capture phase.
5b. **本会话实测（2026-06-18）：lark-cli `--markdown` 模式可正确渲染 50-80 字符内的短段 + 自动 wrap 成 post 格式**：当文章 body 切到 10 段、每段 480-870 字符时，lark-cli 1.0.16 把每条 `--markdown` 消息成功渲染为 post 类型。验证方法：发送后立即 `lark-cli im +chat-messages-list --chat-id <id> --format pretty`，看 type 列全是 `post`（不是 `text`）。如果 type 出现 `text`，说明 markdown 没被正确 wrap，检查 message 长度（>4096 字符可能触发降级）。
5c. **公众号文章系列 Vol 编号硬要求（2026-06-18 实测）**：本会话发布的是 "WWDC26 技术解读 Vol.01"。**首篇必须用 Vol.01 而不是省略编号**，让助理能识别这是系列开端。Title 段格式：`【系列名 Vol.0X】\n<文章标题>`。资源区或正文末尾必须预告下一篇主题，让读者知道系列规划。
6. **fxtwitter truncation**: For very long articles (15k+ chars), the API may truncate. If blocks count seems low, try fetching twice or use Jina reader as fallback.

## Common pitfalls

00. **`render_cover.py` 需要 OSS 环境变量（2026-07-16 实测）**：`render_cover.py` 脚本要求 `OSS_AK` 和 `OSS_SK` 环境变量，否则会报 `ValueError: 请设置环境变量 OSS_AK 和 OSS_SK`。**更简单的方案**：直接用 Playwright 渲染封面 HTML 为 PNG，然后手动上传到 OSS（见 Option B）。这样不需要配置环境变量，代码更简洁。示例：
   ```python
   from playwright.sync_api import sync_playwright
   import os
   
   html_path = os.path.abspath("/tmp/cover.html")
   url = f"file://{html_path}"
   
   with sync_playwright() as p:
       browser = p.chromium.launch()
       page = browser.new_page(viewport={"width": 1200, "height": 540}, device_scale_factor=2)
       page.goto(url, wait_until="networkidle")
       page.wait_for_timeout(2000)
       page.screenshot(path="/tmp/cover.png", type="png")
       browser.close()
   ```
   然后用 HTTP PUT + V1 签名上传到 OSS（见 aliyun-oss-upload skill）。

0. **❗ lark-cli TLS handshake timeout through proxy（2026-07-14 实测）**：当 `HTTPS_PROXY=http://127.0.0.1:7897` 设置但代理不稳定时，lark-cli 请求飞书 API 会报 `TLS handshake timeout`。**修复**：加 `LARK_CLI_NO_PROXY=1` 环境变量绕过代理直连：
   ```bash
   LARK_CLI_NO_PROXY=1 lark-cli im +messages-send --chat-id oc_xxx ...
   ```
   适用于所有 lark-cli 命令（im/base/api）。当代理正常工作时不需要这个变量；只在 TLS timeout 时加。

00. **oss2 SDK cffi 版本冲突（2026-07-12 实测）**：在 hermes-agent 环境中，oss2 SDK 导入会报 cffi 版本冲突（venv 的 cffi 2.0.0 vs miniconda3 的 cffi 1.17.1）。**修复**：用 `sys.path` 过滤掉 hermes-agent venv 路径：
   ```python
   import sys
   sys.path = [p for p in sys.path if 'hermes-agent/venv' not in p]
   import oss2
   ```
   必须在 `import oss2` **之前**执行。或者用 HTTP PUT + V1 签名方案（见下方）。

0a. **lark-cli flag is `--chat-id`, NOT `--chat`.** The `+messages-send` command uses `--chat-id` (with a hyphen). Using `--chat` will fail with "unknown flag: --chat". **The full command syntax is `lark-cli im +messages-send`** (NOT `lark-cli +im +messages-send` — that fails with "unknown command \"+im\""). Always use:
   ```bash
   lark-cli im +messages-send --chat-id oc_xxx --as user --markdown "content"
   ```
   2026-06-14 实测踩坑：`+im` 报 `unknown command`，改用 `im` 立即成功。
0a. **❗ lark-cli JSON 响应检查要用 `json.loads()`，不要字符串匹配 `"ok":true`（2026-07-11 实测）**：lark-cli 输出的 JSON 中 `"ok": true` 有空格，用 `'"ok":true'` 匹配永远不中，导致成功的消息被误判为失败。正确做法：
   ```python
   import json
   # 先 strip lark-cli 的 warning 前缀
   stdout = re.sub(r'^\[lark-cli\].*?\n', '', result.stdout, flags=re.MULTILINE)
   resp = json.loads(stdout)
   if resp.get('ok'):
       mid = resp['data']['message_id']
   ```
   或至少用 `'"ok": true'`（含空格）匹配。如果用字符串匹配，segments 全部显示为 "failed" 但实际已发送成功。
1. **Don't try to send the cover image via 飞书.** Will fail with `im:resource:upload` permission error. Upload to OSS only.
2. **Don't include a `---` separator inside the body.** 飞书 renders it as a horizontal rule and breaks post formatting.
3. **Segment by paragraph, not by character count.** Markdown segmenter should split at `\n\n` boundaries; max 900 chars/segment to leave safety margin.
4. **Don't write the article body in the wrong CWD path.** Use absolute paths to `outputs/<vol>-*.md`; never to `/tmp/`.
5. **Don't send the title inside the body.** 公众号 title comes through the post request — the 助理 will see it from the title message you sent first.
6. **Don't assume the previous publish succeeded.** Always verify via `+chat-messages-list` after sending. The user blocked Vol.07 — don't assume future articles are auto-approved.
7. **Don't read the cover image from `/tmp/...` with lark-cli --image.** It requires CWD-relative path AND the auth privilege. Just upload to OSS and let 助理 pull it.
8. **Don't re-POST to "confirm" a record creation.** If your `lark-cli api POST .../records` returned `code:0` but you can't see `record_id` in the truncated stdout, **don't POST again** — that creates duplicate records. Always use `json.loads(r.stdout)` to parse the full JSON and extract `data['data']['record']['record_id']` in the same step. (2026-06-06 Shann 实测:3 条重复 + bot-identity 清理。)
9. **PUT success ≠ all fields written.** After `lark-cli api PUT .../records/{id}`, don't trust `code:0` alone — parse the response and verify `data['data']['record']['fields'].keys()` includes every field you intended to update.
10. **`--as user` can't GET list, `--as bot` can.** When cleaning up duplicates or listing records (e.g. for QA), use `--as bot` — user identity lacks `bitable:app:readonly` (99991679). Bot identity has full table permissions.
11. **HTML cover template 2 latent bugs (fixed in 2026-06-06 Vol.10).** `templates/cover-agent-engineering-series.html` (in `content-collector` skill) had: (a) code-card right:60px + width:320px overlapping the title's last character on long titles; (b) `<span class="kw">N.</span>` prefix duplicating with user-supplied `CSNIPPET_LINE_N` that already had "1. xxx" text → rendered as "1. 1. xxx". Both fixed. When reusing the template, supply `CSNIPPET_LINE_N` **without** numeric prefix and **always** visually verify with `browser_vision` after rendering.
12. **❗ 公众号封面比例错 (2026-06-14 实测)**: 公众号**官方要求 20:9 横向** (1200×540)，不是 9:16 竖版。生成封面时显式用 `--ratio 20x9`（`wechat-cover-image` skill 已支持）。如果传错了竖版图：(1) 重新生成横向图，(2) 覆盖上传到 OSS 同一 key，(3) 在飞书发一条修正提示让用户刷新。
13. **❗ DeepSeek 返回的图片占位不是标准 markdown (2026-06-18 v_pradeilles 实测)**: DeepSeek 偶尔会返回 `![alt 文本描述](无 URL)` 这种"无 URL 的伪图片语法"（alt 文本是一段描述而不是图片名），按 `re.findall(r'!\[[^\]]*\]\([^)]+\)', body)` 数图数会漏。**修正**：扫描时改成更宽松的正则 `r'!\[[^\]]*\]'`，看到任何 `![]` 都当成图片占位处理；或者在 prompt 里强制要求"图片必须用 ![alt text](https://...) 完整语法，不能用空括号"。
14. **❗ image_gen 段 YAML 重复 (2026-06-23 codex-image 评估实测)**: `~/.hermes/config.yaml` 是 Hermes 全部配置的单文件，向其追加 `image_gen:` 段时**必须**先 `if "image_gen:" in text` 检查；重复 key 取最后一个值，调试时极易迷惑。
15. **❗ codex-image (Leon-llb) 第三方 provider 在当前 Codex CLI (≥ 0.141) 上不工作 (2026-06-23 实测)**: 它的 `generate.py` 用 `codex exec` 生成图片，但 Codex CLI 0.141+ 已经是纯代码 agent，没有图片生成工具——`codex exec` 退出 0 但 `~/.codex/generated_images/` 无新图，diff 算法抛 `No new image found`。**用 Hermes 内置 `openai-codex` provider 代替**（走 Codex Responses API + `image_generation` 工具，不依赖 CLI）。详见 `references/image-gen-providers.md`。
16. **❗ openai-codex 内置 provider 在当前 Codex Responses API 上也不工作 (2026-06-23 实测，2026-06-26 再次确认)**: 切到 `provider: openai-codex` 后请求成功发到 `https://chatgpt.com/backend-api/codex/responses`，但后端返回 `HTTP 400: Tool choice 'image_generation' not found in 'tools' parameter`——plugin 的 `tool_choice.allowed_tools.tools[]` 子结构跟当前后端协议不兼容。**结论 (2026-06-26 二次确认)：本 Hermes 环境下，所有走 ChatGPT Plus 的图片生成路径都不可用**。封面图必须回退到 (A) HTML + Chrome headless 渲染（首选，稳定可靠）或 (B) 付费 provider（`fal` / `openai` / `xai`）。详见 `references/image-gen-providers.md` 末尾的 2026-06-23 caveat。
16a. **❗ baoyu-visual-content skill 的 image_generate 也会失败 (2026-06-26 实测)**：加载 `baoyu-visual-content` skill 后按其 workflow 生成封面图，`image_generate` 同样返回 `Tool choice 'image_generation' not found` 错误。**fallback 路径**：用 HTML + Chrome headless（`--headless=new --screenshot`）生成。实测 notion 风格流程图 HTML 模板在 1200×675 尺寸下效果好于之前的手工 dark-gradient 模板——文字更清晰、布局更结构化。**baoyu skill 的价值在于分析和 prompt 记录**（outline.md + prompts/ 目录），即使 image_generate 不可用，prompt 文件仍可复用于 HTML 模板的文案。
17. **❗ 重新发布同一项目的文章要明确标注版本（2026-06-23 swiftui-agent-skill 重新发布实测）**：当用户说「重新发布」/「再发一遍」同一主题（例如之前发过 swiftui-agent-skill 这篇，现在又有 v4.0.0 新版要发），要：(1) **标题加版本号或时间戳** 区分（例：`《给 AI 装一个 SwiftUI 专家大脑：3.1k Stars 的 Agent Skill v4.0 实测》`），避免读者看到重复标题误以为没新内容；(2) **OSS 资源 key 加版本后缀**（例：`wechat/swiftui-agent-skill-v4-20260623.png`），不覆盖旧版；(3) **封面图配色或布局换风格**（同主题项目重新发布时换主色调），让两期封面一眼能区分；(4) **正文里加一句「重新发布」说明** 在资源段，让助理识别这是新版而非重复。
17a. **❗ 「重新通知 AICoder 发布」≠ 重新写文章（2026-06-25 实测踩坑）**：用户说「这篇文章重新通知 AICoder 内容助手去发布」时，**首先确认是 a) 复用现有文章 还是 b) 真的重写**。在 `TechnologyHub/outputs/` 或 `TechnologyHub/raw/articles/` 搜同主题 → 找到了 → 询问/判断用户意图（「是复用旧文章只重新发飞书？还是用新版本内容重发？」）。**不要默认 = 重写整篇**——这会消耗 5-10 分钟重写一篇用户可能只需要「通知助理重新跑流程」的文章。**正确路径**：先 grep 同主题 → 如果已有：列出旧标题和 OSS key 让用户确认意图；如果没有：按用户意图走「写 → 发」标准流程。
18x. **❗ 探索型 vs 教程型文章结构区分（2026-06-23 lldb-mcp 实测）**：当用户说「探索这篇文章提到的内容并写一篇技术博客」时（如从一条推文出发，写一篇关于 LLDB MCP 的科普/解读文章），这不是 `tech-content-writer` 模板 A 的「工具介绍」型，也不是模板 B 的「踩坑记录」型，而是**探索型**：开头不能直接给「这是什么」的硬定义，应该先讲故事背景（推文作者、附图、原帖反应），再切入主体。模板：A 推文故事 + 用户痛点 → B 官方文档关键章节解读 → C 实操配置步骤 → D 跟之前方案的对比 → E 工程意义延伸。每个章节独立 `### h3` 标题。**判别方法**：源材料是单一信息源（一条推文 / 一篇官方文档 / 一个项目 README），不是具体报错也不是工具对比——就是探索型。**避免**：按模板 A 的「Hook → 最小示例 → 核心概念 → 实战 → 总结」硬套，会丢失探索型文章的「先讲故事再展开」的节奏。
18. **❗ 标题换了 → 封面必须同步更新（2026-07-13 用户纠正）**：用户确定新标题后，不要只更新飞书消息里的标题文字——必须重新渲染封面 HTML（更新标题文本）→ 上传新封面到 OSS → 重新发飞书消息（包含新封面 URL）。用户说"标题换了"时，默认包含"封面也要换"。不要等用户提醒"封面也更新一下"。

19. **❗ `render_cover.py` 需要 `OSS_AK` / `OSS_SK` 环境变量（2026-07-16 实测）**：直接调用 `render_cover.py` 时，如果没设 `OSS_AK` / `OSS_SK`，脚本会报 `ValueError: 请设置环境变量 OSS_AK 和 OSS_SK`。**两种修复**：
   - (a) 设环境变量后调用：`env={"OSS_AK": "...", "OSS_SK": "...", **os.environ}`
   - (b) **跳过 render_cover.py，直接用 Playwright 渲染 + 手动 OSS 上传**（更简单，不依赖脚本）：
     ```python
     from playwright.sync_api import sync_playwright
     html_path = os.path.abspath("/tmp/cover.html")
     with sync_playwright() as p:
         browser = p.chromium.launch()
         page = browser.new_page(viewport={"width": 1200, "height": 540}, device_scale_factor=2)
         page.goto(f"file://{html_path}", wait_until="networkidle")
         page.wait_for_timeout(2000)
         page.screenshot(path="/tmp/cover.png", type="png")
         browser.close()
     # 然后用 HTTP PUT + V1 签名上传到 OSS
     ```
   推荐方案 (b)，少一层依赖。

20. **❗ 封面必须用 `wechat-cover-html` skill 模板，禁止手写 HTML（2026-07-11 用户纠偏）**：用户原话「你的封面有点丑」。根因：绕过了 `wechat-cover-html` skill，自己手写了一个简陋的 dark-gradient HTML。**正确做法**：
   - **始终**用 `wechat-cover-html` skill 的模板（`code-card-purple.html` / `code-card-blue.html` 等），不要自己写封面 HTML
   - 模板已有 6 套配色 + 代码卡片 + feature chips + 版本号 + 作者行，视觉层次完整
   - 用 `render_cover.py --upload` 一条龙（渲染 + OSS + 飞书），不要手动分步
   - 判断标准：如果文章涉及代码/架构/AI工具 → 必须用 `code-card-*` 模板，不能用纯文字 dark-gradient
   - 实测：手写 dark-gradient 封面 vs `code-card-purple` 模板，用户满意度差距巨大

20. **❗ Python 字符串中的中文引号转义（2026-07-13 实测）**：当文章标题包含中文引号（`"` `"` 或 `'` `'`）时，在 execute_code 中构建 Python 字符串会触发 `SyntaxError`。例如：
   ```python
   # ❌ 错误：中文引号在双引号字符串内
   title = "431 Stars：这个 Skill 专治 AI 写测试的"坏毛病""
   # SyntaxError: invalid syntax
   
   # ✅ 正确：用单引号包裹，或转义
   title = '431 Stars：这个 Skill 专治 AI 写测试的"坏毛病"'
   # 或用 Unicode 转义
   title = '431 Stars：这个 Skill 专治 AI 写测试的\u201c坏毛病\u201d'
   ```
   **规则**：当标题/摘要可能包含中文引号时，Python 字符串统一用单引号包裹，或在 write_file 阶段就避免在标题中使用中文引号（改用英文引号或去掉）。

18b. **❗ 抓取文章插图必须嵌入正文，不能只上传 OSS（2026-07-11 用户纠偏）**：用户原话「你抓取到的一些图片，没有应用到这个我们新生成的文章的内容中」。根因：图片下载上传到 OSS 后，文章里只在末尾笼统提了一句「原文插图 8 张」，没有在对应章节嵌入。**正确做法**：
   - **先用 `vision_analyze` 逐张分析图片内容**，确定每张图对应文章的哪个章节
   - **在文章对应章节嵌入** `![描述性 alt](oss_url)` — alt 文字要描述图片内容，不能是「图片 1」「img_01」
   - **图片嵌入位置要有上下文**：图片前后各有一段文字解释这张图展示什么、为什么放在这里
   - **封面图（cover）可以放在文末做收束**，正文插图必须在对应章节内
   - 判断标准：如果源文章含 3+ 张图，每张图都应该在新文章中有对应位置，不能「批量上传后一笔带过」

18c. **❗ 封面美观度要求提升（2026-07-03 用户反馈）**：用户原话「最近你生成公众号封面的美观能力有点下降」。根因：对复杂技术主题仍用 T1-T5 的纯文本+装饰元素布局，信息密度不够、视觉层次单一。**正确做法**：
   - **技术流程/架构/检测逻辑/对比矩阵类文章** → 用 T6 (Split+SVG)，右侧放信息卡或流程图
   - **信息卡设计**：暗色背景 + 半透明卡片 + 编号步骤 + 关键术语高亮 + 大数字水印
   - **标题区域**：用渐变文字（`background: linear-gradient(...); -webkit-background-clip: text`）而非纯白
   - **视觉层次**：至少 3 层（背景网格 + 发光球体 + 前景内容），不要只用纯色+文字
   - **判断标准**：如果文章内容涉及「N 步流程」「N 层架构」「检测机制」「对比矩阵」，**必须**用 T6，不要用 T1-T5
   
   实测案例：Claude Code 防封号封面，T6 布局 + 右侧三层检测流程卡 + 橙红渐变标题，用户满意。
18a. **❗ 「探索 thread 内容」的含义 = 推文本身 + 一手资料（2026-06-25 corentinanjuna tweet 实测）**：用户说「根据推文中 thread 的内容整理」时，**不要执着去找不存在的 thread 回复**。X 的 thread 在无登录 + browser JS 渲染下基本抓不到 9 条 reply。**正确路径**：(1) 先用 `fxtwitter` 拿推文 `text`（含超链接和图片）(2) 如果作者预告要 thread（`🧵` 符号），但 `tweet.thread` 字段为空——直接用原推文本 + 配图展开，不要再去绕找回复 (3) **图片里的内容（OCR）= 一手数据**：本会话实测 corentinanjuna 推文单图包含完整 build 输出（`[2,701 / 2,703] ... Elapsed time: 59.709s`），这本身就是发布素材的核心 (4) 用 `vision_analyze` 提取图片里所有可见数字/命令/配置 (5) 作者的推文文本往往是「实验报告骨架」，图片是「实验数据」——组合起来才是完整信息源。

## 跨文章去重检查（同一项目被反复要求发布时必走）

发布前先 `ls TechnologyHub/outputs/` + `search_files content: <项目名> path: TechnologyHub/raw/articles`，确认本次是不是同一个项目/主题的二次发布。如果是：

1. **找出上次发布的标题、日期、OSS key、cover 路径**（读 log.md 或 Obsidian raw 目录）
2. **本次标题/封面/资源 key 全部做版本区分**（见 pitfall #17）
3. **正文末尾加版本对比段**：简述「v1 写了 X，v2 新增 Y」让读者知道增量
4. **不要简单重发旧文章**——AIGC 合规和公众号降权都禁止同质化内容

- Full lark-cli + 飞书表 operational cheat sheet (4 步对照清单 + 9 个失败案例 + 验证脚本) is in `references/lark-cli-feishu-table-traps.md`.
- End-to-end publish script template (Playwright cover → OSS → Feishu post + chunked body) at `references/publish-script-template.md` — copy the script to `/tmp/publish_<slug>.py`, edit the CONFIG block (6 lines), run with `/Users/nowcoder/miniconda3/bin/python3`.
- **Verified `execute_code` one-shot pattern** (2026-07-13): complete publish flow in a single Python block (cover render → OSS upload × 2 → Feishu send → table record) at `references/publish-execute-code-pattern.md`. Use when you want to avoid multi-step terminal calls and have all artifacts ready at `/tmp/`.

## Verification checklist

- [ ] `index.md` updated (Outputs section + Total pages count)
- [ ] `log.md` appended with publish entry
- [ ] Cover image on OSS, URL publicly readable (HEAD 200)
- [ ] 飞书 chat shows the title (text) + N body segments (post format)
- [ ] All 飞书 message_ids recorded in log
- [ ] No broken image (no 飞书 message containing the OSS URL that will fail to render)
- [ ] Disabled-word check: 0 hits
- [ ] Chinese char count: in range
- [ ] Series callback present and consistent with prior articles
- [ ] If using `image_generate` tool: `image_gen.provider` in config.yaml is set and the provider is verified available. **2026-06-23 caveat**: both `codex-image` and `openai-codex` are currently broken (see pitfall #15-#16). Before publishing, run a one-image smoke test for the chosen provider, or fall back to Playwright HTML cover (step 2 option A).
