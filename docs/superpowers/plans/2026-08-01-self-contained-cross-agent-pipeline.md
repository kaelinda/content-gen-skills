# Self-Contained Cross-Agent WeChat Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository run the complete WeChat preparation and publishing workflow without reading external Hermes files, while exposing the same Skill and CLI to Codex and Claude Code.

**Architecture:** Keep `publishing-wechat-articles/SKILL.md` as the agent-facing workflow, vendor the required Hermes scripts/themes/templates/references into the Skill, and add a repository-local Python package that fixes and orchestrates them. Account profiles, a private local runtime config, security policy, run manifests, OSS and Feishu clients all live inside the repository. Agent runtimes share the canonical Skill through project-local discovery links.

**Tech Stack:** Python 3.11 standard library, vendored Hermes resources, Playwright Python runtime for PNG cover rendering, TOML configuration, `unittest`, Aliyun OSS and Feishu/lark-cli adapters.

---

### Task 1: Define self-contained contracts

**Files:**
- Create: `publishing-wechat-articles/config/accounts.toml`
- Create: `publishing-wechat-articles/config/runtime.local.toml` with mode `0600`
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/config.py`
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/models.py`
- Test: `tests/test_config.py`

- [ ] Write failing tests proving tech and parenting profiles load from the repository, contain no absolute external skill paths, and route explicit/keyword accounts consistently.
- [ ] Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_config.py` and confirm imports or profiles are missing.
- [ ] Implement immutable `AccountProfile`, `RepositoryConfig`, and TOML loading with CLI/env/profile precedence.
- [ ] Store themes, local vault defaults, and non-secret identifiers in `accounts.toml`; load credentials only from the ignored repository-local `runtime.local.toml`, never from environment variables.
- [ ] Rerun the focused test and confirm it passes.

### Task 2: Enforce trust-boundary security

**Files:**
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/security.py`
- Test: `tests/test_security.py`

- [ ] Write failing tests that reject `file:`, loopback, private/link-local IPs, unsafe redirects, path traversal, event-handler HTML, and `javascript:`/`data:` links.
- [ ] Run the focused tests and confirm the security module is missing.
- [ ] Implement HTTP/HTTPS-only URL policy with DNS/IP checks, redirect revalidation, slug normalization, rooted-path checks, output size limits, and URL scheme sanitization.
- [ ] Keep TLS verification enabled and support a custom CA only through `SSL_CERT_FILE` or the standard SSL context.
- [ ] Rerun the focused tests and confirm all attack inputs are blocked.

### Task 3: Vendor capture, quality, rendering, and cover assets

**Files:**
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/capture.py`
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/quality.py`
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/render.py`
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/cover.py`
- Create: `publishing-wechat-articles/vendor/hermes/`
- Create: `publishing-wechat-articles/assets/themes/geek-dark.css`
- Create: `publishing-wechat-articles/assets/themes/orange-heart.css`
- Create: `publishing-wechat-articles/assets/covers/tech.html`
- Create: `publishing-wechat-articles/assets/covers/parenting.html`
- Test: `tests/test_capture.py`
- Test: `tests/test_quality.py`
- Test: `tests/test_render.py`
- Test: `tests/test_cover.py`

- [ ] Write failing tests for safe public capture parsing, no implicit upload, complete banned-word checks, frontmatter-aware horizontal-rule checks, escaped Markdown rendering, safe link/image schemes, and escaped cover fields.
- [ ] Run focused tests and confirm missing modules/assets fail.
- [ ] Copy the required Hermes Skill runtime files into `vendor/hermes`, remove embedded credentials, and verify no runtime path points back to `~/.hermes`.
- [ ] Wrap the vendored capture and fxtwitter logic with verified HTTPS and bounded downloads; archive source text and image metadata without upload.
- [ ] Implement quality reports with blocking/warning findings and machine-readable output.
- [ ] Implement the repository-local Markdown renderer and two inline themes without loading Hermes theme catalogs.
- [ ] Implement cover HTML generation and Playwright PNG rendering from repository templates.
- [ ] Rerun focused tests and confirm deterministic artifacts.

### Task 4: Add durable run manifests and resumable orchestration

**Files:**
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/manifest.py`
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/orchestrator.py`
- Test: `tests/test_manifest.py`
- Test: `tests/test_orchestrator.py`

