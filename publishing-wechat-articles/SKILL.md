---
name: publishing-wechat-articles
description: Use when collecting a URL or topic, writing or revising a Chinese WeChat Official Account article, preparing its cover and HTML, handing it to Feishu, or tracking technical and parenting content.
---

# Publishing WeChat Articles

## Overview

Use the repository-local CLI as the only execution entry point. Code, templates, themes, references, account settings, and private runtime settings all live under `publishing-wechat-articles/`; the pipeline never reads an external Skill installation or credential environment variable.

## Choose A Mode

| Mode | Boundary | External writes |
|---|---|---|
| `collect-only` | Source and provenance archived locally | None |
| `prepare-only` | Markdown checked; cover and article rendered | None |
| `publish` | OSS upload, one Feishu handoff, tracking row | Requires explicit `--commit` |

Default ambiguous requests to `prepare-only`. 未经用户授权不得运行 `publish --commit`，也不得上传 OSS、发送飞书消息或写入飞书表格。

## Run The Pipeline

先运行预检 from the repository root:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py preflight \
  --mode prepare-only --title "文章标题"
```

Create a durable run, then use the returned `run_id`:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py plan \
  --mode prepare-only --title "文章标题" --summary "文章摘要" --json
python3 publishing-wechat-articles/scripts/pipeline.py capture RUN_ID "https://example.com/source" --json
```

### 可选进阶配置: 作者声音

默认流程不要求作者声音产物。只有当用户需要注入稳定的作者视角、判断和证据时，才为本次写作 Run 显式启用：

```bash
python3 publishing-wechat-articles/scripts/pipeline.py preflight \
  --mode prepare-only --title "文章标题" --author-voice --json
python3 publishing-wechat-articles/scripts/pipeline.py plan \
  --mode prepare-only --title "文章标题" --summary "文章摘要" \
  --author-voice --json
```

启用后，在写正文前读取 `references/author-voice-contract.md`，完成并导入 `author-brief.json`；正文完成后导入绑定当前正文哈希的 `voice-review.json`：

```bash
python3 publishing-wechat-articles/scripts/pipeline.py brief RUN_ID \
  --input /absolute/path/to/author-brief.input.json --json
python3 publishing-wechat-articles/scripts/pipeline.py voice-review RUN_ID \
  --input /absolute/path/to/voice-review.input.json --json
```

未使用 `--author-voice` 创建的 Run 不读取这些产物，也不增加新的准备门禁。作者声音只改变本地写作与质检，不构成发布授权。

Write the final article to `workspace/runs/RUN_ID/article.md`. Editorial writing remains the agent's responsibility; do not publish a source transcript as an original article.

`prepare` first runs 标题校验 against the completed body, then checks the article, then generates the Cover and HTML. The title must score at least 80, match正文重点, show a concrete value signal, and avoid sensational language. The result is stored in `title-quality.json`.

```bash
python3 publishing-wechat-articles/scripts/pipeline.py prepare RUN_ID --json
python3 publishing-wechat-articles/scripts/pipeline.py status RUN_ID --json
```

When title validation returns `needs_review`, revise it through the CLI and prepare again:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py retitle RUN_ID \
  --title "修订后的标题" --json
python3 publishing-wechat-articles/scripts/pipeline.py prepare RUN_ID --json
```

Only after explicit authorization, the run must have been planned with `--mode publish`:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py publish RUN_ID --commit --json
```

Use `resume RUN_ID` for local stages or `resume RUN_ID --commit` for an already authorized publish run. A `needs-reconcile` state requires manual OSS/Feishu reconciliation before any retry.

## Enforce The 10 个阶段

| Gate | Required evidence |
|---|---|
| 1. Capture | Source URL, method, raw body, image manifest |
| 2. Archive | Repository-local raw path and provenance metadata |
| 3. Write | Final `article.md`, title, summary, source attribution |
| 4. Check | `title-quality.json` score >= 80, then article report with zero blocking findings |
| 5. Cover | 1200 x 540 PNG and visual inspection |
| 6. Render | HTML using `极客黑` for `tech`, `橙心` for `parenting` |
| 7. Upload | Public cover and HTML URLs verified with expected MIME types |
| 8. Handoff | 只发送 1 条消息: title, summary, cover URL, HTML URL |
| 9. Record | Record ID and boolean `是否已发布=false` |
| 10. Publish | Explicit human/assistant confirmation; otherwise `待发布` |

Every run persists `manifest.json` with state, relative artifact paths, SHA-256 hashes, external IDs, and errors. Never infer completion of a later gate from an earlier one.

## Read Local Contracts

- Read `references/writing-contract.md` before capture and editorial work.
- Read `references/author-voice-contract.md` only after explicitly enabling `--author-voice`.
- Read `references/publishing-contract.md` before any external write.
- Use `references/resource-map.md` to locate repository assets and configuration.
- Read `references/troubleshooting.md` after a failed stage.

## Report Completion

Report content, local assets, upload, handoff, tracking, and WeChat confirmation separately. Never print or copy values from `config/runtime.local.toml`. Handoff is not publication; report `已发布` only with explicit confirmation.

## Common Mistakes

- Creating a `prepare-only` run and later treating it as publish authorization.
- Sending article chunks instead of the single link handoff.
- Retrying an ambiguous timeout and creating duplicate messages or rows.
- Marking the tracking checkbox true at handoff.
- Treating an attractive title as permission to use clickbait, unsupported superlatives, or repeated exclamation marks.
- Editing `manifest.json` by hand after title failure instead of using `retitle`.
- Changing the title without regenerating the cover.
- Executing scripts under `vendor/hermes/`; they are reference snapshots, not runtime entry points.
