# Apple Developer Video 页面内容提取指南

## 页面结构

每个 WWDC Session 页面 (`https://developer.apple.com/videos/play/wwdc{YEAR}/{SESSION_ID}/`) 有 4 个 Tab：

| Tab | CSS Class | 内容 |
|-----|-----------|------|
| About | `.supplement.details` | 标题、简介、Chapter 列表、Resources、Related Videos |
| Summary | `.supplement.summary` | 每个 Chapter 的一句话摘要（时间戳 + 概要） |
| Transcript | `.supplement.transcript` | 完整逐字稿（时间戳内联在文本中） |
| Code | `.supplement.sample-code` | 所有代码示例（带时间戳标题 + Copy Code 按钮） |

## JavaScript 提取命令

在 `browser_console` 中执行，每次用 IIFE 避免变量重复声明：

```javascript
// 获取 Transcript（完整逐字稿）
(() => {
  const el = document.querySelector('.supplement.transcript');
  return el?.innerText?.substring(0, 10000);
})()

// 获取 Code（所有代码示例）
(() => {
  const el = document.querySelector('.supplement.sample-code');
  return el?.innerText?.substring(0, 12000);
})()

// 获取 Summary（章节摘要）
(() => {
  const el = document.querySelector('.supplement.summary');
  return el?.innerText?.substring(0, 5000);
})()

// 检查当前激活的 Tab
(() => {
  const els = document.querySelectorAll('[class*="supplement"]');
  return Array.from(els).map(e => e.className);
})()
```

注意：innerText 超过 ~10000 字符时需要分段获取，offset 递增（如 10000-20000, 20000-30000）。

## Tab 切换

Tab 链接在页面 snapshot 中的 ref 通常是：
- About: `e121`
- Summary: `e122`  
- Transcript: `e123`
- Code: `e124`

（ref ID 每次加载可能不同，以实际 snapshot 为准）

## Resources 模块探索

每个 Session 页面底部有 Resources 区域（Swift Blog、Documentation、Swift Forums）和 Related Videos。

提取 Resources 链接的 URL：

```javascript
(() => {
  const links = document.querySelectorAll('a');
  const resources = [];
  links.forEach(a => {
    const text = a.textContent.trim();
    if (['Swift Blog', 'Explore documentation on swift.org', 'Swift Forums'].includes(text)) {
      resources.push({ text, href: a.href });
    }
  });
  // 也提取 Related Videos
  const related = [];
  const h4s = document.querySelectorAll('h4');
  h4s.forEach(h4 => {
    if (h4.textContent.includes('WWDC')) {
      let ul = h4.nextElementSibling;
      while (ul && ul.tagName !== 'UL') ul = ul.nextElementSibling;
      if (ul) {
        ul.querySelectorAll('a').forEach(a => {
          related.push({ text: a.textContent.trim(), href: a.href });
        });
      }
    }
  });
  return JSON.stringify({ resources, related }, null, 2);
})()
```

Resources 链接通常指向：
- `https://www.swift.org/blog/` — 博客（含版本发布说明、案例研究）
- `https://www.swift.org/documentation/` — 文档入口
- `https://forums.swift.org/` — 社区论坛

**关键 pitfall**：Swift.org 博客文章的 URL slug 可能与标题不完全一致（省略 "the"、用点号替代连字符）。**从 DOM 中获取真实 href**，不要手动拼 URL。

探索 Resources 的价值：博客文章通常包含 Session 中没有的细节：
- Swift Evolution 提案编号
- 实际案例数据（如 Goodnotes 的 220 万行 Swift/Wasm 代码、147 万行共享）
- API 详细说明（如 API Notes YAML 格式、SWIFT_SHARED_REFERENCE 宏）
- 迁移指南和工具链信息

用 `delegate_task` 并行读取多个资源页面可大幅提速。

## iOS 开发者视角分析框架

提取内容后，按以下维度组织技术解读：

1. **语言层面改进** — 每天写代码会用到的语法糖、类型系统变化
2. **框架/库更新** — Foundation、SwiftUI、Testing 等标准库变化
3. **工具链 & 工程化** — Xcode、SwiftPM、Build System、CI 相关
4. **性能 & 底层** — 编译器优化、内存模型、所有权系统
5. **跨平台 & 互操作** — Swift 出圈（Wasm、Android、Embedded、C/C++/Java 互操作）
6. **迁移指南** — 从旧版本升级的 breaking changes 和 deprecations

## 常见 Pitfall

- **语言提示弹窗**：页面加载后可能出现「查看简体中文页面」弹窗，先用 `browser_click` 关闭（`关闭语言建议` 按钮），再操作 Tab，否则 snapshot 中的 ref 可能不稳定
- **Transcript 分段获取**：innerText 超过 ~10000 字符时需分段。每次用新的 IIFE（变量名不能重复），offset 递增。推荐模式：
  ```javascript
  // 第一段
  (() => { const el = document.querySelector('.supplement.transcript'); return el?.innerText?.substring(0, 10000); })()
  // 后续段（用不同变量名）
  (() => { const el2 = document.querySelector('.supplement.transcript'); return el2?.innerText?.substring(10000, 20000); })()
  ```
  如果直接复用 `el` 变量名会报 `Identifier has already been declared` 错误（因为是在同一 console 上下文）
- **Code Tab CSS 类名**：Code Tab 的 CSS 类是 `.supplement.sample-code`，不是 `.supplement.code`
- **Summary Tab**：Summary 的 CSS 类是 `.supplement.summary`，内容格式为「时间戳 - 概要」逐条排列
- **Tab 激活状态检测**：用 `document.querySelector('.tab.active')` 确认当前 Tab，用 `document.querySelectorAll('[class*="supplement"]')` 列出所有 Tab 内容区
- **Transcript 时间戳内联**：格式为 `0:45Some of them...`（时间戳和文本之间无空格），解析时用正则 `(\d+:\d+)([A-Z])` 在时间戳后插入分隔符
- **bot detection**：Apple Developer 页面有反爬检测，当前环境无 residential proxy。如遇加载失败，重试通常有效
- **ref ID 不稳定**：每次 `browser_navigate` 或 Tab 切换后，ref ID 可能变化，操作前先 `browser_snapshot` 获取最新 ref
- **Resources URL slug 不一致**：Swift.org 博客 URL 可能省略标题中的 "the" 或用不同分隔符，从 DOM 获取真实 href
