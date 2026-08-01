AI 编程工具已经能快速搭出完整页面，但“能运行”和“设计成熟”之间仍有一段距离：千篇一律的渐变、层层嵌套的卡片、缺乏重点的排版，以及只在理想数据下成立的布局，都会让成品带着明显的生成痕迹。

Impeccable 试图补上这段距离。它安装在 Claude Code、Codex、Cursor 等 AI 编程工具里，用一组有明确含义的设计命令引导代理读取产品上下文、检查界面、修改源码，再用确定性规则拦截常见问题。它更接近“设计协作协议”，而非一套可直接套用的 UI 模板。

截至 2026 年 8 月，npm 上的最新版本是 `3.5.0`。官方资料列出 23 个命令和 59 条确定性检测规则。下面从安装开始，走完整个使用和工程接入过程。

## Impeccable 到底解决什么问题

通用模型知道 CSS、组件库和交互代码，却不了解你的真实受众、品牌边界和既有设计系统。一个“优化页面”的宽泛要求，常被解释成换字体、加渐变、堆阴影。页面有了变化，产品判断却没有变清晰。

Impeccable 把设计判断拆成三层上下文：

- `PRODUCT.md` 记录平台、受众、用途、定位、已有证据与长期约束。
- `DESIGN.md` 记录颜色、字体、组件、圆角、层级和视觉规则。
- `.impeccable/surfaces/` 记录某个页面的任务、证明顺序与选定方向。

它还会生成 `.impeccable/design.json` 供 Hook、Detector 和 Live Mode 使用。这个 JSON 是派生数据，更新方式是重新运行 `document`，不宜手工维护。

同一产品里的页面也会按目的区分。官方定义了四种模式：`Persuade` 面向营销与转化，`Operate` 面向后台和工作台，`Read` 面向文档与阅读，`Experience` 面向作品和沉浸体验。开发者工具的首页可以是 `Persuade`，它的文档仍是 `Read`。这样的页面级判断，比全站统一套一种“科技感”更贴近真实设计工作。

## 安装：优先使用项目级构建

安装前需要 Node.js `22.12.0` 或更高版本，并准备一个含 HTML、CSS 或前端组件的项目。从项目根目录执行：

```bash
npx impeccable install
```

安装器会检测当前使用的 AI 编程工具，展示目标目录，并让你选择项目级或全局安装。项目级更适合团队：Skill、Hook 和设计上下文跟随仓库，Claude Code 与 Codex 可以围绕同一套规则协作。

安装完成的验收不能只看命令返回成功。先确认工具实际写入了项目对应的 Skill 目录，再重载 AI 编程工具，检查 `impeccable` 是否出现在 Skill 或命令列表中。若启用了 Hook，还要查看各工具的 Hook 清单并做一次真实 UI 文件修改，确认检测结果能回到当前会话。这样能发现“清单存在、脚本路径已经失效”的静默故障。

希望脚本化安装到两个工具时，可以明确指定目标：

```bash
npx impeccable install \
  --providers=claude,codex \
  --scope=project
```

Claude Code 还有插件市场方式：

```text
/plugin marketplace add pbakaus/impeccable
```

添加市场后，需在 `/plugin` 中完成安装。Codex 采用 Skill 入口，安装完成后通过 `/skills` 查找或输入 `$impeccable` 使用；项目 Hook 位于 `.codex/hooks.json`，还要打开 `/hooks` 批准。Hook 定义更新后，Codex 会再次要求确认。

`npx skills add pbakaus/impeccable` 也能安装通用 Skill，不过它不会针对具体工具编译原生命令路径与 Hook，团队接入更适合官方安装器。安装后重启 AI 编程工具，并用下面两条命令检查和更新版本：

```bash
npx impeccable check
npx impeccable update
```

## 十分钟入门：上下文先于润色

进入项目后的第一个命令是：

```text
/impeccable init
```

在 Codex 中使用对应的 `$impeccable` Skill，并把 `init` 作为任务参数。`init` 会扫描代码库，判断 Web、iOS、Android 或 adaptive 平台，然后询问代码无法回答的信息：具体用户是谁、产品让他们完成什么、相邻产品无法复制的定位是什么、未来改动必须保留哪些约束。

