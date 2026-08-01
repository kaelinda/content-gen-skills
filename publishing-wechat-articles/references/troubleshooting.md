# Troubleshooting

## Preflight

Run the mode-specific JSON check first:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py preflight --mode prepare-only --title "文章标题" --json
```

- `theme_file` or `cover_template`: restore the missing repository asset; do not substitute an external path.
- `playwright_chromium`: install Playwright in the active Python runtime and install Chromium, then rerun preflight.
- `runtime_permissions`: restore `config/runtime.local.toml` to mode `0600`.
- credential or target failures: repair the private local TOML without printing its values.

## Capture

- A private, loopback, link-local, or non-HTTP(S) URL is rejected by design.
- Every redirect is revalidated. Do not disable this check to reach internal services.
- If a page needs login or client-side rendering, provide exported source text or a public structured endpoint and preserve provenance.
- Capture never uploads media. Missing image downloads do not authorize a publish operation.

## Quality And Rendering

- `title-low-score`: inspect the other title findings, revise with `retitle`, then rerun `prepare`.
- `title-body-mismatch`: make the actual subject, audience, or promised outcome visible in the title; do not insert unrelated keywords only to raise the score.
- `title-sensational`: remove unsupported superlatives, fake precision, fear-of-missing-out language, and repeated punctuation.
- A title revision invalidates prior quality, HTML, and cover outputs by design.
- YAML frontmatter delimiters are allowed only at the beginning; body horizontal rules remain blocking.
- Text inside fenced or inline code is excluded from banned-word scanning.
- Unsafe link/image schemes are removed, not rewritten.
- A short article warning may be accepted with a reason; missing headings and banned phrases are blocking.

## Cover

- Keep the repository template and use Playwright at 1200 x 540.
- If fonts or remote imports time out, remove the remote font dependency from the local template or use system fonts.
- Do not proceed to upload until the PNG exists and has been visually inspected.

## OSS And Feishu

- A returned upload URL is checkpointed before public verification, so reruns verify it instead of uploading again.
- A successful Feishu message ID is checkpointed before the tracking call, so a tracking retry does not resend the message.
- `needs-reconcile` means the remote outcome is unknown. Query OSS/Feishu manually, update the manifest only with verified evidence, then resume.
- Permission errors require fixing the configured app or destination; do not fall back to a different identity silently.
