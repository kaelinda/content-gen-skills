# Balanced Human Writing Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the repository-local WeChat writing Skill so articles rely on concrete material and natural progression, while deterministic AI templates block preparation and contextual style signals remain non-blocking warnings.

**Architecture:** Keep `publishing-wechat-articles/SKILL.md` and `scripts/pipeline.py` as the only workflow and runtime entry points. Put editorial judgment in a pre-draft writing contract and a post-draft review reference, then extend the pure `check_article()` function with narrow hard-pattern groups and deterministic prose-shape warnings. Preserve the existing `QualityReport` JSON shape and let its current `passed = not blocking` behavior carry warning-only articles through the existing orchestrator.

**Tech Stack:** Python 3.11 standard library (`re`, `statistics`, `collections`), Markdown reference files, `unittest`, repository-local Skill validation.

---

## File Map

- Modify `publishing-wechat-articles/SKILL.md`: declare the material gate, post-draft review timing, and balanced error/warning behavior.
- Modify `publishing-wechat-articles/references/writing-contract.md`: define the non-fiction material floor, speaker position, paragraph progression, and account voice constraints.
- Create `publishing-wechat-articles/references/human-writing-review.md`: hold the post-draft editorial review and upstream attribution without bloating `SKILL.md`.
- Modify `publishing-wechat-articles/scripts/wechat_pipeline/quality.py`: detect hard templates and contextual prose-shape warnings while preserving `QualityReport`.
- Modify `tests/test_skill_contract.py`: make the new editorial contract and progressive loading testable.
- Modify `tests/test_quality.py`: drive hard and soft quality behavior through focused unit tests.
- Modify `tests/test_orchestrator.py`: prove errors stop preparation and warning-only reports still render.

No changes are planned for `orchestrator.py`, `models.py`, `pipeline.py`, publishing adapters, configuration, themes, or `agents/openai.yaml`.

### Task 1: Add the staged editorial contract

**Files:**
- Modify: `tests/test_skill_contract.py:14-56`
- Modify: `publishing-wechat-articles/SKILL.md:39-86`
- Modify: `publishing-wechat-articles/references/writing-contract.md:13-30`
- Create: `publishing-wechat-articles/references/human-writing-review.md`

- [ ] **Step 1: Record a skill-behavior baseline with a fresh agent**

Use a fresh agent that can see the current Skill but not this design or plan. Give it this task exactly:

```text
Use $publishing-wechat-articles at /Users/nowcoder/Documents/MyCode/services/content-gen-skills/publishing-wechat-articles to write a 2500-Chinese-character WeChat article. The only source material is: voice input is convenient; recordings preserve state; AI search can retrieve old recordings. Do not research and do not ask questions. Produce the article immediately. Do not publish or perform any external write.
```

Record the raw response in the execution thread. RED is confirmed if the agent produces a long article by expanding or repeating those three abstract points, invents a user/example/scene, or treats the requested length as stronger than the available material. If it already narrows or shortens the article without fabrication, record that result and retain the contract test below as the deterministic RED surface; do not invent a failure claim.

- [ ] **Step 2: Add failing contract tests**

Add `references/human-writing-review.md` to `required` in `test_required_skill_files_exist`, then add this test to `SkillContractTest`:

```python
    def test_human_writing_review_is_loaded_only_after_the_draft(self):
        skill_text = (SKILL / "SKILL.md").read_text()
        writing_text = (SKILL / "references/writing-contract.md").read_text()
        review_text = (SKILL / "references/human-writing-review.md").read_text()

        self.assertIn("至少五项", writing_text)
        self.assertIn("每个主要段落", writing_text)
        self.assertIn("材料不足", writing_text)
        self.assertIn("初稿完成后", skill_text)
        self.assertIn("human-writing-review.md", skill_text)
        self.assertLess(skill_text.index("writing-contract.md"), skill_text.index("human-writing-review.md"))
        self.assertIn("quality warnings", skill_text)
        self.assertIn("hard error", review_text)
        self.assertIn("warning", review_text)
        self.assertIn("4fda173f3fef7fb808f3eba991eeb2528ea4b189", review_text)
        self.assertIn("MIT", review_text)
```