这轮访谈不能交给代理自行脑补。代码能暴露技术结构，却无法证明市场定位和品牌承诺。完成后要人工阅读 `PRODUCT.md`，修正含糊表述。

接着接受初始化流程提出的 `document`，或手动运行：

```text
/impeccable document
```

它会从现有 Token、组件和页面中提取现实中的视觉系统，写入 `DESIGN.md`。对成熟工程而言，这一步的目标是记录并约束现状，避免工具在“优化”时另造一套颜色、间距和组件。

选一个边界清楚的页面做首次尝试：

```text
/impeccable polish the pricing page
```

一次典型的 `polish` 会处理对齐、间距、排版、颜色、交互状态、动效和界面文案。完成后先看 Git diff，再运行项目已有的类型检查、测试和浏览器验收。任何不符合产品判断的修改都可以撤回，并把原因明确反馈给代理。

## 23 个命令该怎么选

命令名的价值在于让人和代理共享同一套设计词汇：

- 创建与规划：`shape`，在写代码前形成页面设计 Brief。
- 评估：`critique`、`audit`，分别检查设计质量与技术实现。
- 视觉强化：`bolder`、`colorize`、`typeset`、`layout`，处理力度、色彩、排版和节奏。
- 视觉收敛：`quieter`、`distill`、`clarify`，降低噪声、删除冗余并改进文案。
- 生产加固：`harden`、`onboard`、`optimize`、`polish`，覆盖异常、引导、性能与交付质量。
- 交互与表达：`animate`、`delight`、`overdrive`，处理状态动效、细节个性和高强度效果。
- 系统维护：`document`、`extract`、`live`，记录系统、提取复用资产并进行浏览器迭代。

用户提供的 X 帖子提到了 `audit`、`adapt`、`optimize`、`colorize`、`animate` 和 `normalize`。前五项都在当前官方命令中；官方 23 个命令里没有 `normalize`。涉及间距、尺寸和视觉节奏时，应使用 `layout`、`polish`，或先通过 `document` 固化设计 Token。文章和团队文档都要以当前命令参考为准，不能把社交媒体里的旧称呼直接写进流水线。

## 进阶用法：从对话技巧走向工程门禁

遇到“看起来不对，但说不清哪里不对”的页面，可以运行 `critique`。它会从视觉层级、清晰度、情绪表达等角度评分，并结合角色视角和自动检测给出问题清单。准备上线时，再依次使用：

```text
/impeccable audit the checkout
/impeccable clarify the checkout
/impeccable harden the checkout
/impeccable polish the checkout
```

这套顺序分别负责发现技术问题、修正文案、覆盖极端状态和完成视觉整理。`harden` 要重点测试超长姓名、多语言标题、巨额数字、接口 500、离线与空数据，避免界面只适配演示数据。

Live Mode 适合视觉方向仍需比较的场景。运行 `/impeccable live` 后，它会连接本地开发服务器，允许在浏览器中选中元素、添加要求、生成三个变体，并把接受的版本写回源码。这里的“接受”会产生真实代码变更，因此仍需审查 diff 和执行回归测试。

确定性 Detector 可以独立运行，不需要 LLM 或 API Key：

```bash
npx impeccable detect src/
npx impeccable detect --json src/
npx impeccable detect --scope type src/
npx impeccable detect https://staging.example.com
```

退出码 `0` 表示没有发现，`2` 表示发现设计问题，`1` 表示命令执行失败。CI 中要区分 `2` 和 `1`，既不能把工具故障当成页面问题，也不能吞掉真实发现。存在 `DESIGN.md` 时，Detector 还会检查未声明字体、字面颜色、圆角和字号漂移。

有意保留的例外应尽量窄。例如只忽略品牌字体的具体值，并写清原因：

```bash
npx impeccable ignores add-value \
  overused-font Inter \
  --reason "Brand font"
```

