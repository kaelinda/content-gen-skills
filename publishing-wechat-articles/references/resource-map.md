# Repository Resource Map

All paths are relative to the repository root. The canonical entry point is `publishing-wechat-articles/scripts/pipeline.py`.

## Runtime

| Capability | Repository path |
|---|---|
| Account routing and local settings | `publishing-wechat-articles/config/accounts.toml` |
| Safe runtime defaults | `publishing-wechat-articles/config/runtime.example.toml` |
| Private publish credentials | `publishing-wechat-articles/config/runtime.local.toml` |
| Capture | `publishing-wechat-articles/scripts/wechat_pipeline/capture.py` |
| Title quality | `publishing-wechat-articles/scripts/wechat_pipeline/title_quality.py` |
| Quality checks | `publishing-wechat-articles/scripts/wechat_pipeline/quality.py` |
| Markdown rendering | `publishing-wechat-articles/scripts/wechat_pipeline/render.py` |
| Cover rendering | `publishing-wechat-articles/scripts/wechat_pipeline/cover.py` |
| Durable state | `publishing-wechat-articles/scripts/wechat_pipeline/manifest.py` |
| Optional author voice | `publishing-wechat-articles/scripts/wechat_pipeline/voice.py` |
| Orchestration | `publishing-wechat-articles/scripts/wechat_pipeline/orchestrator.py` |
| OSS and Feishu | `publishing-wechat-articles/scripts/wechat_pipeline/oss.py`, `feishu.py`, `publish.py` |

Collect and prepare modes fall back to the checked-in `runtime.example.toml`, so a clean clone can run without credentials or environment variables. For publishing, create `runtime.local.toml` from the example; it must remain ignored and mode `0600`. Do not include any of its values in commands, logs, generated artifacts, or responses.

## Assets

| Need | Repository path |
|---|---|
| Parameterized covers | `publishing-wechat-articles/assets/covers/` |
| Original theme CSS | `publishing-wechat-articles/vendor/hermes/md-to-html/references/mdnice-themes/` |
| Original cover collection | `publishing-wechat-articles/vendor/hermes/wechat-cover-html/templates/` |
| Original writing references | `publishing-wechat-articles/vendor/hermes/content-collector/references/` |
| Original technical references | `publishing-wechat-articles/vendor/hermes/tech-content-writer/references/` |

The `vendor/hermes/` tree is a copied, redacted source snapshot. Runtime code must not import or execute its legacy scripts; some preserve historical unsafe behavior for traceability.

## Local Storage

- Runs: `workspace/runs/<run_id>/`
- Technical vault: `workspace/vaults/tech/`
- Parenting vault: `workspace/vaults/parenting/`
- Optional voice evidence: `workspace/vaults/<account>/voice/evidence.toml` plus repository-local relative evidence files
- Each run owns its raw source, article Markdown, quality report, cover, HTML, and `manifest.json`.

Runs created with `plan --author-voice` additionally own `voice-context.json`, `author-brief.json`, and `voice-review.json`. Checked-in defaults live in `publishing-wechat-articles/config/voice/`; the context snapshot never contains private evidence bodies.

The entire `workspace/` directory is local operational state and is ignored by version control.

## Required Machine Runtime

- Python 3.11+
- Playwright Python package with Chromium for PNG cover rendering
- Network access only for capture or an explicitly authorized publish

Feishu and OSS calls use Python's verified TLS stack and credentials from the private repository-local TOML file. No separate command-line client is required.