- [ ] **Step 3: Run the contract tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_skill_contract.SkillContractTest.test_required_skill_files_exist tests.test_skill_contract.SkillContractTest.test_human_writing_review_is_loaded_only_after_the_draft -v
```

Expected: FAIL because `references/human-writing-review.md` does not exist and the new phrases are absent.

- [ ] **Step 4: Add the staged workflow to `SKILL.md`**

Immediately after the paragraph that assigns editorial writing to the agent, add:

```markdown
Before drafting a long non-fiction article, apply the material gate in `references/writing-contract.md`: establish the speaker position and list at least five concrete, traceable materials. If the source cannot support the requested length, research, narrow the topic, or shorten the article instead of inventing examples or repeating the same point.

After the first draft is complete, read `references/human-writing-review.md` and revise the article before running `prepare`. Do not load the detailed revision checklist before drafting. `prepare` treats narrow AI templates and absolute jargon as blocking errors; prose-shape heuristics remain warnings that require editorial judgment.
```

Under `## Read Local Contracts`, replace the writing bullet with these two bullets, preserving the existing publishing, resource-map, and troubleshooting bullets:

```markdown
- Read `references/writing-contract.md` before capture and editorial work.
- Read `references/human-writing-review.md` only after the first draft is complete and before `prepare`.
```

Replace the first sentence under `## Report Completion` with:

```markdown
Report blocking checks and remaining quality warnings, then report content, local assets, upload, handoff, tracking, and WeChat confirmation separately.
```

- [ ] **Step 5: Add the material and progression rules to `writing-contract.md`**

Insert this section before `## Account Voice`:

```markdown
## Material, Speaker, And Progression

Before drafting a long non-fiction article, identify the reader, the speaker's position, the central judgment, and the limit of that judgment. Internally list at least five concrete, traceable materials such as a fact, number, workflow, quotation, failure, cost, constraint, or later result. Rewording one abstract idea does not create another material.

When fewer than five materials are available, research public sources first. If the material is still thin, narrow the topic or shorten the article. Never invent a personal experience, representative user, exact scene, quotation, weather detail, or emotional reaction to fill the requested length.

Start with a real problem, action, number, or surprising fact instead of previewing the article structure. Each major paragraph must add a fact, action, example, distinction, limitation, or consequence. Merge or delete paragraphs that only restate an earlier point. Put evidence close to judgment, mark inference as inference, and stop when the subject is complete instead of repeating the summary or forcing a grand conclusion.
```

- [ ] **Step 6: Create the post-draft review reference**

Create `publishing-wechat-articles/references/human-writing-review.md` with this complete content:

```markdown
# Human Writing Review

Read this file only after the first draft is complete. Preserve useful facts, decisions, examples, and natural phrasing before removing model-like shapes.

## Review Order

1. Identify who is speaking, how that person knows the subject, what they care about, and where their judgment stops.
2. Label the new information in every paragraph. Merge or delete a paragraph that only paraphrases an earlier point.
3. Remove unsupported exact times, weather, expressions, rooms, dialogue, and other decorative details. In non-fiction, specificity without provenance is fabrication.
4. Replace nominalized actions with the person or system that acted, what changed, and the cost, time, responsibility, or consequence.
5. Remove pivot templates, insight road signs, absolute jargon, slogan-like short paragraphs, and repeated summary endings.
6. Read the article cold. Ask where the author demonstrates knowledge, which sentence exceeds the material, and where the article has already ended.

Do not manufacture personality with slang, profanity, typos, fake asides, or repeated first-person markers. Voice comes from material selection, admitted uncertainty, and defensible judgment.

## Deterministic Gate

`prepare` records narrow template phrases and absolute jargon as `hard error` findings. It records sentence rhythm, conjunction density, repeated paragraph shapes, nominalization, highlight density, and metaphor clustering as `warning` findings. A warning asks for editorial judgment and never blocks rendering by itself.

The checker detects shapes, not authorship. Passing it does not prove that a human wrote the article, and a warning does not prove that a sentence is wrong.

## Source

This review adapts non-fiction editing ideas from [KKKKhazix/human-writing](https://github.com/KKKKhazix/human-writing), version 1.1.0, commit `4fda173f3fef7fb808f3eba991eeb2528ea4b189`, licensed under MIT. The repository-local pipeline and checker remain independent implementations.
```

