# Image Generation Contract

The cover generator is an optional, paid external operation. `prepare-only` must never call it and no API key belongs in tracked files.

## Configuration

Copy `config/runtime.example.toml` to the untracked `config/runtime.local.toml`, set `[image_generation] enabled = true`, the HTTPS endpoint, model `gpt-image-2`, a local API key, timeout, and exact download allowlist. Runtime configuration is loaded only from this repository. Never print the key or provider response.

## Authorization and output

A caller must explicitly opt in and authorize the cost for each generation. Do not silently fall back to another model or claim a template cover is AI-generated. Save the provider source image, cropped 1200×540 cover, prompt hash/provenance, model, transform, and a `visual_review: required` marker under the run directory. Verify the image type, dimensions, crop, text legibility, and absence of credentials before upload.

The implementation accepts the configured OpenAI-compatible endpoint and the `gpt-image-2` model only. It supports a single `b64_json` response; URL responses are fetched only over verified HTTPS from the exact configured host allowlist. DNS, response size, timeout, redirect, private-address, and credential-leak checks are enforced. Transport failures are redacted and never automatically retried because billing state may be ambiguous.

Use the repository's cover template when AI generation is not explicitly authorized. Report which path was used. A source image from an official website is a body illustration, not a self-designed cover.

All tests use synthetic provider responses and do not make paid network calls.
