# Impeccable 原始资料索引

- 收录日期：2026-08-01
- 主题：Impeccable 的安装、设计上下文、命令体系、自动检测与现有工程接入
- npm 核验版本：`3.5.0`
- Node.js 要求：`>=22.12.0`

## 用户提供的来源

- 官网：https://impeccable.style/
  - 本地抓取：`workspace/runs/impeccable-site-source/source/`
  - 抓取方式：仓库统一流水线，HTTPS HTML
- X 帖子：https://x.com/indie_maker_fox/status/2030172276315079059?s=20
  - 本地抓取：`workspace/runs/impeccable-x-source/source/`
  - 抓取方式：仓库统一流水线，FxTwitter 结构化接口

## 官方补充资料

- 入门：https://impeccable.style/tutorials/getting-started
  - 本地抓取：`workspace/runs/impeccable-getting-started-source/source/`
- 命令总览：https://impeccable.style/docs
  - 本地抓取：`workspace/runs/impeccable-commands-source/source/`
- 设计方法：https://impeccable.style/designing
  - 本地抓取：`workspace/runs/impeccable-designing-source/source/`
- 设计上下文：https://impeccable.style/docs/context
  - 本地抓取：`workspace/runs/impeccable-context-source/source/`
- Detector CLI：https://impeccable.style/docs/detector
  - 本地抓取：`workspace/runs/impeccable-detector-cli-source/source/`
- Design Hooks：https://impeccable.style/docs/hooks
  - 本地抓取：`workspace/runs/impeccable-hooks-source/source/`
- 配置与忽略项：https://impeccable.style/docs/config
  - 本地抓取：`workspace/runs/impeccable-config-source/source/`
- GitHub：https://github.com/pbakaus/impeccable
- npm：https://www.npmjs.com/package/impeccable

## 已核验事实

- Impeccable 当前以一个 `impeccable` Skill 暴露 23 个命令。
- 官方推荐从项目根目录运行 `npx impeccable install`，安装器按 AI 编程工具生成对应构建。
- 初始化命令生成 `PRODUCT.md`，并建议继续运行 `document` 生成 `DESIGN.md` 与 `.impeccable/design.json`。
- 官方支持 Claude Code、Cursor、GitHub Copilot、Gemini CLI、Codex CLI 等工具。
- Detector 提供 59 条确定性规则，无需 LLM 或 API Key；退出码 `0` 表示无发现、`2` 表示发现问题、`1` 表示执行失败。
- Design Hook 支持 Claude Code、GitHub Copilot、Codex、Cursor；Codex 安装或更新后需要在 `/hooks` 中批准项目 Hook。
- Native iOS、Android 与 adaptive 支持仍标记为 alpha；Live Mode、Detector 和 Hook 以 Web/HTML/CSS 为主。

## 帖文校正

X 帖子提到 `audit`、`adapt`、`optimize`、`colorize`、`animate` 和 `normalize`。除 `normalize` 外，其余都能在当前官方 23 个命令中找到；截至收录日，官方命令列表没有 `normalize`。间距、尺寸和视觉节奏相关工作由 `layout`、`polish`、`document` 等命令覆盖，文章不把 `normalize` 当作当前正式命令。

## 资料边界

- 官网推荐语和 X 帖子属于作者或用户评价，不作为效果保证。
- npm 版本与命令能力会更新，执行前用 `npx impeccable check` 和官方 changelog 复核。
- Impeccable 会修改项目源码并可安装 Hook；接入现有工程时需使用分支、代码审查和原有测试门禁。
