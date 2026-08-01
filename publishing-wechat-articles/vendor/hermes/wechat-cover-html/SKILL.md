---
name: wechat-cover-html
description: "Use when generating a 公众号 (WeChat) 20:9 cover image for CODE-DENSE technical articles (iOS / Swift / AI tooling / CLI tools). HTML + Playwright pipeline renders sharp code snippets in the cover (real Swift/JS/Python syntax with JetBrains Mono font), unlike Pillow which can only render simple text. Outputs 1200x540 (2x retina) PNG. Triggers: 代码密集型封面, code snippet cover, 20:9 1200x540, swiftui cover, bazel cover, iOS article cover with code. This skill replaces ~30 lines of inline Playwright + OSS upload + 飞书 post code that was being repeated in every 2026-06-23 session — call it instead."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [wechat, cover, image, playwright, html, code, publishing, tech-article]
    related_skills:
      - tech-content-writer
      - wechat-cover-image
      - aliyun-oss-upload
      - tech-wechat-publish
---

# 公众号封面图：Playwright + HTML 模板（代码密集型）

## Overview

当公众号文章需要**在封面里展示真实代码片段**（Swift / SwiftUI / Python / JS / Bash 终端输出），纯 Pillow 方案画不出等宽代码字体的视觉冲击力。这个 skill 用 **HTML + Playwright 截图**路线——把代码块当作一等公民渲染，输出 1200x540 PNG（2x retina）。

适用场景：
- iOS / SwiftUI / Swift 6 新特性介绍（封面要展示 `@Observable` / `AsyncImage(request:)` 等真实代码）
- AI 工具教程（封面要展示 Claude Code / Codex / Cursor 命令）
- CI/CD / Bazel / 构建系统（封面要展示终端输出）
- 任何代码块是文章核心卖点的技术文

不适用：纯文字标题的文章（用 `wechat-cover-image` Pillow 方案更轻量）

## When to Use

触发词：
- 「给这篇文章生成代码风格的封面」
- 「封面要展示真实代码」
- 「Playwright 渲染封面」
- 「代码密集型 20:9 封面」

依赖：
- Playwright Python：`pip install playwright && playwright install chromium`
- macOS 默认 `python3`（`/Users/nowcoder/miniconda3/bin/python3`）通常已装

## 模板结构

每个封面 HTML 包含 5 个固定区域：

| 区域 | 位置 | 内容 |
|---|---|---|
| 顶部 tag | 左上角 | 分类标签（如「SwiftUI · iOS 27」） |
| 版本号 | tag 下方 | 型号 / 版本 / Stars 标识 |
| 主标题 | 中央偏左 | 2 行，每行 30-36px |
| 副标题 | 主标题下方 | 1-2 行说明 |
| 特性 chips | 副标题下方 | 4-6 个小标签 |
| 作者 | 底部 | 来源 + 标签 |
| 右侧代码卡片 | 右侧 | macOS 红黄绿圆点 + 等宽代码块 |

## 配色按主题选**（已验证的 6 套）

| 主题 | 模板 | 主色 |
|---|---|---|
| iOS 27 / SwiftUI / 编译器版本 | `code-card-blue.html` | 蓝-青 `#5e9fff → #5ed4ff` |
| AI 工具 / Agent Skills / Claude / Cursor | `code-card-purple.html` | 紫-靛 `#a78bfa → #6366f1` |
| CI/CD / Bazel / 远程构建 / Linux 工具链 | `code-card-orange.html` | 橙-红 `#fb923c → #f43f5e` |
| LLDB / 终端 / DevTools / 调试器 | `code-card-green.html` | 绿 `#4ade80 → #22c55e` |
| 前端 / UI 设计 / Tailwind / 设计系统 | `code-card-cyan.html` | 青 `#2dd4bf → #5eead4` |
| 纯观点 / 周报 / 综述（无代码） | `text-only-blue.html` | 蓝-青（大字号） |

完整调色板说明和模板结构见 `templates/README.md`

## Quick Start

