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
Impeccable stores runtime settings under .impeccable/ . Most users do not need to hand-edit those files. Use the CLI when you want to record a confirmed exception.
Use config for:
- detector ignores shared by npx impeccable detect and the design hook;
- private local ignores that should not be committed;
- hook lifecycle settings such as enabled, quiet mode, and audit logging;
- project roots, for repos where design boundaries are not declared by a package manager.
Use PRODUCT.md and DESIGN.md for product and design intent. See Design Context .
## The usual path
List the current ignores: npx impeccable ignores list
Add the narrowest exception that matches the real reason: npx impeccable ignores add-value design-system-color " #ff00aa " --reason " Campaign accent " npx impeccable ignores add-file " src/legacy/** " npx impeccable ignores add-rule side-tab
Remove an exception when the underlying code is fixed: npx impeccable ignores remove-value design-system-color " #ff00aa "
The same detector config is used by the CLI and the hook, so an ignore behaves consistently in both places.
A config file fails quietly when it is wrong: a misspelled key is simply never read, an ignored rule id that no longer exists suppresses nothing, and a projectRoots glob that matches no directory leaves the repo root standing in for the app you meant. /impeccable doctor checks for all three. It also reads "stalenessCheck": false here, which turns off the session-start staleness notice.
## Shared or local
Default ignores go into .impeccable/config.json . Commit them when they represent team intent: a legacy folder, a confirmed brand exception, or a project-wide rule decision.
Use --local for private work: npx impeccable ignores add-file " src/private-experiment/** " --local
Local settings go into .impeccable/config.local.json , which Impeccable keeps out of git.
## Project Roots
Impeccable normally finds nested projects through package-manager workspace declarations: package.json workspaces, pnpm-workspace.yaml , or lerna.json . When those files do not exist, or when design boundaries do not line up with packages, declare the roots directly: { " projectRoots " : [ " docs/design/skins/* " ] }
Each matched folder becomes its own project: it can carry its own PRODUCT.md and DESIGN.md , it appears in the app picker, and it falls back to the repo root per file for any context it does not define. See Design Context . How the patterns resolve against package workspaces
- Patterns are relative to the repo root and use the same glob syntax as package.json workspaces, including * , ** , and ! negation.
- projectRoots in config.local.json extends the shared list, so one developer can add private roots without committing them.
- A path matched by any projectRoots pattern, positive or negated, is governed by this config alone. Package-manager workspaces apply only to paths these patterns do not match, and each source's ! negations apply only to its own patterns. So "!apps/internal" here hides a package workspace from Impeccable, while a package-level negation never hides a folder that projectRoots declares.
## Value ignores
Prefer value ignores when a rule reports a specific value: npx impeccable ignores add-value overused-font Inter --reason " Brand font "
Fonts, colors, radii, and motion values should usually be suppressed by value, not by whole rule. That keeps the rule useful everywhere else.
Wildcard value ignores are allowed only when scoped to a file: npx impeccable ignores add-value design-system-color " * " --file " src/demo.css "
That keeps one intentionally experimental file from teaching the whole project that every undocumented color is acceptable.
## Inline ignore comments
Config ignores live in .impeccable/config.json , which is the right home for repo-wide policy. They do not follow a file out of the repo, though. When a waiver belongs to one file and needs to travel with it (a generated or exported standalone document, an emailed HTML file, a snippet scanned out of context), put the waiver in the file itself: <!-- impeccable-disable overused-font: exported brand doc, font is first-party -->
The marker works in any comment syntax, and three scopes are available: /* impeccable-disable overused-font */ /* whole file */ . brand { font-family : Inter } /* impeccable-disable-line overused-font */ /* impeccable-disable-next-line bounce-easing */ Syntax details and per-file behavior
The directive is comment-syntax-agnostic: the same marker works in // , /* */ , <!-- --> , # , and {/* */} comments across HTML, CSS, JSX, TSX, Vue, and Svelte.
List one or more rule ids, comma-separated, or omit them (or use * ) for every rule. A reason after : or -- is optional and recommended; it is for the diff, and the scanner discards it.
Static HTML findings have no line number, so only whole-file impeccable-disable applies to them. That is the standalone-document case this exists for. The line-scoped forms apply to CSS, JSX, TSX, Vue, and Svelte, where findings carry a line.
Inline directives apply by default. --no-inline-ignores turns them off for one run while keeping config ignores; --no-config turns off config and inline ignores together.
## Details when the default path is not enough What the config file looks like
The shared config lives at .impeccable/config.json . A typical file looks like this: { "detector": { "ignoreRules": [], "ignoreFiles": [], "ignoreValues": [], "designSystem": { "enabled": true } }, "hook": { "enabled": true, "quiet": false, "auditLog": ".impeccable/hook.ndjson" } }
The detector section is shared by manual scans and hooks. The hook section only controls automatic hook execution and hook output. Disable design-system checks
Design-aware rules run when DESIGN.md exists. Disable them for the project only when the design file is intentionally not authoritative yet: { "detector": { "designSystem": { "enabled": false } } }
For one manual run, keep config but skip the design-system rules: npx impeccable detect --no-design-system src/
Use --no-config only when you want a raw scan with no project ignores and no DESIGN.md context. Hook runtime settings
Use /impeccable hooks for normal lifecycle changes: /impeccable hooks status /impeccable hooks on /impeccable hooks off
hook.quiet: true suppresses clean and pending acknowledgements while still surfacing new findings.
hook.auditLog writes one NDJSON line per hook invocation for debugging. Leave it off during normal work.
Environment variables still override config for one shell: IMPECCABLE_HOOK_DISABLED , IMPECCABLE_HOOK_QUIET , and IMPECCABLE_HOOK_LOG .
