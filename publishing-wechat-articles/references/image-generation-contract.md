# Image Generation Contract

The cover generator is an optional, paid external operation. `prepare-only` must never call it and no API key belongs in tracked files.

## Configuration

Configure `IMAGE_*` and the API key in the untracked repository-root `.env` (process environment takes priority); private `config/runtime.local.toml` remains a compatibility fallback. The existing Images API adapter accepts model `gpt-image-2` only. This is an implementation constraint, not a claim that the endpoint/model is currently available. Never print a key or raw provider response.

## Current integration boundary

`prepare` currently renders an HTML-template cover. The optional `generate_image_cover` function
is a separately authorized library API, not a wired CLI command; do not invent a `cover --commit`
command. Migration installs neither a Codex subscription adapter nor its authentication. If the
user requires AI-generated pixels or an exact named model, template preparation does not satisfy
that requirement. Configure and verify the target Agent image capability explicitly, record the
actual model evidence, and report any unavailable capability rather than silently substituting.
See `editorial-playbook.md` for cover/body-image distinctions and authentication boundaries.

## Authorization and output

A caller must explicitly opt in and authorize the cost for each generation. Do not silently fall back to another model or claim a template cover is AI-generated. Save the provider source image, cropped 1200×540 cover, prompt hash/provenance, model, transform, and a `visual_review: required` marker under the run directory. Verify the image type, dimensions, crop, text legibility, and absence of credentials before upload.

The implementation accepts the configured OpenAI-compatible endpoint and the `gpt-image-2` model only. It supports a single `b64_json` response; URL responses are fetched only over verified HTTPS from the exact configured host allowlist. DNS, response size, timeout, redirect, private-address, and credential-leak checks are enforced. Transport failures are redacted and never automatically retried because billing state may be ambiguous.

Use the repository's cover template when AI generation is not explicitly authorized. Report which path was used. A source image from an official website is a body illustration, not a self-designed cover.

All tests use synthetic provider responses and do not make paid network calls.
