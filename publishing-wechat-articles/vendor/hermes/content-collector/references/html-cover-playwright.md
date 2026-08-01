# HTML 封面图 + Playwright 精确截图（推荐方案）

## 为什么不用 browser_vision

`browser_navigate(file://xxx.html) + browser_vision` 的问题：
- 浏览器视口尺寸不一定正好是 1200×514，会被压成 16:9 默认窗口
- 截图依赖 vision 模型识图再保存，开销大且不可重复
- 中文长标题经常被截断或 DPI 不对

**Playwright 直接调用 chromium 截图**，可控、可重复、尺寸精确。

## 工作流

### Step 1: 写 HTML 模板

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1200px;
    height: 514px;        /* ← 严格 20:9 比例 */
    font-family: -apple-system, "PingFang SC", "Helvetica Neue", Arial, sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: #fff;
    position: relative;
    overflow: hidden;
  }
  /* 装饰、标题、副标题、meta 全部用 absolute 或 flex 布局 */
  .title { font-size: 64px; font-weight: 800; line-height: 1.2; }
  .title .highlight {
    background: linear-gradient(135deg, #6366f1, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
</style>
</head>
<body>
  <!-- 内容 -->
</body>
</html>
```

完整模板参考 `references/html-cover-templates.md`。

### Step 2: Playwright 截图

**必须用 conda Python**（系统 Python 没有 playwright 包，pip install 在本机常超时）：

```bash
/Users/nowcoder/miniconda3/bin/python3 <<'PY'
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    # device_scale_factor=2 出 2x 图,适配公众号高 DPI 缩略图
    context = browser.new_context(
        viewport={'width': 1200, 'height': 514},
        device_scale_factor=2
    )
    page = context.new_page()
    page.goto('file:///tmp/cover_xxx.html')
    page.wait_for_load_state('networkidle')
    page.screenshot(
        path='/tmp/cover_xxx.png',
        clip={'x': 0, 'y': 0, 'width': 1200, 'height': 514}
    )
    browser.close()
PY
```

关键参数：
- `viewport={'width': 1200, 'height': 514}` — 严格 20:9
- `device_scale_factor=2` — 2 倍 DPI,适合公众号高分辨率缩略图(图片实际 2400×1028)
- `clip` 显式指定截图区域,避免被页面 padding/scrollbar 污染

### Step 3: 上传 OSS（必须）

```python
import oss2
auth = oss2.Auth('__MIGRATED_TO_RUNTIME_LOCAL__', '__MIGRATED_TO_RUNTIME_LOCAL__')
bucket = oss2.Bucket(auth, 'https://oss-cn-beijing.aliyuncs.com', 'kaelblog')
with open('/tmp/cover_xxx.png', 'rb') as f:
    bucket.put_object('wechat/cover_xxx.png', f, headers={
        'Content-Type': 'image/png',
        'Cache-Control': 'max-age=86400',
    })
# 拿到公网 URL: https://kaelblog.oss-cn-beijing.aliyuncs.com/wechat/cover_xxx.png
```

## 验证清单

- [ ] HTML body 严格 1200×514
- [ ] Playwright viewport 等同尺寸
- [ ] device_scale_factor=2 出高清图
- [ ] 用 `vision_analyze` 检查实际渲染效果(文字不被裁、布局正常)
- [ ] 上传 OSS 后用 `urllib.request.urlopen(oss_url)` 验证公开访问

## 实测案例（2026-06-03）

任务：为 Khairallah 的 Claude Projects+Skills 长文生成封面

1. HTML 模板：暗紫渐变 + 网格背景 + orb 光晕 + 渐变高亮标题
2. Playwright 截图：1MB PNG,2400×1028(2x)
3. 视觉验证：标题、徽章、arrows 全部清晰
4. 上传 OSS:https://kaelblog.oss-cn-beijing.aliyuncs.com/wechat/cover_khairallah_2026-06-03.png
5. 公开访问验证通过
6. 用于飞书 post 发布请求的封面图

耗时：< 1 分钟（HTML 写好 + Playwright 截图 + 上传）

## 与 image_generate 方案的对比

| 维度 | image_generate | HTML + Playwright |
|------|---------------|-------------------|
| 速度 | 30-60 秒（API 等待） | 5-10 秒（本地渲染） |
| 文字可读性 | 不稳定（AI 生图常写错字） | 100% 准确（HTML 字体） |
| 品牌一致性 | 不可控 | 100% 复用 CSS |
| 中文支持 | 一般 | 完美（系统字体） |
| 离线可用 | 否（需 FAL_KEY） | 是 |
| DPI 控制 | 不可控 | 精确（device_scale_factor） |

**结论**：技术号公众号封面默认走 HTML + Playwright。仅当需要插画/照片元素时用 image_generate。