- [ ] **Step 7: Run the focused tests and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_skill_contract -v
```

Expected: all `SkillContractTest` tests PASS.

- [ ] **Step 8: Forward-test the revised Skill with a fresh agent**

Give a new fresh agent the exact Step 1 task with the revised Skill. Do not share the baseline output or expected answer. Expected: it does not fabricate enough material for a 2500-character article; because research and questions are forbidden, it explicitly narrows the scope or produces a materially shorter answer with the evidence boundary intact. Compare only the observable decisions, not writing taste.

- [ ] **Step 9: Commit the editorial contract**

```bash
git add publishing-wechat-articles/SKILL.md publishing-wechat-articles/references/writing-contract.md publishing-wechat-articles/references/human-writing-review.md tests/test_skill_contract.py
git commit -m "feat: add staged human writing review"
```

### Task 2: Replace broad phrase blocking with narrow hard findings

**Files:**
- Modify: `tests/test_quality.py:13-52`
- Modify: `tests/test_orchestrator.py:18-87`
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/quality.py:9-85`

- [ ] **Step 1: Add failing hard-rule unit tests**

Add this helper and these tests to `QualityTest`:

```python
    def _report_for(self, body: str):
        return check_article(f"## Section\n\n{body}\n", "<h2>Section</h2>")

    def test_explicit_pivots_road_signs_and_hard_jargon_block(self):
        cases = {
            "banned-word": "这并非速度问题，而是边界问题。",
            "ai-road-sign": "更微妙的是，团队从未记录失败原因。",
            "hard-jargon": "这套组合拳帮助团队完成认知跃迁。",
        }
        for expected_code, body in cases.items():
            with self.subTest(expected_code=expected_code):
                report = self._report_for(body)
                self.assertIn(expected_code, {item.code for item in report.blocking})

    def test_contextual_words_do_not_block_by_themselves(self):
        report = self._report_for("这个方法论可能不适合小团队，其实还要看请求规模。")
        self.assertNotIn("banned-word", {item.code for item in report.blocking})
        self.assertNotIn("hard-jargon", {item.code for item in report.blocking})

    def test_new_hard_rules_ignore_code_examples(self):
        markdown = """---
description: 值得注意的是
---

## Section

```text
更微妙的是，使用组合拳完成认知跃迁。
```

`并非 A，而是 B` 是待检查的提示词。
"""
        report = check_article(markdown, "<h2>Section</h2>")
        codes = {item.code for item in report.blocking}
        self.assertNotIn("banned-word", codes)
        self.assertNotIn("ai-road-sign", codes)
        self.assertNotIn("hard-jargon", codes)
```

- [ ] **Step 2: Add a failing hard-error orchestration test**

Add to `OrchestratorTest`:

```python
    def test_article_quality_error_stops_before_cover(self):
        pipeline = Pipeline(self.config, self.workspace)
        manifest = pipeline.plan(
            "Swift Agent 稳定性检查：识别生产边界",
            "Summary",
            "tech",
            run_id="run-hard-quality",
        )
        run_dir = self.workspace / "runs" / manifest.run_id
        (run_dir / "article.md").write_text(
            "## 稳定性边界\n\n更微妙的是，这套组合拳带来了认知跃迁。\n",
            encoding="utf-8",
        )

        with self.assertRaises(PipelineError):
            pipeline.prepare(manifest.run_id, render_png=False)

        report = json.loads((run_dir / "quality.json").read_text())
        self.assertFalse(report["passed"])
        self.assertIn("ai-road-sign", {item["code"] for item in report["findings"]})
        self.assertEqual(pipeline.status(manifest.run_id).state, Stage.NEEDS_REVIEW)
        self.assertFalse((run_dir / "cover.html").exists())
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_quality.QualityTest.test_explicit_pivots_road_signs_and_hard_jargon_block tests.test_quality.QualityTest.test_contextual_words_do_not_block_by_themselves tests.test_quality.QualityTest.test_new_hard_rules_ignore_code_examples tests.test_orchestrator.OrchestratorTest.test_article_quality_error_stops_before_cover -v
```

Expected: FAIL because `ai-road-sign` and `hard-jargon` findings do not exist. The contextual-word test may already pass and is the false-positive guard for the implementation.

