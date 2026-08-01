# Cover Templates

5 套代码密集型模板 + 1 套纯文字模板，按文章主题选配色。

## 模板选择决策表

| 主题 | 推荐模板 | 主色 |
|---|---|---|
| iOS / SwiftUI 新特性（iOS 17+） | `code-card-blue.html` | 蓝-青 |
| iOS 27 / Swift 6+ / 编译器/语言版本 | `code-card-blue.html` | 蓝-青 |
| SwiftUI Liquid Glass / 性能 / 内存 | `code-card-blue.html` 或 `code-card-green.html` | 蓝/绿 |
| AI 工具 / Agent Skills / Claude / Cursor / Codex | `code-card-purple.html` | 紫-靛 |
| MCP / Skills / 自动化 Skill | `code-card-purple.html` | 紫-靛 |
| CI/CD / Bazel / 远程构建 / Linux 工具链 | `code-card-orange.html` | 橙-红 |
| 性能分析 / 终端 / DevTools / lldb / strace | `code-card-green.html` | 绿 |
| 前端 / UI 设计 / Tailwind / React / 设计系统 | `code-card-cyan.html` | 青-蓝绿 |
| 反 AI slop / 否定式约束 / 「NEVER」类 | `code-card-cyan.html` | 青-蓝绿 |
| 纯观点文章 / 周报 / 综述 | `text-only-blue.html` | 蓝-青（单色） |
| 不知道选什么 | `code-card-blue.html`（默认） | 蓝-青 |

## 5 个区域可定制

每个 `code-card-*.html` 都有 5 个固定区域，编辑后保持视觉一致：

| # | 区域 | 元素类名 | 决定什么 |
|---|---|---|---|
| 1 | **Tag** | `.tag` | 分类标签（如「AI 编程 · iOS」） |
| 2 | **Version** | `.version-badge` | 版本号 / 项目名 / Stars 标识 |
| 3 | **Title** | `.title` | 2 行主标题（第二行用 `<span class="hl">` 渐变高亮） |
| 4 | **Subtitle** | `.subtitle` | 1-2 行副标题（`<br>` 换行） |
| 5 | **Code card** | `.code-card > .code-body` | 6-12 行代码 + 语法高亮 |

## 配色 token 一览

每套模板的「token 群」是固定的（10+ 处 CSS 变量）。换配色时**整套替换** 8 个色值：
1. `body background`（深色底）
2. `.tag background/border/color`
3. `.title .hl` 渐变
4. `.version-badge .ver` 渐变
5. `.feature-chip.hl border/color`
6. `.code-card border` 1px 透明度
7. `.glow` 径向渐变
8. `.badge-new background/color/border`

最容易错的是 `.tag` 的 `background` / `border` 透明度 — 改时保持 0.12 / 0.3 的比例。

## 渲染命令

```bash
# 单套模板 + 上传到 OSS + 发飞书
python3 ~/.hermes/skills/creative/wechat-cover-html/scripts/render_cover.py \
  --html ~/.hermes/skills/creative/wechat-cover-html/templates/code-card-blue.html \
  --output /tmp/cover-new.png \
  --upload --slug new-article-20260625 \
  --feishu-chat-id oc_cde2971ca05c08d8b36f4a3f86a6544a \
  --title "..." --summary "..."
```

## 视觉规范

- **不要修改字号**：标题 34px / 副标题 15px / chip 12px / 代码 12-13px。改大改小都破坏整体感
- **不要增加 emoji**：在 Playwright 渲染下部分 emoji 变豆腐方块。用 Unicode 符号（★ · → ◆）替代
- **代码块不超过 12 行**：超过会被卡片裁切，需要扩宽或缩字号（建议缩字号到 11px）
- **feature-chip 6 个以内**：超过会换行挤压标题
- **作者行必须有**：建立信任 + 避免被读者误以为是「AI 自动生成内容」

## 添加新模板

1. 复制最接近的 `code-card-*.html`
2. 改 5 个 token（`body` / `.tag` / `.title .hl` / `.version-badge .ver` / `.glow`）
3. 用 `render_cover.py` 验证
4. `vision_analyze` 检查无视觉问题
5. 改名（如 `code-card-pink.html`）加到本 README 决策表
