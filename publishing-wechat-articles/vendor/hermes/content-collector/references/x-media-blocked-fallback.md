# X 媒体 CDN 不可达时的封面图 fallback 链

> 适用:在中国大陆/受限网络环境下,公众号文章封面图的获取失败场景。
> 2026-06-04 收录:Debug Mode Vol.07 那次抓 eric zakariasson 的封面图时验证。

## 2026-06-27 重要更新: pbs.twimg.com 现在偶发可下

**实测 2026-06-27 3 次抓图都成功** (Moysei 9 rules 配图 292KB PNG / Tony A2A Bridge 配图 361KB JPG / freak4pc CLAUDE.md 截图 69KB JPG),用 Python urllib + `Referer: https://x.com/` + `User-Agent: Mozilla/5.0` + 15s timeout 直接成功。

**网络状况决定的可用性**:同一个 IP 段,有时能下有时不能。可能是 CDN 调度 / 路由变更 / 临时网络抖动。

**修正后的工作流**:
1. **首选 Python urllib + Referer 头**,大概率直接成功 (2026-06-27 3/3 成功)
2. **失败时** curl 试一次 (`curl -sL --max-time 15`)
3. **再失败**走本文件下方 fallback 链 (HTML 自制封面)

**别再把"pbs.twimg.com 不可达"当默认假设**。抓不到时排查 5 秒 (网络状态 / IP) 再决定要不要走 fallback。

## 现象

按 content-collector SKILL.md 的 Step 5 准备封面时,正常流程是:

```
抓 X Article 原文 → 原文里 cover_media.original_img_url 是 pbs.twimg.com/...
→ curl 下载到 /tmp/ → 上传 OSS → 公网 URL
```

在受限网络里,这条链会在第一步就断:

```
$ curl -sL "https://pbs.twimg.com/media/HJ2avu_aoAA2ZMp.jpg" -o cover.jpg
# 30 秒后:curl: (28) Connection timed out
```

pbs.twimg.com 的多个 IP(104.244.46.186、108.160.165.8、52.175.9.80、199.232.45.20 等)在受限网络下全部 TCP 握手超时,无论强制 IPv4 还是 IPv6。

## 已尝试的失败路径(避免重复踩坑)

| 方案 | 结果 |
|------|------|
| `curl -sL pbs.twimg.com/...jpg` | 30s 超时 |
| `curl -4` 强制 IPv4 | 同样 30s 超时(IPv4 IP 104.244.46.186 等都封) |
| `curl --resolve pbs.twimg.com:443:108.160.165.8` | 同样 30s 超时(不是 DNS,是 TCP 被 reset) |
| `wget` 同 URL | `Operation timed out`,30s 后放弃 |
| `curl -sL api.fxtwitter.com/...` | 200 OK,但返回的 article.cover_media 仍是 pbs.twimg.com 链接 |
| `curl -sL fixupx.com/.../status/...` | 200 OK,HTML 里 `og:image` 还是 pbs.twimg.com 链接 |
| `curl -sL d.fxtwitter.com/<media>.jpg` | 200 OK 但实际是 HTML 文章页(302 redirect),不是图 |
| `curl -sL pbs.fxtwitter.com/<media>.jpg` | 502 Bad Gateway(Cloudflare 上游连不上 pbs.twimg.com) |
| `browser_navigate` x.com/<URL> | 重定向到 x.com 登录页,需登录态才能看到图片,无登录态拿不到图 |
| `browser_navigate` fixupx.com/<URL> | 服务端 302 redirect 到 x.com 主页,跟直接访问 x.com 一样 |

**关键判断:任何从 twimg.com 或 fxtwitter/fixupx 系列代理下载 twimg 源图的方式,在当前网络下都不可行。**

## 正确 fallback 链

不要再尝试原图。直接做 HTML 自制封面。

### Step 1:跳过原图下载

raw/articles 里的 frontmatter 仍然保留:

```yaml
cover_image: https://pbs.twimg.com/media/HJ2avu_aoAA2ZMp.jpg   # 远程 URL 留作来源
cover_local: ../_assets/eric-debug-mode-cover.jpg               # 本地路径,文件可以不存在
```

