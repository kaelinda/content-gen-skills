# Content Pipeline Architecture & Series Tracking

## Purpose

When the user asks "what articles have we written?" or "which ones are systematic?", this reference provides the search strategy and known inventory so you don't do blind multi-directory searches.

## Storage Locations (4 directories)

```
~/Documents/Obsidian/
├── obsidian-nc/Common/
│   ├── X-Content/
│   │   ├── raw-resource/     ← 原始收录（抓取的原始素材，50+ 篇）
│   │   └── content/          ← 加工成品（编号 001-034，含中英双语）
│   ├── raw/articles/         ← 带 YAML frontmatter 的新收录
│   └── iOS/WWDC/2026/        ← WWDC 专题文章（Vol.01-07 + 综合长文）
│
└── TechnologyHub/            ← LLM Wiki 知识库
    ├── concepts/             ← 概念页（53 个，含 12 个 2026-06-14 批量创建）
    ├── outputs/              ← 加工后的可发布文章（20 篇）
    ├── raw/articles/         ← 带 frontmatter 的原始收录
    └── index.md              ← 全局索引（117 pages）
```

## Series Identification Strategy

Articles are tagged by `series:` in YAML frontmatter. Known series:

| Series Name | Tag in frontmatter | Location |
|---|---|---|
| Agent 工程化系列 | `series: Agent 工程化系列` | TechnologyHub/outputs/ |
| Claude 生态实战 | `series: Claude 生态实战` | TechnologyHub/outputs/ |
| 技术精选 | `series: 技术精选` | TechnologyHub/outputs/ |
| 技术公众号 | `series: 技术公众号` | TechnologyHub/outputs/ |
| WWDC26 Swift 专题 | Vol.01-07 numbering in filename | obsidian-nc/Common/iOS/WWDC/2026/ |

## Quick Search Commands

When user asks about series completeness:

```python
# 1. Find all articles with series tag
search_files(pattern="series:", path="<outputs_dir>", file_glob="*.md")

# 2. Find by Vol. numbering
search_files(pattern="Vol\.", path="<vault_root>", file_glob="*.md")

# 3. Check TechnologyHub index for full inventory
read_file(path="TechnologyHub/index.md")
```

## Known Inventory (as of 2026-06-14)

### Agent 工程化系列 (confirmed in outputs/)

| Date | File | Title |
|---|---|---|
| 2026-06-04 | eric-debug-mode-runtime-context | 别让 agent 再猜了：Cursor Debug Mode 把「看」这件事教给了它 |
| 2026-06-04 | hermes-ecosystem-plugins-vol08 | 给 agent 装上「灵魂」：Hermes 周围正在长出 6 个开源 plugin |
| 2026-06-10 | loop-engineering-anthropic | 别再雕 prompt 了：Anthropic 工程师用 3 层循环让 agent 自己变强 |

**Memory says Vol.06-13 exist** but only 3 are confirmed with explicit `series: Agent 工程化系列` tag. The remaining volumes may:
- Have been written in earlier sessions not indexed by session_search
- Use a different series tag or no tag
- Exist in a location not yet searched (e.g., hermes-agent docs repo, or deleted)

**Action when user asks about this series**: Check outputs/ first, then search all directories for "工程化" or "Vol" patterns. If still incomplete, ask user to confirm the full list.

### WWDC26 Swift 专题 (Vol.01-07)

| Vol. | Topic | Session |
|---|---|---|
| 01 | anyAppleOS + @diagnose | 262 |
| 02 | Module Selectors (::) | 262 |
| 03 | Swift Testing 互操作 | 262 |
| 04 | borrow / mutate / Ref | 262 |
| 05 | @C + Wasm + Swift-Java | 262 |
| 06 | @inline + @specialized | 262 |
| 07 | Iterable + UniqueBox | 262 |

Plus综合长文: `WWDC2026 技术全景.md` (covers Session 262/269/310/232)

### TechnologyHub Concepts (12 Agent-related, 2026-06-14 batch)

1. agent-loop-engineering (5 sources)
2. agent-harness-engineering (6 sources)
3. claude-code-dynamic-workflows (4 sources)
4. claude-skills-prompt-mastery (6 sources)
5. multi-agent-team-orchestration (2 sources)
6. agent-memory-knowledge-systems (4 sources)
7. agents-md-context-files (3 sources)
8. ai-agent-fundamentals (5 sources)
9. codex-ecosystem (4 sources)
10. google-gemini-antigravity (3 sources)
11. ai-business-monetization (4 sources)
12. ai-research-infrastructure (4 sources)

## Pitfalls

- **Don't assume all articles are in one place.** Content is spread across 4+ directories. Always search multiple paths.
- **Series tag is the source of truth, not filename.** Some files have "vol08" in the name but may not have a `series:` frontmatter field.
- **session_search has limited depth.** Very early sessions (before 2026-06-06) may not be retrievable. If you can't find a known series, ask the user.
- **TechnologyHub/index.md is the best single source.** It has 117 pages indexed with descriptions. Read it first when doing content inventory.
- **The user's memory says Vol.06-13 for Agent 工程化.** Trust the memory but verify against actual files. If there's a gap, surface it honestly rather than guessing.