- [ ] Write failing tests for state transitions, atomic manifest writes, artifact hashes, prepare-only zero external writes, restart/resume, and invalid transition rejection.
- [ ] Run focused tests and confirm missing state machinery fails.
- [ ] Implement versioned `manifest.json` with `run_id`, authorization mode, current state, artifact hashes, external IDs, errors, and timestamps.
- [ ] Implement `plan`, `capture`, `prepare`, `status`, and resumable stage execution.
- [ ] Require a final article Markdown file before `prepare`; agent runtimes remain responsible for editorial writing.
- [ ] Rerun focused tests and confirm a local run survives process restart.

### Task 5: Implement secure, idempotent publishing adapters

**Files:**
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/oss.py`
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/feishu.py`
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/publish.py`
- Test: `tests/test_publish.py`

- [ ] Write failing fake-adapter tests proving content-hash OSS keys, one Feishu handoff, boolean tracking state, checkpointing after each external success, and no duplicate calls on resume.
- [ ] Run focused tests and confirm adapters are missing.
- [ ] Implement verified-TLS OSS PUT signing with credentials read only from `config/runtime.local.toml`.
- [ ] Implement Feishu/lark-cli clients using identifiers and credentials read only from repository-local configuration.
- [ ] Implement fail-closed `publish --commit`; persist each returned URL/message ID/record ID before the next side effect.
- [ ] Treat ambiguous timeouts as `needs-reconcile` instead of blind retries.
- [ ] Rerun focused tests with fake transports; do not call live OSS or Feishu.

### Task 6: Expose one CLI and strict preflight

**Files:**
- Create: `publishing-wechat-articles/scripts/pipeline.py`
- Replace: `publishing-wechat-articles/scripts/preflight.py`
- Test: `tests/test_cli.py`
- Modify: `tests/test_skill_contract.py`

- [ ] Write failing CLI tests for `preflight`, `plan`, `capture`, `prepare`, `status`, `publish`, and `resume` help and exit codes.
- [ ] Prove preflight fails when a required internal asset, Playwright capability, account identifier, or credential is unavailable for the selected mode.
- [ ] Implement CLI commands over repository-local modules only.
- [ ] Add `--json` output and redact all credential values.
- [ ] Scan source and tests for `~/.hermes`, hardcoded credentials, `CERT_NONE`, `shell=True`, and unsafe URL schemes.
- [ ] Rerun the full suite.

### Task 7: Support Codex and Claude Code from the same repository

**Files:**
- Create: `AGENTS.md`
- Create: `CLAUDE.md`
- Create link: `.agents/skills/publishing-wechat-articles`
- Create link: `.claude/skills/publishing-wechat-articles`
- Modify: `publishing-wechat-articles/SKILL.md`
- Modify: `publishing-wechat-articles/references/resource-map.md`
- Test: `tests/test_agent_discovery.py`

- [ ] Write failing tests proving both project-local discovery paths resolve to the canonical Skill and both root instruction files invoke the same CLI.
- [ ] Create relative discovery links without duplicating Skill content.
- [ ] Rewrite Skill commands and references so every runtime dependency resolves inside the repository.
- [ ] Keep `agents/openai.yaml` for Codex UI metadata; use standards-compliant `SKILL.md` for both runtimes.
- [ ] Rerun discovery and Skill validation tests.

### Task 8: End-to-end dry-run acceptance

**Files:**
- Create: `tests/fixtures/source.html`
- Create: `tests/fixtures/article.md`
- Create: `tests/test_e2e.py`

- [ ] Write an end-to-end fixture test that creates a run, captures local fixture content through an injected transport, prepares themed HTML and cover HTML, records hashes, and publishes through fake OSS/Feishu adapters.
- [ ] Verify exactly one handoff and one tracking record are produced.
- [ ] Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` and require zero failures.
- [ ] Run Skill `quick_validate.py` and require `Skill is valid!`.
- [ ] Run repository scans for external file dependencies and secret patterns; require zero active-code matches.
- [ ] Run `preflight --mode prepare-only` and a fixture `plan -> prepare -> status` smoke test without live external writes.

The directory is not currently a Git repository, so commit steps are intentionally omitted. Once repository ownership is established, initialize or attach it to Git before making this pipeline the production source of truth.