`_assets/` 目录是空的、文件不存在是允许的状态。下游消费者(公众号发布)看到 cover_local 文件不存在就直接用 cover_image 的远端 URL,或者更常见的 — 直接用自制的 20:9 封面替换。

### Step 2:HTML 自制 20:9 封面

用 `templates/cover-agent-engineering-series.html`(本 skill 内)做基础,改 6 个 marker:

- `SERIES_TAG_LABEL` → "Agent 工程化系列" / "育儿知识库系列" 等
- `SERIES_VOL_NUM` → "Vol.07"
- `TITLE_LINE_1` / `TITLE_LINE_2` → 主标题两行(第二行走渐变高亮)
- `SUBTITLE` → 副标题
- `AUTHOR_META_1/2/3` → 作者/团队/日期
- `CODE_SNIPPET_HEADER` + 5 行 code → 右侧代码卡片(可省略)

然后 Playwright 截图(conda Python,详见 references/html-cover-playwright.md):

```bash
/Users/nowcoder/miniconda3/bin/python3 << 'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(
        viewport={'width': 1200, 'height': 514},
        device_scale_factor=2
    )
    page = ctx.new_page()
    page.goto('file:///tmp/cover_xxx.html')
    page.wait_for_load_state('networkidle')
    page.screenshot(path='/tmp/cover_xxx.png',
                    clip={'x': 0, 'y': 0, 'width': 1200, 'height': 514})
    browser.close()
PY
```

### Step 3:`vision_analyze` 验证渲染

```python
vision_analyze(
    image_url='/tmp/cover_xxx.png',
    question='检查封面:① 标题是否清晰不被裁切 ② 顶部系列标签是否显示 '
             '③ 右侧装饰是否布局正常 ④ 整体观感有什么需要调整的'
)
```

如果发现标题被裁切、装饰溢出,改 HTML 重新跑一遍(整个 cycle < 30 秒)。

### Step 4:上传 OSS

```python
import oss2
auth = oss2.Auth('__MIGRATED_TO_RUNTIME_LOCAL__', '__MIGRATED_TO_RUNTIME_LOCAL__')
bucket = oss2.Bucket(auth, 'https://oss-cn-beijing.aliyuncs.com', 'kaelblog')
with open('/tmp/cover_xxx.png', 'rb') as f:
    bucket.put_object('wechat/cover_xxx_2026-MM-DD.png', f, headers={
        'Content-Type': 'image/png',
        'Cache-Control': 'max-age=86400',
    })
```

公网 URL = `https://kaelblog.oss-cn-beijing.aliyuncs.com/wechat/cover_xxx_2026-MM-DD.png`

### Step 5:验证公网访问

```python
import urllib.request
with urllib.request.urlopen(oss_url, timeout=10) as r:
    assert r.status == 200
```

## 通讯:告诉用户「原图缺失,已用自制封面」

在最终汇报里写明:

```
❌ Twitter 原图下载 — 当前网络 pbs.twimg.com 全部节点超时(尝试 5 个 IP),
   浏览器访问 fixupx 也被重定向到 x.com 主页(无登录态拿不到图)。
   原图跳过,改用自制 20:9 封面。
```

不要隐瞒这个降级,让用户知道。

## 不要做的几件事

- ❌ 不要反复尝试不同 IP 解决 pbs.twimg.com — 失败已验证,继续尝试是浪费 token
- ❌ 不要用 image_generate 替代 HTML 封面 — 用户偏好 100% 准确的字体渲染,FAL_KEY 也没配
- ❌ 不要把 X Article 里的"文章内嵌图"当封面 — 用户在微信端看不清楚,且那些图可能也用 pbs.twimg.com 链接
- ❌ 不要因为"封面失败"就放弃整个发布流程 — 公众号文章正文比封面重要得多,封面是装饰,可降级

## 实测记录

- 2026-06-04 eric zakariasson / Cursor Debug Mode Vol.07:按本 fallback 链完成,自制封面 2400×1028 PNG,1MB,上传 OSS 后公网访问 HTTP 200,文章按时发布
- 该系列前 6 篇(Khairallah/hooeem 等)的 raw/articles/_assets/ 目录是空的(原图下载都失败),本 fallback 链正是它们当时的处理路径
