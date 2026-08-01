# 本项目 md-to-html 使用约定

## 主题分配

| 公众号 | 主题 | 风格 | 用途 |
|--------|------|------|------|
| 技术号（AICoder） | **极客黑** | 深色背景 + 代码高亮 | 技术文章、编程教程、工具介绍 |
| 育儿号（育儿育己） | **橙心** | 暖橙色调 | 育儿文章、亲子内容、心理科普 |

## 标准命令

```bash
cd ~/.hermes/skills/productivity/md-to-html

# 技术号
python3 scripts/md_to_html.py render article.md --themes 极客黑 --output /tmp/article.html

# 育儿号
python3 scripts/md_to_html.py render article.md --themes 橙心 --output /tmp/article.html
```

## 默认行为

- **模式**：inline（CSS 内联到元素 `style` 属性，公众号粘贴不丢样式）
- **脚注**：默认开启（`[text](url)` → `[text][N]` 上标，文末引用链接）
- **代码高亮**：自动配对（极客黑→atom-one-dark，橙心→atom-one-light）
- **Frontmatter**：自动剥离，不渲染为正文

## 发布流程

1. 渲染 HTML → 2. 上传 OSS → 3. 飞书发链接 → 4. 助理浏览器 Ctrl+A 粘贴到公众号

## 查找主题

```bash
python3 scripts/md_to_html.py list-themes           # 列出全部
python3 scripts/md_to_html.py list-themes --query 极客  # 搜索
python3 scripts/md_to_html.py list-themes --query 橙心  # 搜索
```