- [ ] **Step 4: Define narrow hard-rule groups**

Replace `BANNED_PATTERNS` and add the two new groups in `quality.py`:

```python
BANNED_PATTERNS = (
    (r"不是[^，。]+[，,]而是", "不是X，而是Y"),
    (r"并非[^，。]+[，,]而是", "并非X，而是Y"),
    (r"不在于[^，。]+[，,]而在于", "不在于X，而在于Y"),
    (r"与其(?:说)?[^，。]+[，,](?:倒)?不如(?:说|讲)?", "与其X，不如Y"),
    (r"看似[^，。]+[，,]实则", "看似X，实则Y"),
    (r"你以为[^，。]+[，,]其实", "你以为X，其实Y"),
    (r"首先.*其次.*最后", "首先...其次...最后"),
    (r"总的来说|总而言之|综上所述", "空泛总结"),
    (r"在当今|不可否认|众所周知|显而易见", "陈词滥调"),
    (r"不难发现|不言而喻|毋庸置疑|毫无疑问", "无依据断言"),
    (r"正如我们所知|需要指出的是|值得注意的是", "AI 过渡语"),
)

AI_ROAD_SIGN_PATTERNS = (
    (r"更微妙的是", "更微妙的是"),
    (r"还有一层", "还有一层"),
    (r"真正的问题是", "真正的问题是"),
    (r"先说结论", "先说结论"),
    (r"只说对了一半", "只说对了一半"),
    (r"从某种意义上说", "从某种意义上说"),
)

HARD_JARGON = (
    "赋能",
    "抓手",
    "商业闭环",
    "价值闭环",
    "能力沉淀",
    "拉通",
    "底层逻辑",
    "顶层设计",
    "认知跃迁",
    "价值释放",
    "能力建设",
    "降本增效",
    "内容矩阵",
    "全链路",
    "组合拳",
    "打开想象空间",
    "结构性机会",
)
```

This intentionally removes the old blanket blocker for `大概|似乎|可能|应该|非常|十分|极其|真正`. Those words need context and cannot be hard errors in the balanced design.

- [ ] **Step 5: Add one reusable finding helper and wire hard groups**

Add above `check_article`:

```python
def _append_regex_findings(
    findings: list[Finding],
    text: str,
    *,
    code: str,
    severity: str,
    patterns: tuple[tuple[str, str], ...],
) -> None:
    for pattern, label in patterns:
        matches = list(re.finditer(pattern, text, flags=re.MULTILINE))
        if matches:
            findings.append(
                Finding(code, severity, label, {"count": len(matches)})
            )
```

Compute the prose body first so frontmatter and code cannot trigger hard findings, then replace the current `BANNED_PATTERNS` loop at the start of `check_article` with:

```python
    body = _without_code(_without_frontmatter(markdown))
    _append_regex_findings(
        findings,
        body,
        code="banned-word",
        severity="error",
        patterns=BANNED_PATTERNS,
    )
    _append_regex_findings(
        findings,
        body,
        code="ai-road-sign",
        severity="error",
        patterns=AI_ROAD_SIGN_PATTERNS,
    )
    jargon_matches = [
        match.group()
        for term in HARD_JARGON
        for match in re.finditer(re.escape(term), body)
    ]
    if jargon_matches:
        findings.append(
            Finding(
                "hard-jargon",
                "error",
                "绝对禁用的商业或模型黑话",
                {"count": len(jargon_matches), "samples": jargon_matches[:6]},
            )
        )
```

- [ ] **Step 6: Run focused and existing quality tests and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_quality tests.test_orchestrator.OrchestratorTest.test_article_quality_error_stops_before_cover -v
```

Expected: all selected tests PASS; the report contains distinct `banned-word`, `ai-road-sign`, and `hard-jargon` codes.

- [ ] **Step 7: Commit hard-rule behavior**

```bash
git add publishing-wechat-articles/scripts/wechat_pipeline/quality.py tests/test_quality.py tests/test_orchestrator.py
git commit -m "feat: add narrow human writing blockers"
```

### Task 3: Add non-blocking prose-shape warnings

**Files:**
- Modify: `tests/test_quality.py`
- Modify: `tests/test_orchestrator.py`
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/quality.py`

