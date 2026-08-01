# AIGC 二次创作 fact-check checklist

**触发场景**：扩写、改写、翻译英文推文/Article 为中文技术公众号文章时。

**核心原则**：可以加观点、加个人案例、加"为什么"分析，**但不能改原文的技术数据**。

## 必查清单（发布前 5 分钟过一遍）

### 1. 技术栈 / 工具名核对

最容易出错的字段。把原文里所有出现的「语言名 / 框架名 / 工具名 / 文件名 / API 名」逐个核对。

**2026-06-15 实测 bug**：原文说「Bun 是用 Zig 写的，有人把 Bun 移植到 Rust」。扩写时为了"差异化"说"移植到 C"。事实是 **Rust**。`tech-content-writer` 在「❗ AIGC 二次创作必须 fact-check」pitfall 已记录。

**对策**：
- 抓取后立即建一张「原文关键事实」表（语言 / 数字 / 人名 / 引文 / 链接）
- 扩写时**只能**加观点 / 加分析 / 加个人案例，**不改**这张表
- 发布前再核对一次

### 2. 数字 / 百分比 / 版本号

| 类型 | 容易出错的点 | 对策 |
|---|---|---|
| 百分比 | 99.8% vs 99% vs 100% | 直接读原文复制 |
| 行数 / 文件数 | 750K vs 75K | 同上 |
| 时间 / 天数 | 11 天 vs 6 天（原推文两个数字都有）| 两个都保留或加注 |
| 版本号 | v2.1.139 vs v2.1.154 | 一字不差 |
| 计数器 | 16 并发 / 1000 agents | 核对原推 |

### 3. 人名 / 机构名

- 拼写正确：Anthropic、DeepMind、Akshay Pachaar、Thomas Ricouard、Samuel McDonnell
- 头衔正确：「Claude Code 创始人」vs「Claude Code 负责人」—— 看原文用哪个
- 双重身份区分：「Bun 作者 Jarred Sumner」vs「Bun 维护者」

### 4. 引文 / 原话

直接引用必须一字不差（含标点、语气词）。如果中文表达需要意译：
- 用「原文是」/「作者原话」开头
- 在引号里给英文原文（即使主要文章是中文）
- 意译单独写，**不**和原文混在一起

### 5. 链接 / 引用源

- 论文 arXiv 编号：2606.12683（DeepMind From AGI to ASI）/ 2210.03629（ReAct）/ 2303.11381（Reflexion）
- 官方文档：https://code.claude.com/docs / https://developers.openai.com/codex
- **发布前用 curl HEAD 验证每个外链 HTTP 200**

### 6. 边界事实

- "**没**说过" vs "**说过**"：原文是否真的有这观点
- "**第一次**" vs "**第二次**"：是初版还是修订
- "**已经**" vs "**即将**"：当前态 vs 未来态
- "**内部**" vs "**外部**"：原文是 internal 还是 public 来源

## fact-check 工作流（发布前 3 分钟）

```bash
# 1. 列出原文所有"硬事实"（一次性固化，避免扩写时漂移）
cat > /tmp/facts.txt <<'EOF'
# 技术栈
- Bun: Zig → Rust
- Codex Mobile: 6 个核心模式
- Claude Code: /goal v2.1.139, dynamic workflows v2.1.154

# 数字
- Bun port: 750K 行, 99.8% 测试通过
- 11 天 from first commit to merge (Anthropic); 6 天 (Sumner)
- 16 并发 / 1000 agents per run

# 人名
- Thomas Ricouard @Dimillian
- Samuel McDonnell @samueljmcd
- Akshay Pachaar @akshay_pachaar
EOF

# 2. 扩写时把这张表当作"不可修改"清单
# 3. 发布前再 diff 一遍：grep -E "Zig|Rust|99\.8|750K" article.md
```

## 扩写时容易引入的事实漂移模式

| 漂移类型 | 例子 | 修复 |
|---|---|---|
| **技术栈改名** | "Bun 移植到 C" → 实际是 Rust | 引用原文片段 |
| **数字改大/改小** | "99% 通过" → 实际是 99.8% | 严格按原文 |
| **人名错位** | 把推主 A 的观点说成推主 B 的 | 标清楚归属 |
| **时间错位** | "上周"→ 实际是上个月 | 原文日期+1 周内表述 |
| **顺序错位** | 把 2024 的事说成 2025 | 核对时间线 |
| **观点加强** | "loop 是好东西" → "loop 是终极答案" | 只能微调语气，不能改立场 |

## 对应 pitfall

`tech-content-writer` SKILL.md 的 Pitfalls 节：
- **❗ AIGC 二次创作必须 fact-check，不能"为了差异化"瞎编细节**（2026-06-15 实测）

## 对应 system prompt 强化

`tech-content-writer` SKILL.md 的 DeepSeek System Prompt 已加：

```
## 核心要求
- 正文第一行不带标题（标题通过其他方式传递）
- 技术表述必须准确，不臆测
- **AIGC 二次创作 fact-check**：所有技术细节（语言/数字/人名/引文）必须忠于原文，
  不能"为了差异化"改写技术数据。可以加观点/个人案例，但不能改事实。
```
