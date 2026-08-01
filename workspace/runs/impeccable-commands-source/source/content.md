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
- 01 Install npx impeccable install Run from the project root, then reload your agent.
- 02 Set context /impeccable init Create PRODUCT.md and DESIGN.md.
- 03 Try it /impeccable polish the pricing page Point it at a real page.
Full walkthrough: Getting started .
Start a project /impeccable init Polish a page /impeccable polish Find design issues /impeccable critique Check implementation /impeccable audit Iterate in the browser /impeccable live Build a new surface /impeccable <describe it>
Design Context PRODUCT.md + DESIGN.md New work Direction for new surfaces Detector CLI npx impeccable detect Design hooks /impeccable hooks Doctor /impeccable doctor Config and ignores .impeccable/config.json
## Iterate in the browser
Pick UI, generate variants, accept one into source.
Live Mode docs
localhost:4321
Hero headline
Variant 2 of 3
Prev 2 / 3 Next Accept
- Plan /impeccable shape Think before you build. Produce a design brief through discovery, not guesswork.
- Review /impeccable critique A design review with scoring, persona tests, and automated detection.
- Refine /impeccable polish The meticulous final pass between good and great.
- Iterate /impeccable live Iterate on UI in the browser. Pick an element, drop a comment, get three variants. Accept one and it writes to source.
Already shipped? Use /impeccable polish on the page that needs work, or /impeccable audit for checks.
bolder ↔ quieter
Two halves of voice. Loud or restrained, never neutral.
audit → harden
Find the technical issues. Then fix them.
critique → polish
Review the work. Then refine it.
init → shape
Capture the product. Then plan the surface.
Create 2
- impeccable Get a next-step recommendation, or describe design work in plain English.
- shape Think before you build. Produce a design brief through discovery, not guesswork.
Evaluate 2
- audit Five-dimension technical quality check with P0 to P3 severity.
- critique A design review with scoring, persona tests, and automated detection.
Refine 8
- animate Purposeful motion that conveys state, not decoration.
- bolder Push safe designs toward impact without sliding into chaos.
- colorize Add strategic color to monochrome interfaces without going garish.
- delight Small moments of personality that turn functional into memorable.
- layout Fix layout, spacing, and visual rhythm.
- overdrive Push an interface past conventional limits. Shaders, physics, 60fps, cinematic transitions.
- quieter Tone down designs that are shouting without losing their intent.
- typeset Fix typography that feels generic, inconsistent, or accidental.
Simplify 3
- adapt Make designs work across screens, devices, and contexts without amputating features.
- clarify Rewrite confusing UX copy so interfaces explain themselves.
- distill Ruthless subtraction. Strip designs to their essence.
Harden 4
- harden Make interfaces production-ready. Edge cases, i18n, error states, overflow.
- onboard Design first-run experiences, empty states, and paths to value.
- optimize Diagnose and fix UI performance from LCP to bundle size.
- polish The meticulous final pass between good and great.
System 3
- document Generate a spec-compliant DESIGN.md that captures your visual system so every AI agent stays on-brand.
- extract Pull reusable components, tokens, and patterns into the design system.
- live Iterate on UI in the browser. Pick an element, drop a comment, get three variants. Accept one and it writes to source.
