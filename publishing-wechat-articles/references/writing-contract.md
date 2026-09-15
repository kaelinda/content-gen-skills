# Writing Contract

## 给好朋友准备礼物：写作与终审

把读者当成一位具体的好朋友，把文章当成认真准备的礼物。围绕他的真实问题组织内容，删掉只为凑字数、显得丰富或制造热闹的材料；宁可短一点、范围窄一点，也不要交出准备不足的内容。这是质量要求，不是让文章套上煽情口吻。

写前阅读 `selection-research-contract.md`，完成读者价值、官网主动检索和关键事实来源记录。写作采用“直觉解释 → 必要原理 → 场景与取舍 → 可执行动作 → 边界”，不堆砌 API、README、会议纪要。代码仅在确实有助于读者时提供；未运行须标示例/未实测，不虚构作者经历。第一人称判断可以使用，第一人称经验必须有真实证据。

正式交付前逐项人工审核并写入 run 的 `editorial-review.md`：

- **准确**：版本、参数、数字、链接与来源逐一对应；事实与分析分清，未核验处明确标注。
- **有用**：读者能做出一个决定、完成一个操作或避开一个坑；不是只有“产品有什么”。
- **增量**：有场景、比较、判断、验收清单或真实经验，不能靠换说法伪装原创。
- **风险**：成本、认证、权限、地区、兼容性、安全、预览状态及专业领域风险没有被省略。
- **交付**：标题承诺与正文相符，图片与章节相关，代码和链接可用，移动端可读。
- **礼物检查**：是否愿意推荐给那位朋友？哪个准备不足之处仍会浪费他的时间？有则修改或暂缓，不能用自动格式检查通过掩盖它。

审核结论使用通过/修改/拒绝，列明依据。自动检查只能发现部分问题，不能证明事实可靠、图片可读或公众号排版正确。

## Capture And Provenance

1. Capture public HTTP(S) sources through the unified pipeline command.
2. Save source URL, final URL, timestamp, capture method, raw body, image metadata, and checksums.
3. Treat X/Twitter and other partially rendered pages as incomplete when their captured body lacks the claimed content; obtain a public structured source or ask for authenticated source text.
4. For a topic, collect official sources plus reputable secondary sources and record each URL.
5. Never upload captured images during capture or preparation.

Never claim a source says something that was inferred. Mark inference and verify material technical or parenting claims against authoritative sources.

## Article Quality

- Identify the reader, concrete problem, incremental value, and why the source alone is insufficient.
- Add judgment, comparisons, pitfalls, examples, or an actionable path. Do not publish a translation or long paraphrase as original work.
- Use `##` for sections and `###` for subsections; do not emulate headings with bold text.
- Do not repeat the title at the start. Body horizontal rules are forbidden; YAML frontmatter delimiters at the beginning are allowed.
- Default long-form target is 3000–4000 Chinese characters, with content-based exceptions. 用户要求精简时取消最低字数，短篇干货可用完整代码加最少解释；不限字数时按内容需要展开。不得凑字数或虚构经历扩写。
- Preserve source links through the safe renderer.
- Distinguish repeated topics by version, title, cover, content hash, and incremental value.

## Account Voice

| Account | Voice | Theme | Local vault |
|---|---|---|---|
| `tech` | AICoder: practical, precise, code and tradeoffs | `极客黑` | `workspace/vaults/tech` |
| `parenting` | Warm, specific, evidence-aware, actionable | `橙心` | `workspace/vaults/parenting` |

Do not mix parenting language into a technical article or technical-brand assumptions into a parenting article.

The table above is the default account-level voice. For an optional author-voice run created with `plan --author-voice`, use the run-local `voice-context.json` and follow `references/author-voice-contract.md`. Create and ingest `author-brief.json` before drafting, then ingest a passing `voice-review.json` after the body is complete. This advanced workflow is not required for normal runs.

## Title, Summary, And Cover

- Produce three title candidates, then select one final title before rendering.
- Run the selected title through the title quality gate after the body is complete and before any cover or article HTML is rendered.
- Keep the summary factual and self-contained for the Feishu handoff.
- Use the repository cover templates by default at 1200 x 540 logical pixels. 用户指定 `gpt-image-2` 时按 `image-generation-contract.md` 配置调用，不能偷偷替换模型或将模板封面谎称为生成结果。
- 官方账号或机构内容的标题突出来源与具体收益，但禁止虚构量化承诺、最高级或效果保证。
- 正文优先采用官网真正解释机制、流程或界面的图片，记录来源/使用限制，下载到项目 workspace；不要把仓库 OG 预览图冒充架构图。图片映射到具体章节，使用描述性 alt 并解释读者应该看哪里。
- 封面由自己设计，不能拿原文插图顶替；复杂流程、决策、对比的正文需要解释性插图，封面不能替代它。无合适官方图时记录缺口，征得需要的生成授权或提供明确标注的示意图，不为凑数加装饰。
- 准备阶段保留本地图片；发布阶段由项目上传器上传 OSS 并重写 HTML 引用。检查每张图的可访问性、MIME、实际渲染和移动端可读性；视觉工具不可用时如实保留人工检查项。
- Visually inspect clipped Chinese text, fonts, contrast, and stale title text.
- A title change invalidates the previous cover.

### Title quality gate

The deterministic gate scores the title from 0 to 100 and requires at least `80`:

| Dimension | Expected behavior |
|---|---|
| Length | Hard range 6-64 visible characters; recommended range 12-32 |
| Focus | 标题与正文关键词有可验证的呼应，避免题文错位 |
| Value | 包含问题、收益、方法、范围等明确的价值信号 |
| Restraint | 不使用夸张词、虚假比例、无依据最高级或过量问号/感叹号 |
| Specificity | 避免“关于……的一些思考”“聊聊……”等空泛表达 |

The report is written to `title-quality.json`. A blocking finding moves the run to `needs_review` before HTML or cover generation. Revise through:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py retitle RUN_ID \
  --title "修订后的标题" --json
python3 publishing-wechat-articles/scripts/pipeline.py prepare RUN_ID --json
```

Do not bypass a low score by editing the report or manifest. When a title changes, previously derived quality, HTML, and cover artifacts are invalidated and must be regenerated.

## Blocking Checks

Run preparation after placing the final Markdown in the run directory:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py prepare RUN_ID --json
```

Publication is blocked by title score below 80, sensational title findings, banned phrases outside code, missing real `##` sections, body horizontal rules, unsafe resource URLs, missing or invalid cover output, absent source attribution, or material unverified claims. Character-count findings are warnings when a content-based exception is documented.
