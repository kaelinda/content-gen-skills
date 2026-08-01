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
npx impeccable detect runs Impeccable’s deterministic design checks directly from the terminal. Use it when you want a fast signal without asking an AI command to review the work.
## Fast path
Scan the source folder: npx impeccable detect src/
Scan one file: npx impeccable detect src/components/Card.tsx
Scan a rendered page: npx impeccable detect https://example.com
Use JSON when another script or CI job needs to read the result: npx impeccable detect --json src/
## What it checks
The detector looks for design and implementation patterns that are usually visible to users: contrast problems, typography drift, layout overflow, generic AI-design tells, brittle motion, and design-system violations when DESIGN.md exists.
Directories are walked for design-relevant files. HTML files include linked local CSS. Framework files such as JSX, TSX, Vue, Svelte, Astro, and CSS modules get source-text checks. URL targets use a browser and inspect the rendered page.
Server-side templates are covered too, once you name their extensions. Add them under detector.extensions in .impeccable/config.json and Blade, ERB, Twig, or Handlebars files get the same checks as JSX. See Config and ignores .
Web only. The engine reads HTML and CSS, so it has nothing to say about a native iOS or Android codebase. On a project whose PRODUCT.md declares ios , android , or adaptive , use /impeccable audit , which runs a native pass covering VoiceOver, TalkBack, touch targets, and platform conformance instead.
## How to read results
Plain output groups findings by file and prints the rule id, snippet, and explanation. Exit codes are: Code Meaning 0 No findings. 2 Findings were detected. 1 The command failed.
That makes CI usage straightforward: fail the job on 2 , then decide whether to fix the issue or add a narrow ignore.
## DESIGN.md awareness
When a local DESIGN.md exists, detect loads it by default and enables design-system checks for fonts, literal colors, border radii, and literal font sizes documented in the typography ramp. The generated .impeccable/design.json sidecar gives those checks richer token and ramp data.
If the design file is stale, refresh it: /impeccable document
If you need one scan without design-system checks: npx impeccable detect --no-design-system src/
To narrow a scan to one design domain (for example before a typeset or layout pass): npx impeccable detect --scope type src/ npx impeccable detect --scope layout src/
## Managing intentional findings
Detector ignores are shared with the design hook: npx impeccable ignores list npx impeccable ignores add-value overused-font Inter --reason " Brand font " npx impeccable ignores add-file " src/legacy/** "
For a waiver that should travel with one file instead of living in the repo config, drop an inline comment in the file itself: <!-- impeccable-disable overused-font: exported brand doc -->
Use Config and ignores for the full ignore workflow, including the line-scoped impeccable-disable-line and impeccable-disable-next-line forms.
## Details when the default path is not enough Scan stdin
If you pipe text into the command with no target, it scans stdin: cat component.css | npx impeccable detect Project config and raw scans
By default, detect reads .impeccable/config.json and .impeccable/config.local.json .
It respects detector.ignoreRules , detector.ignoreFiles , detector.ignoreValues , and detector.designSystem.enabled .
It does not respect hook.enabled ; manual scans still run when the automatic hook is disabled.
In-file impeccable-disable* comments are honored too, so a waiver can travel with a file. --no-inline-ignores skips just those; --no-config skips config and inline ignores together.
Use --no-config only when you want a raw detector run with no project config, no detector ignores, and no DESIGN.md context. Where the detector fits
The same detector also powers the design hook, /impeccable audit , the public slop catalog , the browser extension, and the local detector lab.
Use Design hooks when you want findings inside the agent flow. Use detect when you want a direct terminal signal.
