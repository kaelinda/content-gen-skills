Skip to content
The core loop
Start From a blank file, through a brief, to a designed feature. Iterate Refine in place. Command line or in the browser. Polish The pre-ship gauntlet. Audit, clarify, harden. Maintain Pay down design debt before it solidifies.
↘ ↙ ↖ ↗
designing impeccable
PRODUCT.md Written by init
Platform web
Users SREs on call, reading fast, often in the dark.
Positioning Traces every alert back to the deploy that caused it.
Evidence on hand Real incident timelines. No customer logos yet.
Init scans the codebase, forms its own read of the platform and the product, and asks only what it could not work out. It writes PRODUCT.md and, if there's code to scan, offers a DESIGN.md . Every later command reads both before generating.
It does not ask about colors or type. Those get decided with the surface, not before it.
For blank-slate work, a visual reference helps more than a long prompt. Impeccable renders the chosen direction as a system board and a first-surface mock, then codes toward that image instead of a paragraph. Neo Mirai is the full loop: rolled direction, implemented page, browser iteration.
Shape
Brand toolkit. Identity, palette, type, icon language, applications, social tiles, UI direction. One plate, reviewable at a glance. Approved decisions get written into DESIGN.md . Visualize
Hi-fi reference. The destination, before the first line of CSS. The build codes toward a concrete image, not an abstract brief. That is the step change. Ship
Live build. The mock became semantic markup, regenerated assets, responsive fixes, nav state, speaker carousel behavior, and browser-verified polish. Open the live site . Which image models this uses, and what to do without one
The first two plates were generated with OpenAI GPT Image 2 ; the third is the implemented Neo Mirai page. Any harness with a built-in image tool works the same way, Codex and Gemini CLI included. Impeccable calls whatever your harness provides rather than a specific model.
No native image tool in your harness? Set OPENAI_API_KEY and Impeccable renders through gpt-image-2 instead. It says so before the first image, since it spends your own credit, roughly 5 to 25 cents each.
### When the edit has a name.
Type a command and let the skill encode a specific discipline. Best when you know the word: typography, layout, color, motion.
$ /impeccable polish pricing
$ /impeccable bolder hero
$ /impeccable typeset checkout
### When the edit is easier to point at.
Run /impeccable live in your AI tool and it drops this picker onto your running dev server. Point at any element, draw or type what you want, hit Go. Three production-quality variants; accept one and it writes back to source.
localhost:3000
No. 04
#### Letters, occasionally . Send me one
‹ 2 / 3 › ✕ Accept
Pick Insert Detect DESIGN.md When to reach for which Fix something "off" that you can't name /impeccable live Apply a specific discipline: type, layout, color, motion /typeset · /layout · /colorize · /animate Explore three directions side by side /impeccable live Ask "is this any good?" /impeccable critique Bring a safe design to life, or tone a shouting one down /bolder · /quieter
Pre-ship
audit clarify harden 03 · 04
### Score it.
Five dimensions scored 0 to 4: accessibility, performance, theming, responsive, anti-patterns. Findings tagged P0 to P3.
### Rewrite the copy.
Labels, error messages, empty-state prose, microcopy. Tuned to the audience from PRODUCT.md.
### Stress-test reality.
60-character names, German product titles, prices in the billions, 500s, offline. Production data is messy.
/impeccable extract
Subscribe Submit Join Send Go OK → Button
### Consolidate drift.
Find patterns used three or more times with the same intent. Propose tokens and primitives.
/impeccable document
01 Overview
02 Colors
03 Typography
04 Elevation
05 Components
06 Do's & Don'ts
### Re-capture the system.
Scans your tokens, components, and rendered routes, then writes a DESIGN.md in the Stitch format. The more it points at your real components and live routes, the closer Impeccable reads your design language instead of guessing at it.
Command line
### In CI, as a gate.
$ npx impeccable detect src/
Point it at a directory, a file, or a URL. Deterministic rules and JSON output, with an exit code that fails the build when slop slips into a pull request.
Chrome extension
### On any page, live.
a-competitor.com
The same checks as a browser overlay, on anything live: your staging build, a competitor, a page you'll never get into an editor.
Persuade. The visitor decides and acts: landing pages, campaigns, pricing, editorial. Design is the product here, so it has to earn attention. Distinctive type, committed palette, image-led heroes.
Issue 04 · Dispatch Shape the story.
Operate. The visitor completes a task: app UI, admin, dashboards, editors, tools. Scanability and native expectations outrank expression, and brand lives in precise details.
Users 12,482
Active now 1,207
Conversion 4.8%
Read. The visitor understands something: docs, guides, help, changelogs. Structure for comprehension first, then make the reading worth staying in. Measure, rhythm, and quiet hierarchy carry it.
Reference · Context Resolving visual authority
Experience. The visitor is inside the work itself: portfolios, galleries, showcases. The artifact leads from the first viewport and the interface recedes until it is almost gone.
01 / 24 · Untitled
- ×
Running both Impeccable and Anthropic's frontend-design skill
Anthropic's skill does get updates, just infrequent ones, so it tends to sit behind on current patterns. That is not the reason to avoid running both, though. Two skills with different design vocabularies collide and cancel each other out. Pick one.
- ×
Pinning every command
Pinning brings back /audit , /polish , /critique as shortcuts. Pin everything and you've re-exploded the / menu the v3.0 consolidation cleaned up. Pin the two or three you reach for daily.
- ×
Skipping init
Commands still run without PRODUCT.md and DESIGN.md. They default to generic SaaS patterns. The floor is meaningfully higher with context. Run init once; every later command benefits.
- ×
Treating it like a linter
Impeccable is an opinionated design partner, not a validator. It has a point of view. Push back with a reason and it'll work with you. Ignore the opinion without a reason and output gets worse, not better.
