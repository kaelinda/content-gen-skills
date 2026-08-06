# Author Voice Contract

This is an optional advanced workflow. Use it only when the run was created with `plan --author-voice`. A normal run does not require `voice-context.json`, `author-brief.json`, or `voice-review.json`.

## Before Drafting

1. Read the run-local `voice-context.json`. Never load another account's voice overlay or vault.
2. Separate source facts, author judgment, inference, and personal experience.
3. Write an author brief with the reader problem, source baseline, incremental value, thesis, tension, reasoning moves, counterpoint, excluded directions, and three title candidates.
4. Personal experience is optional. When used, every personal claim must reference an ID in `workspace/vaults/<account>/voice/evidence.toml`.
5. Ingest the brief through the canonical CLI:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py brief RUN_ID \
  --input /absolute/path/to/author-brief.input.json --json
```

Do not edit `manifest.json` or copy evidence content into `voice-context.json`.

## Drafting Priority

Draft in this order:

1. Attention: what this author notices that the source or common treatment misses.
2. Judgment: what the author accepts, rejects, or limits.
3. Reasoning: how evidence leads to the conclusion and where it stops.
4. Evidence: concrete facts, tradeoffs, examples, and attributable experience.
5. Language: rhythm and metaphor serve the argument; they do not perform a persona.

Do not invent biography, force first-person anecdotes, or add verbal tics to simulate individuality.

## After Drafting

Review the completed `article.md` across `attention`, `judgment`, `reasoning`, `evidence`, and `language`. Every dimension must cite an exact excerpt from the current article. Mark a paragraph as anonymous when another author could publish it unchanged after replacing the topic nouns.

A passing review requires all five dimensions to be present, no blockers, and no anonymous paragraphs. Otherwise use `decision=revise` and revise the article before preparing.

```bash
python3 publishing-wechat-articles/scripts/pipeline.py voice-review RUN_ID \
  --input /absolute/path/to/voice-review.input.json --json
python3 publishing-wechat-articles/scripts/pipeline.py prepare RUN_ID --json
```

Changing `article.md` invalidates the previous review. Re-run `voice-review`; never repair its hash or the manifest by hand.

## Quality Interpretation

For an author-voice run, generic-language matches are editorial warnings rather than proof of AI authorship. Structural errors, title failures, unsafe resources, unsupported evidence, and a missing, failed, or stale voice review still block preparation.

This workflow performs local file writes only. It does not authorize OSS upload, Feishu handoff, tracking writes, or publication.
