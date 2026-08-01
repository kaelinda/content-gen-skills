Skip to content
Browse docs
Learn
Tutorials
- Getting started
- Iterate on UI with Live Mode
- Critique with the visual overlay
Reference
Core concepts
- Design Context
- Config and ignores
- New work
Automation
- Detector CLI
- Design hooks
- Doctor
Commands
Create
- impeccable
- shape
Evaluate
- audit
- critique
Refine
- animate
- bolder
- colorize
- delight
- layout
- overdrive
- quieter
- typeset
Simplify
- adapt
- clarify
- distill
Harden
- harden
- onboard
- optimize
- polish
System
- document
- extract
- init
- live
The design hook runs Impeccable’s detector automatically when an AI coding tool edits UI files. It catches regressions while the agent still has the edit in context.
## Fast path
Check hook state inside your AI tool: /impeccable hooks status
Turn the hook on or off for this project: /impeccable hooks on /impeccable hooks off
Installer and updater commands can skip hook setup for one run: npx impeccable install --no-hooks npx impeccable update --no-hooks
## What it does
The hook scans direct edits to UI code and styles. When it finds a new issue, it sends the agent a short reminder with the finding and a fix direction.
Claude Code, GitHub Copilot, and Codex run after the edit. Cursor checks proposed writes before they land and blocks only when the detector finds an issue in the proposed UI code.
Plain .ts and .js files are scanned, but the hook stays quiet unless it finds something design-relevant.
### Two speeds
The hook does not report everything on every edit. You get two passes instead:
- Per edit: only what is objectively broken or compounds if ignored. Broken images, overflowing and clipped text, contrast failures, tiny text, gradient text, glow, and drift from your own DESIGN.md .
- At the end of the session: the full rule set across every UI file you touched, minus anything already reported. Why it is split, and how to turn the split off
Reporting every rule on every edit made models measurably more conservative rather than more careful. One copy-level rule alone fired about ninety-seven times in a single session, and the findings that get fixed well (contrast, padding, glow) are the ones judged against a finished page, not a half-written one.
The deep pass fires once per session; a second stop is silent, because its findings are remembered.
Set hook: { "perEditRules": "all" } in .impeccable/config.json to get every rule on every edit again. Cursor and GitHub Copilot are exempt from the split, since they have no end-of-session pass wired and nothing should be deferred into a pass that never runs.
Web only. The hook parses HTML and CSS, so it does not run on a project whose PRODUCT.md declares ios , android , or adaptive . See Design Context .
### Checking it is really running
A hook can look installed and scan nothing: if its script path stops resolving, after a move or a reinstall, the manifest still registers and no findings ever arrive. Silence reads as a clean codebase.
/impeccable doctor checks for exactly that, along with a manifest that says enabled while config says otherwise. Worth running once after you move a project.
## Handling intentional findings
Persist an exception only after you confirm the finding is intentional. Prefer the narrowest exception: /impeccable hooks ignore-value overused-font Inter --shared --reason "Brand font" /impeccable hooks ignore-file "src/legacy/Card.tsx" /impeccable hooks ignore-rule side-tab
For value-specific rules such as overused-font , use ignore-value for a specific font. Use ignore-rule overused-font --all-values only when you want to suppress the entire rule.
The terminal equivalent is npx impeccable ignores ... , which writes the same detector config. See Config and ignores .
## Details when the default path is not enough Supported harnesses and approval steps
npx impeccable install and npx impeccable update install provider-native hook manifests for Claude Code, GitHub Copilot, Codex, and Cursor.
- Claude Code: .claude/settings.local.json by default.
- GitHub Copilot: .github/hooks/impeccable.json , a committed file shared by the Copilot CLI and the cloud agent.
- Codex: .codex/hooks.json .
- Cursor: .cursor/hooks.json .
GitHub Copilot reads the committed .github/hooks/impeccable.json . In the Copilot CLI the hook activates once that file is on the repository's default branch and you trust the folder; the cloud agent reads it straight from the repo.
Codex requires one extra approval step. After install or update, open /hooks in Codex and approve the project hook. Codex tracks trust by hook definition, so updates can require approval again.
Cursor users should also confirm hooks are enabled in Cursor Settings -> Hooks. Scanned file types
The hook scans common UI and style files:
.tsx , .jsx , .html , .vue , .svelte , .astro , .css , .scss , .sass , .less , .ts , and .js . Config and environment overrides
Hook lifecycle settings live under hook in .impeccable/config.json : { "hook": { "enabled": true, "quiet": false, "auditLog": ".impeccable/hook.ndjson" } }
Per-developer choices, including install consent, live in .impeccable/config.local.json .
Detector filters live under detector , not hook , because they are shared by the hook and the CLI detector.
Environment variables still override config for one shell: IMPECCABLE_HOOK_DISABLED , IMPECCABLE_HOOK_QUIET , and IMPECCABLE_HOOK_LOG . Debugging hook behavior
Start with status: /impeccable hooks status
It shows the shared and local config paths, current ignores, hook state, and relevant environment overrides.
For invocation logs, set hook.auditLog or use IMPECCABLE_HOOK_LOG . The hook writes one NDJSON line per invocation. Leave audit logging off for normal work.
If a manifest is malformed, install/update aborts by default. Re-run with --force only when you want Impeccable to back up the malformed file as .bak and replace it.