```bash
# 1. 复制最接近的模板（按主题选配色）
cp ~/.hermes/skills/creative/wechat-cover-html/templates/code-card-blue.html /tmp/cover.html

# 2. 编辑 5 个区域：tag / version / title / subtitle / code-card

# 3. 渲染 + 上传 + 发飞书（一行命令）
/Users/nowcoder/miniconda3/bin/python3 ~/.hermes/skills/creative/wechat-cover-html/scripts/render_cover.py \
  --html /tmp/cover.html \
  --output /tmp/cover.png \
  --upload --slug my-article-20260625 \
  --feishu-chat-id oc_cde2971ca05c08d8b36f4a3f86a6544a \
  --title "..." --summary "..."
```

**flags**:
- `--html` — 输入 HTML 路径
- `--output` — PNG 输出路径
- `--width / --height` — viewport 尺寸（默认 1200x540）
- `--scale` — device_scale_factor（默认 2，输出 2x retina）
- `--upload` — 启用 OSS 上传，得到公网 URL
- `--slug` — OSS object key 用的 slug
- `--feishu-chat-id` — 启用后自动发飞书 post 消息（标题+摘要+封面 URL）
- `--title` / `--summary` — 飞书 post 消息用

## HTML 模板关键技巧

### 1. 字体加载用 Google Fonts CDN
```html
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
</style>
```
- `Noto Sans SC`：中文（替代 PingFang SC）
- `JetBrains Mono`：代码字体（替代 SF Mono）
- `&display=swap` 防止 FOIT（Flash of Invisible Text）

### 2. 关键等待参数
```python
page.goto(url, wait_until='networkidle')  # 等所有网络资源加载完
page.wait_for_timeout(2000)                # 多等 2 秒让字体稳定
```
`networkidle` 不一定等得到 Google Fonts CDN 跨域加载完成，必须额外 sleep。

### 3. 避免 emoji 渲染失败
HTML 里不要用 emoji（如 🚀 ✨ 🎉）。Playwright 渲染时部分 emoji 会变豆腐方块。用 `★` `·` `→` `◆` 等 Unicode 符号替代。

### 4. 代码卡片视觉标准
```html
<div class="code-header">
  <div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
  <div class="code-title">filename.swift</div>
  <div class="badge-new">NEW</div>
</div>
```
- 红黄绿圆点（macOS 窗口）必带
- code-title 用等宽字体小字号
- badge（NEW/HOT/KILLER）放最右，可选

### 5. 字号 / 间距黄金比
- 主标题：34-38px
- 副标题：15-16px
- chip：12-13px
- 代码：12-13px
- 作者署名：12px
- padding：45-55px 四边

## scripts/render_cover.py 接口

```python
def render(html_path, output_path, width=1200, height=540, scale=2) -> str:
    """HTML → PNG. Returns absolute output path."""

def upload_to_oss(png_path, slug) -> str:
    """Upload to kaelblog bucket, return public URL."""

def send_feishu_post(chat_id, title, summary, cover_url) -> bool:
    """Send post message with cover URL to Feishu chat."""
```

### OSS 上传：curl + V1 签名（首选）

当 `oss2` SDK 未安装时，用 curl + V1 签名上传：

```python
import hashlib, hmac, base64, time, subprocess

bucket = "kaelblog"
endpoint = "oss-cn-beijing.aliyuncs.com"
ak = "__MIGRATED_TO_RUNTIME_LOCAL__"
sk = "__MIGRATED_TO_RUNTIME_LOCAL__"
object_key = "covers/my-article-20260714.png"

date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
content_type = "image/png"
string_to_sign = f"PUT\n\n{content_type}\n{date}\n/{bucket}/{object_key}"
signature = base64.b64encode(
    hmac.new(sk.encode(), string_to_sign.encode(), hashlib.sha1).digest()
).decode()

url = f"https://{bucket}.{endpoint}/{object_key}"
auth = f"OSS {ak}:{signature}"

cmd = [
    'curl', '-s', '-X', 'PUT',
    '-H', f'Date: {date}',
    '-H', f'Content-Type: {content_type}',
    '-H', f'Authorization: {auth}',
    '--data-binary', '@/tmp/cover.png',
    url
]

result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0 and 'Error' not in result.stdout:
    print(f"✓ 上传成功: {url}")
```