- [ ] **Step 1: Add failing warning tests**

Add these tests to `QualityTest`:

```python
    def test_nominalized_action_is_a_non_blocking_warning(self):
        report = self._report_for("团队进行了流程的优化，也实现了效率的提升。")
        self.assertIn("nominalized-action", {item.code for item in report.warnings})
        self.assertTrue(report.passed)

    def test_statistical_prose_shapes_are_warnings(self):
        cases = {
            "conjunction-density": ("但是团队继续检查。" * 8) + ("材料" * 300),
            "uniform-sentence-length": "".join("这个句子的长度保持一致。" for _ in range(12)),
            "single-sentence-paragraphs": "\n\n".join(f"第{index}段只说一句。" for index in range(10)),
            "short-paragraph-streak": "\n\n".join(f"这是连续出现的短句段落{index}，读起来很像口号。" for index in range(4)),
            "repeated-opener": "\n\n".join(f"后来团队检查了步骤{index}，还记录了请求、响应、耗时和恢复结果。" for index in range(4)),
            "highlight-density": "「效率」「协作」「增长」「价值」" + ("材料" * 300),
            "metaphor-cluster": "产品找到新的路径，又需要技术底座，随后被市场浪潮推着走。" + ("材料" * 50),
        }
        for expected_code, body in cases.items():
            with self.subTest(expected_code=expected_code):
                report = self._report_for(body)
                self.assertIn(expected_code, {item.code for item in report.warnings})
                self.assertTrue(report.passed)

    def test_short_samples_skip_statistical_warnings(self):
        report = self._report_for("后来团队修了一个问题。")
        statistical = {
            "conjunction-density",
            "uniform-sentence-length",
            "single-sentence-paragraphs",
            "short-paragraph-streak",
            "repeated-opener",
            "highlight-density",
            "metaphor-cluster",
        }
        self.assertTrue(statistical.isdisjoint({item.code for item in report.warnings}))
```

The short-sample test defines an additional minimum for repeated opener, highlights, and metaphor clustering: these checks run only when the body contains at least 100 Chinese characters. The short-paragraph streak needs no extra document-length minimum because four qualifying paragraphs already provide the required sample. This prevents tiny one-paragraph fixtures from becoming noisy without making the four-paragraph threshold impossible.

- [ ] **Step 2: Add a failing warning-only orchestration test**

Add to `OrchestratorTest`:

```python
    def test_article_quality_warnings_do_not_block_rendering(self):
        pipeline = Pipeline(self.config, self.workspace)
        manifest = pipeline.plan(
            "Swift Agent 流程优化：从检查到稳定运行",
            "Summary",
            "tech",
            run_id="run-soft-quality",
        )
        run_dir = self.workspace / "runs" / manifest.run_id
        (run_dir / "article.md").write_text(
            "## 流程检查\n\n团队进行了流程的优化，随后记录每次失败。\n"
            "\n## 稳定运行\n\n负责人把超时、重试和恢复结果写进日志。\n",
            encoding="utf-8",
        )

        prepared = pipeline.prepare(manifest.run_id, render_png=False)

        report = json.loads((run_dir / "quality.json").read_text())
        self.assertEqual(prepared.state, Stage.RENDERED)
        self.assertTrue(report["passed"])
        self.assertIn("nominalized-action", {item["code"] for item in report["findings"]})
        self.assertTrue((run_dir / "article.html").is_file())
        self.assertTrue((run_dir / "cover.html").is_file())
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_quality.QualityTest.test_nominalized_action_is_a_non_blocking_warning tests.test_quality.QualityTest.test_statistical_prose_shapes_are_warnings tests.test_quality.QualityTest.test_short_samples_skip_statistical_warnings tests.test_orchestrator.OrchestratorTest.test_article_quality_warnings_do_not_block_rendering -v
```

Expected: FAIL because the new warning codes do not exist.

- [ ] **Step 4: Add warning constants and prose helpers**

Add `collections` and `statistics` imports, then add these constants below the hard rules:

