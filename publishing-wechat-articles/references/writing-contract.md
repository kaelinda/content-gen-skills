# Writing Contract

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
- Target 3000-4000 Chinese characters; 2500-4500 is acceptable when justified.
- Preserve source links through the safe renderer.
- Distinguish repeated topics by version, title, cover, content hash, and incremental value.

## Account Voice

| Account | Voice | Theme | Local vault |
|---|---|---|---|
| `tech` | AICoder: practical, precise, code and tradeoffs | `极客黑` | `workspace/vaults/tech` |
| `parenting` | Warm, specific, evidence-aware, actionable | `橙心` | `workspace/vaults/parenting` |

Do not mix parenting language into a technical article or technical-brand assumptions into a parenting article.

## Title, Summary, And Cover

- Produce three title candidates, then select one final title before rendering.
- Run the selected title through the title quality gate after the body is complete and before any cover or article HTML is rendered.
- Keep the summary factual and self-contained for the Feishu handoff.
- Use the repository cover templates and render at 1200 x 540 logical pixels.
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