**关键点**：
- `date` 必须用 GMT 格式（`%a, %d %b %Y %H:%M:%S GMT`）
- `string_to_sign` 格式：`PUT\n\n{content_type}\n{date}\n/{bucket}/{object_key}`
- `--data-binary` 保留二进制数据（不要用 `--data`，会丢字节）
- 上传后 URL 格式：`https://{bucket}.{endpoint}/{object_key}`

## ⚠️ 强制标准（2026-07-15 用户硬要求）

**所有公众号封面必须用本 skill 的模板生成，禁止手写 HTML。**

用户原话：「以后生成公众号封面的时候，就按现在的这个标准去生成」「别再乱生成了，就用现在的这个最新版本的生成风格和方式去生成」。

**标准流程**：
1. **复制模板**：从 `templates/` 目录选最接近的配色（6 套已验证）
2. **编辑 5 个区域**：tag / version / title / subtitle / features+author（或 code-card）
3. **Playwright 渲染**：viewport 1200x540, device_scale_factor=2, wait_for_timeout(2000)
4. **上传 OSS**：kaelblog bucket, key 格式 `wechat/<slug>-<date>.png`
5. **飞书发链接**：`📎 封面图：<oss_url>`

**禁止行为**：
- ❌ 自己手写 HTML 封面（用户 2026-07-11 已反馈「你的封面有点丑」）
- ❌ 用 `image_generate` 工具（当前环境不可用）
- ❌ 用 Pillow 画代码密集型封面（字体渲染差）
- ❌ 跳过 Playwright 渲染（HTML 直接截图是唯一标准）

**配色选择决策表**（按文章主题选模板）：
| 主题 | 模板 | 配色 |
|------|------|------|
| iOS / SwiftUI / 编译器 | `code-card-blue.html` | 蓝-青 |
| AI 工具 / Agent / Claude / Cursor | `code-card-purple.html` | 紫-靛 |
| CI/CD / Bazel / Linux 工具链 | `code-card-orange.html` | 橙-红 |
| LLDB / 终端 / DevTools | `code-card-green.html` | 绿 |
| 前端 / UI / Tailwind / 设计系统 | `code-card-cyan.html` | 青 |
| 纯观点 / 周报 / 综述 | `text-only-blue.html` | 蓝-青 |

**同主题多版本封面**：v1 / v2 用不同配色模板区分（如 v1 用 purple，v2 用 cyan）。

## Pitfalls

1. **网络不稳导致字体加载失败**：`networkidle` 后必须额外 `wait_for_timeout(2000)`。如果生产环境网络更差，提到 3000-4000ms。
2. **Google Fonts 跨域失败**：`page.goto` 加 `wait_until='networkidle'` 等到所有外部资源完成。如果还是没字体，回退到系统字体（macOS 自带 PingFang/SF Mono）。
3. **HTML 文件用 file:// 协议**：`page.goto(f'file://{abspath}')` 一定要 `os.path.abspath()`，相对路径会 404。
4. **device_scale_factor 不等于 PNG 尺寸**：2x scale 时 `viewport=1200x540` 输出 2400x1080 PNG，但 viewport CSS 逻辑尺寸仍是 1200x540。所有 CSS 像素按 1200x540 写。
5. **OSS bucket 配额**：每次发图前确认 kaelblog bucket 没满（实际单图 200-800KB，10MB 配额够用几百张）。
6. **lark-cli 命令语法**：`lark-cli im +messages-send --chat-id <oc_xxx> --as user --msg-type post --content <json>`，不要加 `+` 前缀到 `im` 子命令。
7. **避免用 `image_generate` 工具的 fallback**：当前 `image_gen.provider=openai-codex` 因 Codex Responses API tool_choice 协议变化返回 HTTP 400。HTML 渲染方案完全绕过这个。
8. **HTML 模板不要存代码块到 `pre` 标签**：用普通 div + 等宽字体样式，否则 Playwright 渲染时 `pre` 内的换行会被意外处理。
9. **feature chip 数量**：6 个以内。超过会换行或挤压。
10. **大字号标题在 macOS Chrome 默认 anti-aliasing 下边缘发虚**：`text-rendering: optimizeLegibility;` 或 `font-weight: 900` 都能缓解。
11. **lark-cli post 消息 JSON 作为 CLI 参数会失败（2026-06-23 实测）**：`lark-cli im +messages-send --msg-type post --content <json>` 当 JSON 内容超过 200-300 字符时，shell 会截断参数导致 `lark-cli` 报 `Usage:` 而不是真正的错误。这不是 lark-cli bug，而是 shell 的 ARG_MAX 限制。**对策**：用 Python `subprocess.run([...], input=json_bytes, text=True)` 通过 stdin 传 JSON，或把 JSON 写到临时文件后用 `cat /tmp/post.json | lark-cli ...`。正文分段发送（`--markdown`）不受影响，因为每段 < 900 字符。

