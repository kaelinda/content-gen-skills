# Impeccable：给 AI 编程代理补充设计上下文与质量反馈

## 一句话定义

Impeccable 是一套安装到 AI 编程工具里的前端设计 Skill。它把产品目标、视觉系统、设计命令、浏览器迭代和确定性检测串成一个可重复的工程流程。

## 核心模型

1. `PRODUCT.md` 保存平台、受众、定位、证据和长期约束。
2. `DESIGN.md` 保存颜色、字体、组件、圆角、层级和设计规则。
3. `.impeccable/surfaces/` 保存单个页面的目标、模式、证据顺序与方向。
4. `.impeccable/design.json` 是自动化读取的派生数据，不手工修改。
5. 命令、Hook、Detector 和 Live Mode 共享这些上下文。

## 四种页面模式

- `Persuade`：落地页、营销页、定价页，目标是让访问者理解并行动。
- `Operate`：后台、仪表盘、编辑器，优先扫描效率、状态与稳定导航。
- `Read`：文档、指南、帮助中心，优先理解、节奏与层级。
- `Experience`：作品集、展览、画廊，让内容本身占据视觉中心。

模式属于页面，不属于公司。开发者工具的官网仍可归入 `Persuade`，文档页归入 `Read`。

## 推荐闭环

```text
init -> document -> critique/audit -> 定向命令 -> polish/harden -> detect -> 原工程测试
```

- `critique` 回答设计是否有效，包含评分、角色视角和自动检测。
- `audit` 检查可访问性、性能、主题、响应式和反模式。
- `polish` 做交付前的综合整理。
- `harden` 覆盖长文本、国际化、错误、离线和极端数据。
- `detect` 是确定性规则门禁，适合 CI；它不能替代真实浏览器验收与业务测试。

## 接入原则

- 项目级安装优先，确保 Claude Code、Codex 等协作者共享同一版本与上下文。
- `init` 的访谈必须由产品知情者回答，不能只靠代码猜测定位。
- 现有工程先运行 `document` 记录现实，再进行小范围改造。
- 每次只命名一个页面或区域，控制变更范围。
- 忽略项使用具体规则、具体值或具体文件，并写明原因。
- 设计 Hook 是快速反馈层，CI、类型检查、单测和浏览器验收仍保留。
- 更新 `PRODUCT.md` 或 `DESIGN.md` 时按普通代码评审处理。

## 工具边界

- 这是有设计立场的代理协作层，不是纯静态检查器。
- Detector、Hook 与 Live Mode 主要面向 Web；原生移动端能力仍处于 alpha。
- Live Mode 会把接受的视觉变体写回源码，必须查看 diff。
- 上下文缺失或陈旧会让结果退回通用模板倾向。
- 当前官方命令没有 `normalize`；类似需求应使用 `layout`、`polish` 或设计系统文档化。

## 来源

- https://impeccable.style/
- https://impeccable.style/tutorials/getting-started
- https://impeccable.style/docs
- https://impeccable.style/docs/context
- https://impeccable.style/docs/detector
- https://impeccable.style/docs/hooks
- https://impeccable.style/docs/config
- https://github.com/pbakaus/impeccable