```python
CONJUNCTIONS = ("因为", "所以", "但是", "同时", "此外", "然而", "因此", "其实", "当然")
REPEATED_OPENERS = ("首先", "其次", "最后", "另外", "此外", "同时", "其实", "当然", "后来", "于是")
NOMINALIZATION_PATTERNS = (
    r"进行了[^，。！？\n]{1,24}(?:的)?(?:优化|调整|分析|建设|改进|处理)",
    r"实现了[^，。！？\n]{1,24}的(?:提升|增长|优化|改善)",
    r"完成了对[^，。！？\n]{1,24}(?:的)?(?:优化|调整|改造|升级)",
)
METAPHOR_FIELDS = {
    "road": ("路径", "岔路", "赛道"),
    "building": ("底座", "基石", "支柱"),
    "ocean": ("浪潮", "潮水", "深水区"),
    "temperature": ("温度", "滚烫", "冰冷"),
    "storage": ("仓库", "抽屉", "容器"),
}
```

Add these helpers above `check_article`:

```python
def _han_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def _prose_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        clean = re.sub(r"[>*_`]", "", block).strip()
        if not clean or clean.startswith(("#", "http", "![", "```")):
            continue
        if re.match(r"^(?:[-+*]|\d+[.、])\s", clean):
            continue
        if _han_count(clean) >= 4:
            paragraphs.append(clean)
    return paragraphs


def _sentence_lengths(text: str) -> list[int]:
    return [
        _han_count(match.group())
        for match in re.finditer(r"[^。！？!?\n]+[。！？!?]", text)
        if _han_count(match.group()) >= 4
    ]


def _metaphor_cluster(text: str, distance: int = 800) -> tuple[list[str], list[str]] | None:
    hits = []
    for field, words in METAPHOR_FIELDS.items():
        for word in words:
            hits.extend((match.start(), field, word) for match in re.finditer(re.escape(word), text))
    hits.sort()
    for index, (start, _, _) in enumerate(hits):
        window = [hit for hit in hits[index:] if hit[0] - start <= distance]
        fields = sorted({hit[1] for hit in window})
        if len(fields) >= 3:
            return fields, list(dict.fromkeys(hit[2] for hit in window))
    return None
