# Image Generation Providers in Hermes

When the publishing flow needs a cover image (step 2 of the main SKILL.md), you can either:
- (A) Render an HTML cover via Playwright/Chrome (most control, recommended for code-rich tech covers)
- (B) Use Hermes's `image_generate` tool, which dispatches to a configured `image_gen.provider`

This file documents option (B) — provider discovery, configuration, and a real evaluation
of a third-party candidate (`codex-image` by Leon) that turns out to NOT WORK on current
Codex CLI. Read this before installing any new provider.

## Provider discovery and structure

Provider plugins live in `~/.hermes/hermes-agent/plugins/image_gen/<name>/`:

```
image_gen/
├── fal/              plugin.yaml + __init__.py
├── krea/             plugin.yaml + __init__.py
├── openai/           plugin.yaml + __init__.py
├── openai-codex/     plugin.yaml + __init__.py   ← built-in, recommended for free
├── xai/              plugin.yaml + __init__.py
└── codex-image/      plugin.yaml + __init__.py   ← see evaluation below
```

Each provider implements a subclass of `agent.image_gen_provider.ImageGenProvider`
with these methods:

- `name` / `display_name` — the public id and the human label shown in setup
- `is_available()` — return True if the dependencies/credentials are present
- `list_models()` — return list of model metadata dicts
- `capabilities()` — declare `{"modalities": [...], "max_reference_images": N}`
- `generate(prompt, aspect_ratio, **kwargs)` — return a typed response dict
  - use `success_response(image=path, model=..., provider=..., ...)` on success
  - use `error_response(error=..., error_type=..., provider=..., ...)` on failure

Activation is done in `~/.hermes/config.yaml`:

```yaml
image_gen:
  provider: <name>   # must match a provider's .name property
```

Then `hermes gateway restart` (note: on macOS 26+, `launchctl bootstrap` fails with
exit 5; Hermes falls back to spawning a background process — this is expected).

## Built-in providers (as of 2026-06-23)

| Provider | Cost | Strengths | Auth | Caveats |
|---|---|---|---|---|
| `fal` | per-image | Multi-model, fast | `FAL_KEY` env | Pay-per-image |
| `krea` | subscription | Creative models | `KREA_API_KEY` | Subscription |
| `openai` | per-image | gpt-image-1 | `OPENAI_API_KEY` | Pay-per-image |
| **`openai-codex`** | **free (Plus)** | **gpt-image-2 via Codex OAuth** | **`hermes auth codex`** | **text-to-image only (no editing)** |
| `xai` | per-image | Grok image | `XAI_API_KEY` | Pay-per-image |

`openai-codex` is the right default for users with ChatGPT Plus — it reads the Codex
OAuth token from `agent.auxiliary_client._read_codex_access_token()`, calls the Codex
Responses API directly (`https://chatgpt.com/backend-api/codex/responses`) with
`tool_choice` forced to `image_generation`, and saves the b64-decoded PNG to
`$HERMES_HOME/cache/images/`. Streaming is done via raw SSE parsing (no SDK
dependency) so it tolerates event-shape changes from ChatGPT's backend.

## ❌ codex-image (Leon-llb) — do NOT install for actual use

A third-party candidate at https://github.com/Leon-llb/codex-image claims to give
"free image generation via Codex CLI, no API key, no token, just Plus sub." The
README is plausible and the code is clean. But the core assumption is **wrong on
the current Codex CLI** and the project does not work.

### What the project does

A two-layer bridge:
1. `generate.py` shells out to `codex exec "<prompt>" --skip-git-repo-check`,
   then uses a **before/after file diff** against `~/.codex/generated_images/`
   to identify the newly written image (codex exec doesn't tell you the output path).
2. `hermes-plugin/__init__.py` is a thin `ImageGenProvider` that calls `generate.py`
   and parses a `SUCCESS:<path>` line from stdout.

### Why it fails on current Codex CLI (≥ 0.141)

**`codex exec` is a code agent, not an image generator.** It does not have an
image-generation tool. When you ask it for an image, it tries to improvise —
typically by writing an SVG file by hand and admitting:

> Note: the raster image generation tool was not available in this session, so
> I made a clean SVG image file locally instead.

So `codex exec` exits 0, but **no `.png` lands in `~/.codex/generated_images/`**.
The diff algorithm in `generate.py` finds zero new images and raises
`"No new image found"`, which surfaces as `error_type: api_error` from the provider.

`codex --version` on this machine reports `codex-cli 0.141.0` and `0.142.0` —
both too new for Leon's project (last release v1.1.0 was May 2026, against
an older Codex CLI that did ship an image tool).

### What to use instead

If you want a free image provider backed by ChatGPT Plus, **use the built-in
`openai-codex` provider**. It does not depend on `codex exec` at all — it
calls the Codex Responses API directly with a forced `image_generation` tool,
which is a stable surface because ChatGPT's backend controls it.

```yaml
# ~/.hermes/config.yaml
image_gen:
  provider: openai-codex
```

Then `hermes auth codex` (if not already authenticated) and
`hermes gateway restart`.

**⚠️ 2026-06-23 — openai-codex also broken on current backend.**
The plugin's `_build_responses_payload()` uses
`tool_choice: {type: allowed_tools, tools: [{type: image_generation}]}`,
but the Codex Responses API now rejects this with
`HTTP 400: Tool choice 'image_generation' not found in 'tools' parameter`.
The `tools[]` array IS defined with `type: image_generation`; the rejection
is on the `tool_choice.allowed_tools.tools[]` sub-shape. So as of
2026-06-23, **no ChatGPT-Plus-routed image provider works** in this
Hermes install — both third-party `codex-image` (Codex CLI no longer
ships image tool) and built-in `openai-codex` (tool_choice protocol drift)
fail. Practical workarounds for cover images: render via Playwright/Chrome
(HTML option A in the main SKILL.md) or use a paid provider (`fal`, `openai`, `xai`).

### If you still want to install codex-image (for learning only)

The project is worth reading as an example of the two-layer bridge pattern
and the file-diff output-location trick. If you install it, the patched
plugin lives at `~/.hermes/hermes-agent/plugins/image_gen/codex-image/`
with these improvements over Leon's upstream:

- Resolves `generate.py` from the plugin's own bundled copy first, then
  falls back to `~/.claude/skills/codex-image/`, then `CODEX_IMAGE_SCRIPT` env var
- Resolves the `codex` binary via `shutil.which("codex")` first, then macOS
  Codex.app path, then Windows path — no hardcoded `/usr/local/bin/codex` fallback
- Declares `capabilities() -> {"modalities": ["text", "image"], ...}` so the
  model knows `--image` mode is supported

But the core image generation will still fail. Activate it only if you want
to read the code and observe the failure pattern — **do not use it for real
cover generation**.

## What to do in this session

If the user asks to install a third-party image provider:

1. Read the provider's `image_generate` / `generate.py` code end-to-end first.
2. Check the actual `codex exec <prompt>` behavior on this machine (NOT what
   the README claims) — `codex --version` and a 30s `timeout 30 codex exec "test"`
   is enough to learn if it's a code agent or a multi-tool CLI.
3. Cross-check the built-in `openai-codex` provider — it is almost always the
   better answer for "free image generation via ChatGPT Plus."

## YAML config append footgun

When appending `image_gen:` to `~/.hermes/config.yaml`, **always check first**:

```python
if "image_gen:" in text:
    # patch the existing block, do not append
else:
    # safe to append
```

`config.yaml` is a single file shared by all of Hermes; a duplicate `image_gen:`
key silently takes the last-wins value and confuses debugging.
