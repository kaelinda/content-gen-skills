# md-to-html 公众号粘贴工作流（带图版）

> 整理 2026-06-18 第一次用 md-to-html skill 渲染 WWDC26 文章时的实战 playbook。
> 这个工作流是「带图版 publish」的标准动作，纯文字文章继续走标准流程。

## 适用场景

- 源材料含图（推文原图、WWDC session 截图、产品 UI 截图）
- 用户说「带图版」「带图文的公众号文章」「重新排列」「复制粘贴到公众号编辑器」
- WWDC / 苹果发布会总结类文章
- 教程类含步骤截图

不适用：纯文字文章（用标准 publish 流程即可，HTML 反而冗余）。

## 工作流（5 步）

### Step 1: 拉源图到本地

```bash
# 推文原图（含参数 ?name=orig 获取最高分辨率）
curl -sL "https://pbs.twimg.com/media/<id>.jpg?name=orig" -o /tmp/asset.jpg

# 验证
file /tmp/asset.jpg
# 期望: JPEG image data, ..., <width> x <height>
```

### Step 2: 上传源图到 OSS

```python
import sys
sys.path.insert(0, '/Users/nowcoder/miniconda3/lib/python3.9/site-packages')
import oss2

OSS_AK = "__MIGRATED_TO_RUNTIME_LOCAL__"
OSS_SK = "__MIGRATED_TO_RUNTIME_LOCAL__"
OSS_BUCKET = "kaelblog"
OSS_ENDPOINT = "https://oss-cn-beijing.aliyuncs.com"

auth = oss2.Auth(OSS_AK, OSS_SK)
bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)

# 注意 key 前缀：aicoder/<topic>/ 区分于 aicoder/covers/
key = "aicoder/wwdc26/wwdc26-xcode27-title.jpg"
url = f"https://{OSS_BUCKET}.oss-cn-beijing.aliyuncs.com/{key}"

with open("/tmp/asset.jpg", "rb") as f:
    result = bucket.put_object(key, f, headers={"Content-Type": "image/jpeg"})
print(f"HTTP {result.status}, URL: {url}")
```

**Pitfall**: Content-Type 必须设对（`image/jpeg` / `image/png`），否则浏览器访问会触发下载。

### Step 3: 用 md-to-html skill 渲染 Markdown

```bash
# 推荐主题：极客黑（深色 + inline CSS，最适合公众号不掉格式）
python3 ~/.hermes/skills/productivity/md-to-html/scripts/md_to_html.py \
  render /tmp/article.md \
  --themes 极客黑 \
  --output /tmp/article.html \
  --title "Xcode 27 把 agent 装进了编辑器"
```

**关键**：
- Markdown 中写 `![alt](https://kaelblog.oss-cn-beijing.aliyuncs.com/...)` 即可，渲染后图片 URL 保留 + 自动 inline 化样式
- 主题选 `极客黑`（MDNice）→ 默认 inline 模式 → CSS 全内联到元素 `style` 属性
- 输出 HTML 文件大小通常 80-150KB（CSS 内联占大头）

**主题查询命令**：
```bash
python3 ~/.hermes/skills/productivity/md-to-html/scripts/md_to_html.py list-themes
python3 ~/.hermes/skills/productivity/md-to-html/scripts/md_to_html.py list-themes --query 极客
```

### Step 4: 上传 HTML 到 OSS

```python
key = "aicoder/<topic>/article-<slug>.html"
html_url = f"https://{OSS_BUCKET}.oss-cn-beijing.aliyuncs.com/{key}"
with open("/tmp/article.html", "rb") as f:
    bucket.put_object(key, f, headers={"Content-Type": "text/html; charset=utf-8"})
```

**为什么 HTML 不能直接发飞书**：lark-cli 发送消息有大小限制（实测单条 markdown 消息超过 ~30KB 会被截断或失败），HTML 100KB+ 必须走 OSS 链接。

### Step 5: 飞书发送（多段 + 资源链接 + body）