```

- [ ] **Step 5: Implement warning collection**

Add this function above `check_article`:

```python
def _prose_warnings(body: str) -> list[Finding]:
    warnings: list[Finding] = []
    chinese_count = _han_count(body)

    nominalized = [
        match.group()
        for pattern in NOMINALIZATION_PATTERNS
        for match in re.finditer(pattern, body)
    ]
    if nominalized:
        warnings.append(Finding(
            "nominalized-action",
            "warning",
            "名词化动作需要还原成直接动作",
            {"count": len(nominalized), "samples": nominalized[:4]},
        ))

    conjunction_count = sum(body.count(term) for term in CONJUNCTIONS)
    if chinese_count >= 600 and conjunction_count * 1000 / chinese_count > 7:
        warnings.append(Finding(
            "conjunction-density",
            "warning",
            "连接词密度偏高",
            {"count": conjunction_count, "per_thousand": round(conjunction_count * 1000 / chinese_count, 2), "threshold": 7},
        ))

    lengths = _sentence_lengths(body)
    if len(lengths) >= 12:
        mean = statistics.fmean(lengths)
        coefficient = statistics.pstdev(lengths) / mean if mean else 0
        if coefficient < 0.42:
            warnings.append(Finding(
                "uniform-sentence-length",
                "warning",
                "句子长度过于接近",
                {"sentences": len(lengths), "coefficient": round(coefficient, 2), "threshold": 0.42},
            ))

    paragraphs = _prose_paragraphs(body)
    sentence_counts = [max(1, len(re.findall(r"[。！？!?]", paragraph))) for paragraph in paragraphs]
    if len(paragraphs) >= 10:
        ratio = sum(count <= 1 for count in sentence_counts) / len(paragraphs)
        if ratio >= 0.75:
            warnings.append(Finding(
                "single-sentence-paragraphs",
                "warning",
                "单句段落比例偏高",
                {"paragraphs": len(paragraphs), "ratio": round(ratio, 2), "threshold": 0.75},
            ))

    streak = 0
    longest_streak = 0
    for paragraph, sentence_count in zip(paragraphs, sentence_counts):
        if _han_count(paragraph) <= 24 and sentence_count <= 1:
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0
    if longest_streak >= 4:
        warnings.append(Finding(
            "short-paragraph-streak",
            "warning",
            "连续短促单句段可能形成口号节奏",
            {"count": longest_streak, "threshold": 4},
        ))

    if chinese_count >= 100:
        opener_counts = collections.Counter(
            opener
            for paragraph in paragraphs
            for opener in REPEATED_OPENERS
            if paragraph.lstrip("“‘\"（(").startswith(opener)
        )
        repeated = {opener: count for opener, count in opener_counts.items() if count >= 4}
        if repeated:
            warnings.append(Finding(
                "repeated-opener",
                "warning",
                "段落开场重复",
                {"counts": repeated, "threshold": 4},
            ))

        highlights = re.findall(r"[「『][^」』\n]{1,6}[」』]", body)
        highlight_limit = max(3, chinese_count // 700)
        if len(highlights) > highlight_limit:
            warnings.append(Finding(
                "highlight-density",
                "warning",
                "括起的短语过密，可能在批量制造金句",
                {"count": len(highlights), "threshold": highlight_limit, "samples": highlights[:6]},
            ))

        cluster = _metaphor_cluster(body)
        if cluster:
            fields, samples = cluster
            warnings.append(Finding(
                "metaphor-cluster",
                "warning",
                "短距离内混用了多套借喻",
                {"fields": fields, "samples": samples[:6], "window": 800},
            ))

    return warnings
```

In `check_article`, keep the `body` computed before the hard checks, use it for every prose check, use `_han_count(body)` for the report count, and append warnings after structural errors are collected. Remove the old `code_free = _without_code(markdown)` assignment so frontmatter is never scanned:

```python
    body = _without_code(_without_frontmatter(markdown))
    # Existing hard checks remain here.
    findings.extend(_prose_warnings(body))
    chinese_count = _han_count(body)
```

Keep the existing article-length warning, missing-H2 checks, `blocking`, `warnings`, `passed`, and `to_dict()` behavior unchanged.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_quality tests.test_orchestrator.OrchestratorTest.test_article_quality_warnings_do_not_block_rendering -v
```

Expected: all selected tests PASS. `quality.json` has `passed: true` with `nominalized-action` at severity `warning`, and the manifest reaches `rendered`.

- [ ] **Step 7: Commit warning behavior**

```bash
git add publishing-wechat-articles/scripts/wechat_pipeline/quality.py tests/test_quality.py tests/test_orchestrator.py
git commit -m "feat: add nonblocking prose quality warnings"
```

### Task 4: Run complete validation and inspect compatibility

**Files:**
- Verify: `publishing-wechat-articles/`
- Verify: `tests/`

- [ ] **Step 1: Run the full test suite**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Expected: every discovered test PASS with zero errors or failures.

- [ ] **Step 2: Validate the Skill package**

```bash
python3 /Users/nowcoder/Documents/MyCode/services/Skill/skill-hub/skills/.system/skill-creator/scripts/quick_validate.py publishing-wechat-articles
```

Expected: exit code 0 and `Skill is valid!`.

- [ ] **Step 3: Verify the canonical CLI and safe preflight**

```bash
python3 publishing-wechat-articles/scripts/pipeline.py --help
python3 publishing-wechat-articles/scripts/pipeline.py preflight --mode prepare-only --title "Swift Agent 工程化实践" --json
```

Expected: help lists `preflight`, `plan`, `capture`, `retitle`, `prepare`, `status`, `publish`, and `resume`; preflight exits 0 with `ready: true`. Do not run `publish --commit`.

- [ ] **Step 4: Inspect the final diff and compatibility surface**

```bash
git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
git status --short
rg -n "human-writing-review|hard error|warning|至少五项|每个主要段落" publishing-wechat-articles/SKILL.md publishing-wechat-articles/references tests
```

Expected: no whitespace errors; only the design/plan, Skill contracts, `quality.py`, and focused tests changed; worktree is clean after commits. Confirm `quality.json` still has only `passed`, `chinese_characters`, and `findings` at the top level.

- [ ] **Step 5: Report the verified outcome**

Report separately:

- hard rules that now block preparation;
- warning heuristics that remain non-blocking;
- contract/reference changes;
- full test count and Skill validation output;
- confirmation that no OSS upload, Feishu handoff, tracking write, or WeChat publication occurred.
