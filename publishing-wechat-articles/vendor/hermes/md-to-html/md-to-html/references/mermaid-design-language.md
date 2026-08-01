# 手绘 CSS 图设计语言（mermaid 原生化）

本文档是 **高质量手动路径**：当 `--mermaid-render image` 的自动出图（标准 mermaid 外观）
不够好看时，由 Claude 把每个 mermaid 图**重画成手写 HTML/CSS 卡片**，再用浏览器截图成图片
内联/上传，绕过公众号洗 CSS。自动路径见 [SKILL.md](../SKILL.md) 的「发布管线」。

> 公众号硬约束（先记住）：不渲染 mermaid；洗掉 `<style>` / `class` / 外部 CSS；只保留行内
> `style` 和 `<img>`；正文外链不可点；≈90% 是手机窄屏阅读。
> 结论：CSS 排版只在浏览器/预览里有效；**真正发布要把图变成图片**。

## 整体流水线

1. **清洗 md**：去掉 YAML frontmatter 和所有 `<!-- HTML 注释 -->`（脚本默认已做，见 `--keep-comments`）。
2. **渲染基底**：用 `render`（MDNice 主题，inline 模式）出 HTML，文章被包进 `<article id="nice">`。
3. **mermaid 原生化**：把每个 `<div class="mermaid">…</div>` 替换成手写 HTML/CSS 图（见下）。
4. **浏览器验证 + 迭代**：本地渲染，按桌面 / 手机两个宽度截图看效果，反复调。
5. **图片化发布**：把每张 CSS 图截成 PNG，再 base64 内联或上传 OSS 回填到 HTML。

## 一、设计语言（统一）

- **语义配色固定**：人 = 蓝 / 角色·Agent = 紫 / 知识·记忆 = 绿 / 枢纽 = 橙 / 底座 = 深紫。
- **节点**用卡片 `.vmd-n`（圆角 + 描边 + 淡色底 + 可带 `<small>` 副标题）。
- **连接**用竖向 ↓ 箭头 + 标签；旁支（如「写入知识库」）用虚线小药丸。
- **常见图式**：对比并列（flex+wrap）/ 中心枢纽辐射 / 分层堆叠带 / 流程时序。

### CSS 作用域（必须）

所有自绘样式加 `#nice .vmd` 前缀，避开正文样式；并对 `.vmd` 内的 `div/span/ul/li` 做
`margin/padding/list` reset，防止被 MDNice 正文规则污染。

```css
#nice .vmd { /* 容器 */ }
#nice .vmd, #nice .vmd * { box-sizing: border-box; }
#nice .vmd ul, #nice .vmd li { margin: 0; padding: 0; list-style: none; }
#nice .vmd-n {            /* 节点卡片 */
  border-radius: 12px; border: 1px solid #d0d7de; padding: 10px 14px;
}
/* 语义色（示例） */
#nice .vmd-人      { background: #eaf2ff; border-color: #4a90d9; }
#nice .vmd-agent   { background: #f3eafe; border-color: #8b5cf6; }
#nice .vmd-知识    { background: #e9f9ef; border-color: #34c759; }
#nice .vmd-枢纽    { background: #fff2e0; border-color: #ff9500; }
#nice .vmd-底座    { background: #efe9fb; border-color: #5b3ea8; }
```

## 二、移动端适配（重点，公众号是手机端）

- 加 `@media (max-width:540px)`：缩内距 / 字号、网格改 2 列、多行文本一律**左对齐**、
  并列卡片用 `flex-wrap`。
- **图太复杂就拆**：像「四段流程 / 时序」这种不要堆在一张图里（手机上必然拥挤）——
  每个阶段单独画一张小结构图（序号标题 + 角色节点 + 箭头 + 旁支 + 底部质量门），竖向流、各图匀称。
- **默认竖向布局优先**；桌面端再用媒体查询做多列。

```css
@media (max-width: 540px) {
  #nice .vmd-row { flex-wrap: wrap; }
  #nice .vmd-grid { grid-template-columns: repeat(2, 1fr); }
  #nice .vmd-n { font-size: 14px; padding: 8px 10px; text-align: left; }
}
```

## 三、避坑

- **别用绝对定位**画「时间线圆点」（跨内距极易错位）→ 改用彩色 `border-left` 竖线给一组步骤归组，
  简单且永不错位。
- 代码块里的占位符 `<xxx>` 要确保被转义成 `&lt;xxx&gt;`，否则被浏览器当标签吞掉。
- 自绘图元素**不要写行内 `style`**（留给 CSS），但要知道这部分发布时会被公众号洗掉 → 见第四步图片化。

## 四、把图片放进 HTML（发布关键）

公众号洗 CSS 但保留 `<img>`，所以「好看的 CSS 图」必须转成「图片」才能在公众号里活下来。

**做法（CSS 图 → 图片 → 内联 / 上传）：**

1. 本地起服务：`python3 -m http.server 8765`（headless 浏览器禁 `file://`，必须走 http）。
2. 浏览器（Playwright / chrome-devtools MCP）打开页面，设手机宽度（≈390px）+ `deviceScaleFactor 2` 出高清。
3. 给每个图元素加 `id`，逐个 element-screenshot 存成 PNG。
4. 回填两选一：
   - **base64 内联**：`<img src="data:image/png;base64,iVBOR..." style="width:100%;max-width:680px;display:block;margin:16px auto;">`
   - **OSS 外链**：`python3 ../ali-oss/scripts/ali_oss.py upload fig.png --prefix article --acl public-read --quiet`
     拿到 URL 后 `<img src="https://…/fig.png" style="...">`。

产物特性：自包含 / 体积小（OSS）、可直接粘公众号（图片被公众号自动上传保留）、手机显示清晰。

**备选**：纯 mermaid 也可用 `@mermaid-js/mermaid-cli (mmdc)` 直接导 PNG（`-b white -w 1600 -s 2`）；
注意它依赖 puppeteer+Chromium，npm 源常缺 puppeteer，需 `npm_config_registry=https://registry.npmjs.org`。
脚本自带的 `--mermaid-render image` 走服务端 HTTP 渲染（mermaid.ink / kroki），无需本地浏览器。

## 验证清单

- [ ] frontmatter / HTML 注释已剔除，不进产物。
- [ ] 占位符 `<…>` 已转义可见。
- [ ] 桌面 + 375px 手机宽度都截图看过，无横向溢出、不拥挤。
- [ ] 复杂流程已拆成多张小图。
- [ ] 发布版：CSS 图已转 PNG，并 base64 内联或上传 OSS。