整条规则全局关闭会掩盖后续回归。共享例外写入 `.impeccable/config.json` 并参加代码评审；个人实验放进 `.impeccable/config.local.json`。

## 接入已有工程的稳妥路径

现有项目不适合一上来执行全站“变好看”。推荐按下面的边界逐步推进。

### 建立可回退基线

在独立分支中安装，确认工作区干净，记录改造前截图，并跑通项目原有的构建、类型检查、单测和端到端测试。设计工具的结果不能替代业务正确性。

### 固化真实上下文

由熟悉产品的人回答 `init` 访谈，再运行 `document`。检查 `PRODUCT.md` 是否写清受众、定位和证据，检查 `DESIGN.md` 是否引用项目里的真实 Token、组件与路由。若文档与实现冲突，先判断哪一边已经过时，再修正文档或代码。

### 先审计一个页面

从投诉多、价值高、回归范围可控的页面开始：

```text
/impeccable critique the billing settings
/impeccable audit the billing settings
```

把发现按严重度和改动风险排序，一次只处理一个主题。例如先做 `adapt` 解决响应式问题，再做 `typeset`，最后执行 `polish`。小批次更容易审查，也便于发现工具是否误读既有设计规则。

### 让检测进入提交链路

本地用 Design Hook 在代理修改 UI 后立即反馈，CI 再用 Detector 做稳定门禁。Claude Code、Codex、Cursor 与 GitHub Copilot 的 Hook 时机和配置文件不同，安装后用 `/impeccable hooks status` 核对，再运行 `/impeccable doctor` 检查路径失效、配置拼写和上下文过期。Hook 没有输出不等于页面没有问题，脚本路径失效同样会表现为沉默。

### 处理 Monorepo 与版本治理

Impeccable 会读取 `package.json` workspaces、`pnpm-workspace.yaml` 或 `lerna.json`。特殊目录可在 `.impeccable/config.json` 里设置 `projectRoots`。子项目优先使用自己的 `PRODUCT.md` 和 `DESIGN.md`，缺失时再逐文件回退到仓库根目录。

团队应固定接入方式，评审 Skill、Hook、`PRODUCT.md`、`DESIGN.md` 与共享忽略项的变更。升级前运行 `npx impeccable check`，升级后重新执行 `doctor`、Detector 和项目测试，避免新规则让 CI 无预警地改变行为。

## 它有哪些边界

Impeccable 带有明确的设计立场，输出仍需要产品和设计判断。两套拥有不同词汇和反模式的前端设计 Skill 同时生效时，代理会收到互相冲突的要求，官方也建议选择一套主导规则。

Detector、Hook 和 Live Mode 主要分析 HTML 与 CSS，适合 Web 工程。iOS、Android 和 adaptive 的命令支持仍处于 alpha，原生项目依赖 `audit` 完成 VoiceOver、TalkBack、触控区域和平台规范检查，不能照搬 Web Detector 的结论。

它也不等于 Figma 的完整替代品。团队仍要处理研究、信息架构、品牌决策、复杂原型与跨角色评审。Impeccable 的优势落在另一处：把已经形成的产品和设计判断带进代码代理，让发现问题、修改源码和质量检查处于同一个开发闭环。

对于已有工程，最有价值的起点是一条短链路：`init -> document -> audit -> 小范围修复 -> polish -> detect -> 原工程测试`。当这条链路能稳定产出可审查的 diff，再扩大到 Live Mode、自动 Hook 和 CI 门禁。

## 参考资料

- [Impeccable 官网](https://impeccable.style/)
- [官方入门教程](https://impeccable.style/tutorials/getting-started)
- [命令参考](https://impeccable.style/docs)
- [设计上下文](https://impeccable.style/docs/context)
- [Detector CLI](https://impeccable.style/docs/detector)
- [Design Hooks](https://impeccable.style/docs/hooks)
- [配置与忽略项](https://impeccable.style/docs/config)
- [GitHub 仓库](https://github.com/pbakaus/impeccable)
- [Indie Fox 的体验帖](https://x.com/indie_maker_fox/status/2030172276315079059?s=20)
