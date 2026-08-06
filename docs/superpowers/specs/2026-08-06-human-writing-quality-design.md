# 公众号文章去 AI 味质检设计

## 背景

当前 `publishing-wechat-articles` 已在 `writing-contract.md` 约束原创性、篇幅、标题和来源，并由 `quality.py` 阻断少量固定套话。它能拦住明显禁词，但不能发现更常见的模型化形状，例如材料不足却反复解释、段落只换说法不推进、句长过齐、短段排队、连接词密集和抽象名词堆叠。

本次设计参考 [`KKKKhazix/human-writing`](https://github.com/KKKKhazix/human-writing) v1.1.0，核验基线为提交 `4fda173f3fef7fb808f3eba991eeb2528ea4b189`，许可证为 MIT。只吸收适合公众号非虚构写作的方法与检测思路，不引入上游运行时，不执行上游脚本，也不复制其完整通用写作规则。

## 目标

1. 让文章先靠材料、判断和段落推进获得“活人感”，而不是靠口头禅、错别字或网络梗伪装。
2. 对确定性高的 AI 模板腔继续阻断 `prepare`。
3. 对依赖语境的统计信号只发出警告，避免误伤技术文章和正常中文表达。
4. 保持 `pipeline.py` 为唯一入口，保持 `quality.json`、发布授权和账号路由向后兼容。

## 非目标

- 不安装或调用独立的 `human-writing` Skill。
- 不覆盖小说、诗歌、剧本等虚构写作规则。
- 不引入模型打分、第三方 API 或联网质检。
- 不以检测器分数代替编辑判断，也不承诺检测器能证明文章由人类撰写。
- 不改变标题质量门禁、封面渲染、OSS、飞书或发布状态机。

## 方案选择

### 方案 A：只加强提示词

仅扩写 `writing-contract.md`。改动最小，但回归无法稳定检测，后续模型容易重新出现相同模板。

### 方案 B：本地分级质检

写作前约束材料和说话位置，初稿后执行独立复稿清单，再由本地检测器输出硬错误和软警告。它能覆盖判断性工作与机械检查，同时不增加外部依赖。

### 方案 C：直接引入上游 Skill 和脚本

规则覆盖最广，但会形成第二套入口、第二套规则更新和相互冲突的禁令，不符合仓库的单一 canonical Skill 约束。

采用方案 B。

## 写作流程

### 1. 动笔前建立材料底座

`writing-contract.md` 增加以下内部检查，不把检查笔记直接交给读者：

- 明确读者、作者的说话位置、核心判断及判断边界。
- 计划写成长篇非虚构文章时，至少列出五项能核验的具体材料，包括事实、数字、流程、原话、失败、代价或结果；同一抽象观点的不同说法只算一项。
- 材料不足时优先补充公开来源。仍不足时缩小主题或缩短篇幅，不用假案例、假亲历和装饰性细节凑字数。
- 技术文章保持 AICoder 的实用、精确和权衡语气；育儿文章保持温和、具体、证据清楚的语气。

### 2. 初稿按信息推进

- 开头尽快碰到真实问题、动作、数据或反常事实，不预告全文结构。
- 每个主要段落必须增加新事实、新动作、新例子、新区别、新限制或新后果。
- 判断的依据放在附近；推测、官方自述和已核验事实保持不同口径。
- 允许长短段变化和自然重复，不按固定节奏制造金句。
- 事情讲完就结束，不重复摘要或突然上升到时代、文明和未来。

### 3. 初稿后单独复稿

新增 `references/human-writing-review.md`，并要求只在初稿完成后读取。复稿顺序固定为：

1. 找出“换一个模型也能原样写”的匿名段落，补材料、取舍或作者判断；没有内容可补就删。
2. 标记每段新增的信息，合并只做同义改写的段落。
3. 删除无来源的精确时间、天气、神态、对白等假具体。
4. 把名词化表达还原成谁做了什么，以及钱、时间、责任和后果落在哪里。
5. 清理翻案腔、模型路标、商业黑话和空泛结尾。
6. 冷读全文，确认作者凭什么知道、哪句话超过材料、文章在哪一句已经结束。

## 确定性质检

### 输入处理

检测对象为 Markdown 正文。保留标题和小标题的自然语言检查，忽略 YAML frontmatter、围栏代码和行内代码。现有渲染后 `<h2>` 检查保持不变。

### 阻断项

以下 finding 使用 `severity=error`，任何一项都会令 `prepare` 进入 `needs_review`：

| Code | 行为 |
|---|---|
| `banned-word` | 保留现有明确禁用表达，并覆盖“并非 A 而是 B”“不在于 A 而在于 B”“看似 A 实则 B”“你以为 A 其实 B”等明确翻案模板 |
| `ai-road-sign` | 阻断“更微妙的是”“还有一层”“真正的问题是”“先说结论”等用来给段落抬价的固定路标 |
| `hard-jargon` | 阻断“赋能”“抓手”“价值闭环”“认知跃迁”“组合拳”等不能提供具体信息的商业或模型黑话 |
| 现有结构错误 | 保持正文水平线、缺少真实 `##`、渲染缺少 `<h2>` 等现有错误语义 |

硬规则采用窄匹配。不能仅因出现“其实”“可能”“方法论”等单词就阻断；只有确定的固定句式或绝对禁词才进入 error。

### 警告项

以下 finding 使用 `severity=warning`，写入 `quality.json`，但不阻断渲染：

| Code | 默认触发条件 |
|---|---|
| `nominalized-action` | 命中“进行了……”“实现了……的提升”“完成了对……”等名词化动作 |
| `conjunction-density` | 正文不少于 600 个汉字，连接词超过每千字 7 个 |
| `uniform-sentence-length` | 至少 12 个有效句子，句长变异系数低于 0.42 |
| `single-sentence-paragraphs` | 至少 10 个正文段落，其中单句段占比不低于 75% |
| `short-paragraph-streak` | 连续 4 个不超过 24 个汉字的单句段 |
| `repeated-opener` | 同一种段落开场词出现至少 4 次 |
| `highlight-density` | `「」` 或 `『』` 中的短语超过 `max(3, 汉字数 // 700)` |
| `metaphor-cluster` | 800 字窗口内出现至少 3 套互不相干的借喻语义场 |

阈值沿用上游已公开的启发式基线，作为首版默认值。每条 finding 把实际数量、阈值或样例放入 `details`，方便编辑定位。警告不能自动升级为错误。

## 数据流和兼容性

```text
article.md
  -> title quality gate
  -> render Markdown
  -> check_article(markdown, rendered_html)
       -> hard findings: needs_review + stop
       -> warning findings only: checked -> rendered
  -> quality.json
```

`QualityReport.to_dict()` 继续输出 `passed`、`chinese_characters` 和 `findings`。不新增顶层必填字段；统计值写入现有 `Finding.details`。`passed` 仍只由 error 决定，因此现有调用方不需要修改。

## 文件变更

| 文件 | 变更 |
|---|---|
| `publishing-wechat-articles/SKILL.md` | 增加材料检查、初稿后复稿和分级质检说明 |
| `publishing-wechat-articles/references/writing-contract.md` | 增加非虚构材料底座、说话位置和段落推进规则 |
| `publishing-wechat-articles/references/human-writing-review.md` | 新增初稿后的人工复稿流程、硬规则说明和来源声明 |
| `publishing-wechat-articles/scripts/wechat_pipeline/quality.py` | 增加窄匹配硬规则与统计性 warning 检查 |
| `tests/test_quality.py` | 覆盖每类硬错误、警告、阈值和代码屏蔽 |
| `tests/test_orchestrator.py` | 证明纯 warning 仍能完成本地渲染，error 会进入 `needs_review` |
| `tests/test_skill_contract.py` | 约束新参考文件和 SKILL 加载时机 |

`agents/openai.yaml` 的触发范围没有变化，无需更新。

## 错误处理

- 发现 error 时仍写出 `quality.json`，保存具体 finding，再把 run 转为 `needs_review`。
- 只有 warning 时正常生成 HTML 和封面；最终报告必须明确还有哪些内容需要人工判断。
- 检测器遇到短文、句子或段落样本不足时跳过对应统计规则，不把样本不足当成异常。
- 正则与统计函数保持纯函数，不执行网络请求，不读取运行配置，不触碰外部系统。

## 测试策略

实现遵循 Red-Green-Refactor：先增加会因缺少新 finding 而失败的测试，确认失败原因，再写最小实现。

### 单元测试

- 明确翻案句、模型路标和绝对黑话分别产生 error。
- 普通语境中的“其实”“可能”“方法论”不产生 error。
- 名词化、连接词密度、整齐句长、单句段比例、连续短段、重复开场、括号金句和借喻簇分别产生 warning。
- warning 不出现在 `report.blocking`，且 `report.passed` 为 true。
- 围栏代码和行内代码中的示例不触发正文 finding。
- 短样本不触发依赖统计量的 warning。

### 集成测试

- 只含 warning 的文章经过 `Pipeline.prepare(..., render_png=False)` 后进入 `rendered`，并在 `quality.json` 保留 warning。
- 含 error 的文章进入 `needs_review`，不生成封面产物。
- 现有标题质量门禁仍先于文章渲染执行。

### 完整验收

```bash
python3 -m unittest discover -s tests -v
python3 /Users/nowcoder/Documents/MyCode/services/Skill/skill-hub/skills/.system/skill-creator/scripts/quick_validate.py publishing-wechat-articles
python3 publishing-wechat-articles/scripts/pipeline.py --help
git diff --check
```

## 验收标准

1. 所有明确 AI 模板与绝对黑话被阻断并可定位。
2. 所有统计性启发式只警告，不改变 `passed=true` 和 `rendered` 状态。
3. 正常技术术语、代码示例和短文章不因宽泛正则被误阻断。
4. `quality.json` 顶层结构不变，现有测试与新增测试全部通过。
5. Skill 明确要求先靠材料和信息推进写作，再在初稿后加载复稿规则。
6. 整个改造不产生任何 OSS、飞书或其他外部写入。