```python
# 飞书发送函数（标准 tech-wechat-publish 流程）
import subprocess, re

CHAT_ID = "oc_cde2971ca05c08d8b36f4a3f86a6544a"

def send(msg):
    return subprocess.run(
        ["lark-cli", "im", "+messages-send",
         "--as", "user", "--chat-id", CHAT_ID, "--markdown", msg],
        capture_output=True, text=True, timeout=30,
    )

def split_chunks(text, max_len=880):
    paragraphs = text.split("\n\n")
    chunks = []
    cur = ""
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if not cur:
            cur = p
        elif len(cur) + len(p) + 2 <= max_len:
            cur = cur + "\n\n" + p
        else:
            chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    return chunks

# 从 DeepSeek 输出读 body（注意：去图片 md 语法，飞书不渲染 md 图）
body_md = re.sub(r'!\[[^\]]*\]\([^)]+\)\n*', '', body).strip()
chunks = split_chunks(body_md)

messages = [
    # 段 1: 全部资源链接（封面 + 推文原图 + HTML 完整版）
    f"📎 封面图：{cover_url}\n\n"
    f"# {title}\n\n"
    f"📷 推文原图：{asset_url}\n\n"
    f"📄 **完整 HTML 版（含图，可直接复制粘贴到公众号编辑器）**：{html_url}\n\n"
    f"---\n\n"
    f"使用说明：打开 HTML 链接，浏览器中 Ctrl+A 全选 → 复制 → 粘贴到公众号编辑器（自动带上主题 + 内联图片）。",
    *chunks,  # 段 2+: body
    "\n---\n\n📮 本文由 Hermes Agent 自动整理发布，欢迎关注 AICoder 公众号。",
]
for i, msg in enumerate(messages):
    r = send(msg)
    if r.returncode == 0:
        mid = re.search(r'"message_id":\s*"([^"]+)"', r.stdout)
        print(f"  ✅ {i+1}/{len(messages)} {mid.group(1) if mid else '?'}")
```

## 关键 Pitfalls（2026-06-18 实测）

1. **md-to-html 渲染后首行是 `<p>标题注释</p>`**：因为在 markdown 头部写了 `<!-- 标题: ... -->` 注释，HTML 渲染时会把它包成 `<p>`。**解决**：要么不加注释，要么用 HTML comment 单独放文件外（不要写在 md body 里）。
2. **HTML 100KB+ 不能直接 lark-cli 发**：必须上传 OSS 发链接。助理 bot 收到链接后人工浏览器打开 → Ctrl+A → 复制 → 粘贴到公众号编辑器。
3. **飞书不直接渲染 markdown 图片语法 `![]()`**：必须把 md 中的图片去掉（或保留作"参考"用，单独发 OSS 链接段）。HTML 版才带图。
4. **md-to-html 默认 `极客黑` 主题渲染后** `文章阅读体验` 是公众号深色风格（黑底白字）。如果想要浅色/更朴素风格，试试 `heti`（中文阅读体验好）或 `github-light`。
5. **macOS 上用 md-to-html 默认走 `python3` (即 3.11)**，不需要 `conda python`。但脚本里有 `pip install pygments` 依赖，没装 pygments 也能跑（只是代码块没语法高亮）。
6. **图片 URL 必须用 `https://`，不要 `http://`**：md-to-html 渲染时如果图片是 `http://`（OSS 默认是 https，但有些边缘配置）会被某些浏览器拒绝加载。
7. **HTML URL 验证**：`curl -I <html_url>` 应该返回 200 + `Content-Type: text/html; charset=utf-8`，否则助理在浏览器里打开会看到原始 HTML 源码。

## 实测工作流时间线

- 2026-06-18 第一次跑通：下载推文图（5秒）→ 上传 OSS（3秒）→ 写文章 DeepSeek（30秒）→ md-to-html 渲染（5秒）→ 上传 HTML（3秒）→ 飞书发送 10 段（20秒）= **总耗时约 1 分钟**

## 与"标准纯文字 publish"的区别

| 步骤 | 纯文字 | 带图（md-to-html） |
|---|---|---|
| 源图下载 | 不需要 | curl 拉 + file 验证 |
| 源图上传 | 不需要 | 上传 OSS `aicoder/<topic>/` 子目录 |
| 封面生成 | wechat-cover-image skill | 同（封面单独走，**不嵌入 body**） |
| 渲染 | 不需要 | md-to-html skill（HTML 上传 OSS） |
| 飞书段 1 | 封面 + 标题 | 封面 + 标题 + **推文原图 + HTML 链接** |
| 助理最后一步 | 人工复制 body | **人工浏览器打开 HTML → Ctrl+A → 粘贴** |

## 助理 bot (AICoder 内容助手) 收到飞书消息后的标准动作

1. 打开 📎 封面图 OSS 链接 → 右键另存为 → 上传到公众号图文封面位
2. 打开 📄 HTML 完整版链接 → 浏览器 Ctrl+A 全选 → 复制 → 切换到公众号编辑器 → 粘贴（自动带上主题 + 图片）
3. 在公众号编辑器里调整小细节（首段图、段落间距）→ 预览 → 群发

AI 不能完全替代"最后一步人工粘贴"，但**能让这一步从 30 分钟压缩到 5 分钟**（不需要重新找图、重新排版）。