## Verification Checklist

- [ ] 渲染脚本一次跑通，不报 font/network 错误
- [ ] PNG 文件 200-900KB
- [ ] `vision_analyze` 看到：标题完整无截断、代码块语法高亮、配色统一
- [ ] 标题中文用 Noto Sans SC、英文/代码用 JetBrains Mono
- [ ] 主标题不超出 580px 宽（左侧文字区 max-width）
- [ ] 代码块不超过 420px 宽（右侧卡片 width）
- [ ] OSS 上传后 URL 可访问
- [ ] 飞书 post 消息发送成功（看返回 `"ok": true` 或 `"code": 0`）

## 与其他 skill 的关系

- `wechat-cover-image`（Pillow 路线）：纯文字 / 数学公式 / 简单视觉元素的封面，轻量无浏览器
- `wechat-cover-html`（本 skill）：代码密集型封面，必须展示真实代码片段
- `tech-content-writer` 写完文章后，本 skill 出封面
- `aliyun-oss-upload` 把封面图传到 OSS
- `tech-wechat-publish` 把封面 URL 作为「封面图：」文字发到飞书

## 模板复用流程

1. 找到 `/tmp/cover-xxx.html`（历史模板）
2. 复制一份新文件，改 5 个区域：tag / version / title / subtitle / code
3. 改配色（4 处色值变量：`tag bg/border/color`、`hl gradient`、code `border/badge`）
4. 跑 `render_cover.py` 验证视觉
5. `vision_analyze` 检查无文字撞车

## 发布路由规则

根据文章类型自动选择飞书目标 chat：

| 文章类型 | 飞书目标 | chat_id |
|---|---|---|
| 技术类（iOS / AI / 开发工具） | AICoder 内容助手 | `oc_cde2971ca05c08d8b36f4a3f86a6544a` |
| 教育 / 育儿类 | 育儿育己 | `oc_4e795533760520c636df4e7a0260c29f` |

不要每次问用户选哪个——根据文章性质直接发对应 chat。

## 模板库

6 套可复用模板已放入 `templates/` 目录，每套含完整 HTML：

| 文件名 | 主题 | 主色 |
|---|---|---|
| `code-card-blue.html` | iOS 27 / SwiftUI / 编译器 | 蓝-青 |
| `code-card-purple.html` | AI 工具 / Agent Skills / Claude | 紫-靛 |
| `code-card-orange.html` | CI/CD / Bazel / 远程构建 | 橙-红 |
| `code-card-green.html` | LLDB / 终端 / DevTools | 绿 |
| `code-card-cyan.html` | 前端 / UI 设计 / 设计系统 | 青 |
| `text-only-blue.html` | 纯观点 / 周报（无代码卡片） | 蓝-青 |

选模板决策表见 `templates/README.md`。每套模板 5 个可定制区域：tag / version / title / subtitle / code-card。

## Future Improvements

- [ ] 参数化模板（`--title "..."` 直接渲染，不再手写 HTML）
- [ ] 支持 9:16 竖版（公众号次图）
- [x] ~~集成 OSS 上传 + 飞书发送的端到端脚本~~ → 已由 `scripts/render_cover.py` 的 `--upload` + `--feishu-chat-id` 实现
- [ ] 模板库：tech / ci / ai-tools / mobile 各一套配色预设
