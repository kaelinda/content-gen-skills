# WWDC 技术文章系列：从 Session 视频到批量发布

## 端到端流程

```
1. 提取 → browser_console 从 4-Tab DOM 拉取 About/Summary/Transcript/Code
2. 分析 → 按 6 维框架（语言/框架/工具链/性能/跨平台/迁移）归类技术点
3. 选题 → 按开发者影响分 Tier（每天用/测试受益/性能调优/跨平台/生态）
4. 批量写作 → delegate_task 并行写 3 篇（受 max_concurrent_children 限制）
5. 质检 → execute_code 运行禁用词扫描 + 字数统计
6. 逐篇发布 → lark-cli 分段发送到飞书（title → segments → cover）
```

## Step 1: 内容分析与选题

提取完 4-Tab 内容后，按以下步骤组织：

1. 列出所有 Chapter（来自 About Tab）
2. 将 Chapter 归类到技术主题（去重、合并相关章节）
3. 按开发者日常影响排序为 Tier：

```
Tier 1 — 每天写代码都会用到（语言语法糖、API 简化）
Tier 2 — 测试 & 工具链直接受益
Tier 3 — 性能调优（重度场景）
Tier 4 — 跨平台互操作（长期趋势）
Tier 5 — 生态 & 未来
```

4. 每个 Tier（或 Tier 内的子主题）对应一篇文章
5. 总篇数控制在 5-8 篇（太多读者疲劳，太少覆盖不够）

## Step 2: 并行写作（delegate_task）

当文章 ≥ 3 篇时，用 `delegate_task` 的 batch 模式并行写作：

```
delegate_task(tasks=[
  {goal: "Write Vol.N ...", context: "...style rules + content...", toolsets: ["file"]},
  {goal: "Write Vol.N+1 ...", context: "...", toolsets: ["file"]},
  {goal: "Write Vol.N+2 ...", context: "...", toolsets: ["file"]},
])
```

**注意事项：**
- `max_concurrent_children` 默认为 3（受用户 config 限制），一次最多 3 篇并行
- context 中必须包含：禁用词清单、风格规则、代码示例、收束金句格式、系列上下文（其他卷标题）
- 每篇写到 `/tmp/wwdc{YEAR}-vol{NN}-{slug}.md`
- 并行写完后再统一质检（不要边写边检）

## Step 3: 批量质检

```python
# execute_code 中运行
import re
BANNED_PATTERNS = [
    (r'不是[^，。]+[，,]而是', '不是X，而是Y'),
    (r'与其[说]?(?:[^，。]+)[，,]不[如说]', '与其X，不如Y'),
    (r'首先.*其次.*最后', '首先...其次...最后'),
    (r'值得注意的是', '值得注意'),
    (r'总的来说', '总的来说'), (r'总而言之', '综上所述'),
    (r'在当今', '在当今'), (r'不可否认', '不可否认'),
    (r'众所周知', '众所周知'), (r'显而易见', '显而易见'),
    # ... 完整清单见 SKILL.md
]

for vol, path in files:
    with open(path) as f: content = f.read()
    hits = [(l, re.findall(p, content)) for p, l in BANNED_PATTERNS if re.findall(p, content)]
    total = len(content)
    status = "✅" if not hits else "❌"
    print(f"{status} {vol}: {total} chars")
```

发现禁用词立即修复（patch），修复后重跑确认。

## Step 4: 逐篇发布

按顺序发布，每篇流程：

1. 生成封面图（HTML + Chrome headless → /tmp/cover_volNN.png）
2. 上传 OSS（kaelblog bucket, /wechat/ 前缀）
3. lark-cli 发送：title (--text) → body segments (--markdown, ≤880 chars/段) → cover URL (--text)
4. 验证（+chat-messages-list 确认消息顺序）

封面图模板参考 `tech-content-writer` SKILL.md 中的 HTML 模板部分。

## 系列文章规范

### 标题公式
```
数字 + 反常识/痛点 + 身份代入
```
示例：
- 「两刀砍掉多平台开发的重复劳动」
- 「两个 Package 都叫 View，编译器终于不懵了」

### 收束金句
每篇结尾统一句式，核心词不同：
```
把 {重复的事} 交给 {基础设施}，把 {X} 留给 {Y}。
```

### 系列回顾
从 Vol.03 起，文末加「系列回顾」列出前 N-1 篇标题。

### 金句示例（WWDC26 Swift 系列）
- Vol.01: 把重复的平台声明交给 anyAppleOS，把精细的警告策略留给 @diagnose
- Vol.02: 把命名冲突的消歧交给 ::，把 API 设计的清晰留给自己的命名规范
- Vol.03: 把 XCTest 和 Swift Testing 的桥梁交给互操作机制，把迁移节奏留给自己的 CI 管线
- Vol.04: 把零拷贝的安全访问交给 borrow/mutate，把性能优化的决策留给 profiler 的数据
- Vol.05: 把跨语言的边界打通交给 @C 和 Wasm，把 iOS 原生体验的核心竞争力留给自己
- Vol.06: 把编译器优化的决策权交给 @inline 和 @specialized，把「什么时候该用」的判断留给 profiler
- Vol.07: 把 for-in 循环的效率交给 Iterable，把数据容器的安全交给 UniqueBox

## Obsidian 存档

WWDC 文章最终存档到 Obsidian vault 按年份目录：

```
{vault_root}/Common/iOS/WWDC/{YEAR}/
├── WWDC{YEAR} 技术专题.md          ← 索引页（wikilink 导航 + 收束金句）
├── Vol.01 - {slug}.md
├── Vol.02 - {slug}.md
├── ...
└── Session {ID} - {slug}.md        ← 非系列独立文章
```

索引页使用 Obsidian `[[wikilink]]` 导航，按 session 分组。当内容从单一 session 扩展到多 session 时，索引页标题从「WWDC26 Swift 专题」改为「WWDC26 技术专题」并按 session 分组。

Obsidian 文件名避免 `::`、`/`、`@` 等特殊字符。如 `Vol.02 - Module Selectors.md` 而非 `Vol.02 - Module Selectors (::).md`。

用户指定的 WWDC2026 存档路径：`/Users/nowcoder/Documents/Obsidian/obsidian-nc/Common/iOS/WWDC/2026/`

## 独立 Session 文章（非系列）

内容紧凑的 session 可以写成一篇综合解读，不需要拆系列：

- 文件名：`Session {ID} - {主题关键词}.md`
- 结构：Hook → 技术栈/架构 → 核心特性逐项 → iOS 开发者视角评估 → 参考链接
- 同样需要质检（禁用词 + 字数 + 链接）

## 常见 Pitfall

- **delegate_task context 不能太短**：风格规则、禁用词、代码示例必须完整传入，子 agent 没有对话历史
- **并行写完再质检**：不要边写边检，浪费时间
- **封面图中文渲染**：HTML 模板中字体用 `'PingFang SC'` 确保中文正确渲染
- **飞书分段不按字数切**：按段落边界 `\n\n` 切分，最大 880 chars/段（900 限制留 20 安全余量）
- **--- 分隔符**：飞书会渲染为水平线破坏格式，发送前必须删除
- **用户说「继续」= 不要问确认**：写完一篇直接写下一篇，不要停顿询问
- **用户说「先发布第一篇」= 直接执行**：不要问「确认发布？」，直接走完整流程
