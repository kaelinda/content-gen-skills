# Author Voice Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make author voice a versioned, evidence-backed part of article preparation so that articles differ through the author's attention, judgment, reasoning, and real experience instead of converging on another shared set of anti-AI phrases.

**Architecture:** Merge a repository-owned author core with an account-specific overlay, snapshot the result into each writing run, and require two run-local editorial artifacts: `author-brief.json` before drafting and `voice-review.json` after drafting. The agent remains responsible for semantic writing and review; Python performs deterministic schema, provenance, hash, lifecycle, and compatibility checks without calling a model or an external API.

**Tech Stack:** Python 3.11 standard library, TOML, JSON, dataclasses, SHA-256 run manifests, repository-local Markdown contracts, `unittest`.

---

## Implementation Override: Optional Advanced Mode

The implementation follows the user's later requirement that author voice is an advanced, non-required configuration. The statements below about mandatory schema-v2 runs are superseded by these rules:

- Enable author voice per run with `plan --author-voice`; a normal `plan` run keeps the historical workflow.
- Keep manifest schema version 1 and add an optional `editorial` object only to enabled runs.
- Require `voice-context.json`, `author-brief.json`, and `voice-review.json` only when `editorial.author_voice_enabled=true`.
- Run voice-profile preflight checks only with `preflight --author-voice`.
- Preserve the default `banned-word` blocking policy. Only enabled runs treat those generic expressions as `generic-language` warnings backed by the stronger voice review.
- Reject `--author-voice` with `collect-only`; the option is available to `prepare-only` and `publish` runs without changing publish authorization.

This override is authoritative wherever later task text conflicts with it.

## Product Decisions

1. Author voice is a positive selection system, not a larger banned-word list. It controls what the article notices, argues, proves, omits, and how it reasons before it controls sentence rhythm.
2. The checked-in profile contains stable principles and account behavior. Published article samples, private experiences, and interview notes stay under ignored `workspace/vaults/<account>/voice/` paths.
3. A personal claim may appear only when `author-brief.json` points to an existing evidence entry. An article may use no personal claims; the system must never invent one merely to sound human.
4. Semantic review remains agent editorial work. The runtime validates that the review cites the current article and contains concrete excerpts; it does not pretend that regexes can determine whether prose is authentically human.
5. This plan complements `docs/superpowers/specs/2026-08-06-human-writing-quality-design.md`. Structural failures, unsupported claims, unsafe resources, and absolute jargon remain blocking. A generic stylistic phrase becomes a warning unless a narrow rule proves a concrete violation. This rule supersedes that design's blanket `banned-word=error` policy.
6. `collect-only`, `prepare-only`, and `publish` authorization boundaries do not change. None of the new commands may upload OSS objects, send Feishu messages, write tracking rows, or infer publication.
7. Do not fine-tune a model in this version. First prove that profile retrieval, evidence binding, and editorial gates improve blind comparison results.

## Run Data Flow

```text
config/voice/author.toml
  + config/voice/accounts/<account>.toml
  -> plan snapshots voice-context.json
  -> agent creates author-brief.input.json
  -> pipeline brief validates and stores author-brief.json
  -> agent writes article.md
  -> agent creates voice-review.input.json against article.md
  -> pipeline voice-review validates and stores voice-review.json
  -> prepare verifies hashes and editorial gates
  -> title check -> article check -> cover -> HTML
```

For new `prepare-only` and `publish` runs, both editorial artifacts are required. Legacy schema-v1 manifests remain readable and continue through the historical preparation path.

## File Map

| File | Responsibility |
|---|---|
| `publishing-wechat-articles/config/voice/author.toml` | Stable author attention, reasoning habits, boundaries, and language tendencies |
| `publishing-wechat-articles/config/voice/accounts/tech.toml` | Technical account audience, selection bias, proof preferences, and tone |
| `publishing-wechat-articles/config/voice/accounts/parenting.toml` | Parenting account audience, evidence boundaries, and tone |
| `publishing-wechat-articles/scripts/wechat_pipeline/voice.py` | Voice profile merge, schema validation, evidence lookup, artifact normalization, and hash checks |
| `publishing-wechat-articles/scripts/wechat_pipeline/config.py` | Resolve checked-in voice files and local account vaults |
| `publishing-wechat-articles/scripts/wechat_pipeline/manifest.py` | Schema-v2 editorial metadata and schema-v1 compatibility |
| `publishing-wechat-articles/scripts/wechat_pipeline/orchestrator.py` | Snapshot voice context; ingest brief/review; enforce preparation gates |
| `publishing-wechat-articles/scripts/pipeline.py` | Expose `brief` and `voice-review` commands through the canonical CLI |
| `publishing-wechat-articles/scripts/wechat_pipeline/preflight.py` | Validate voice configuration for prepare and publish modes |
| `publishing-wechat-articles/scripts/wechat_pipeline/quality.py` | Keep mechanical checks separate from author-voice evidence checks |
| `publishing-wechat-articles/references/author-voice-contract.md` | Agent-facing profile, brief, drafting, and review contract |
| `publishing-wechat-articles/references/writing-contract.md` | Insert author voice before drafting and clarify warning/error policy |
| `publishing-wechat-articles/references/resource-map.md` | Document new configuration, vault, and run artifacts |
| `publishing-wechat-articles/SKILL.md` | Require the author-voice contract at the Write and Check gates |
| `tests/test_voice.py` | Pure unit tests for profile and artifact validation |
| `tests/voice_helpers.py` | Shared valid brief, review, and article fixtures for voice tests |
| `tests/test_manifest.py` | Manifest migration and editorial metadata tests |
| `tests/test_orchestrator.py` | Run lifecycle, stale review, legacy compatibility, and no-write tests |
| `tests/test_cli.py` | New command help, JSON output, and failure behavior |
| `tests/test_quality.py` | Warning/error policy regression tests |
| `tests/test_skill_contract.py` | Documentation and canonical-entry-point invariants |

### Task 1: Define and load the layered voice profile

**Files:**
- Create: `publishing-wechat-articles/config/voice/author.toml`
- Create: `publishing-wechat-articles/config/voice/accounts/tech.toml`
- Create: `publishing-wechat-articles/config/voice/accounts/parenting.toml`
- Create: `publishing-wechat-articles/scripts/wechat_pipeline/voice.py`
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/config.py`
- Create: `tests/test_voice.py`

- [ ] **Step 1: Write the failing profile-loading tests**

```python
class VoiceProfileTest(unittest.TestCase):
    def setUp(self):
        self.config = load_repository_config(SKILL)

    def test_profile_merges_author_core_with_account_overlay(self):
        profile = load_voice_profile(self.config, "tech")
        self.assertEqual(profile.schema_version, 1)
        self.assertEqual(profile.account, "tech")
        self.assertIn("attention", profile.author)
        self.assertIn("audience", profile.overlay)
        self.assertTrue(profile.profile_sha256)

    def test_parenting_and_tech_overlays_do_not_mix(self):
        tech = load_voice_profile(self.config, "tech")
        parenting = load_voice_profile(self.config, "parenting")
        self.assertNotEqual(tech.overlay["audience"], parenting.overlay["audience"])
        self.assertNotEqual(tech.profile_sha256, parenting.profile_sha256)
```

- [ ] **Step 2: Run the focused test and verify the module is missing**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_voice.VoiceProfileTest -v
```

Expected: `ERROR` because `wechat_pipeline.voice` or `load_voice_profile` does not exist.

- [ ] **Step 3: Add concrete profile files**

Use this author-core shape, seeded only from the author's explicit position in the design discussion:

```toml
schema_version = 1
profile_version = "2026-08-06"

[author]
attention = [
  "观察一套看似正确的规则是否正在制造新的同质化",
  "从具体使用者和执行者的处境判断方案是否成立",
]
reasoning = [
  "先识别表面共识，再检查共识造成的二阶结果",
  "用具体生活类比解释抽象的产品或技术问题",
  "明确区分事实、个人判断和仍待验证的推断",
]
boundaries = [
  "没有证据时不虚构第一人称经历",
  "不为了显得鲜明而强行反对共识",
  "不把口头禅、错别字或网络梗当作作者声音",
]

[language]
cadence = "自然长短句，以论证需要为准"
metaphor = "只使用能降低理解成本的具体类比"
ending = "事情讲完即结束，不重复摘要或强行升华"
```

Use this technical overlay:

```toml
schema_version = 1

[account]
audience = "需要把 AI 和软件工程能力落到真实系统中的开发者"
attention = ["工程边界", "运行时失败", "维护成本", "方案取舍"]
proof = ["可运行代码", "真实调用链", "测试结果", "性能或运维后果"]
tone = "实用、精确，明确说明限制和代价"
avoid = ["只讲概念不讲落点", "把厂商宣称写成已验证事实"]
```

Use this parenting overlay:

```toml
schema_version = 1

[account]
audience = "希望理解孩子行为并采取可执行行动的照护者"
attention = ["可观察行为", "发展阶段", "家庭约束", "关系后果"]
proof = ["权威资料", "明确适用边界的案例", "可重复执行的家庭行动"]
tone = "温和、具体、证据清楚，不制造照护者羞耻"
avoid = ["把个案包装成普遍规律", "用诊断式语言替代专业评估"]
```

Neither overlay may contain invented biography.

- [ ] **Step 4: Implement immutable profile loading and hashing**

Implement `VoiceProfile` and `load_voice_profile` in `voice.py`:

```python
@dataclass(frozen=True)
class VoiceProfile:
    schema_version: int
    profile_version: str
    account: str
    author: dict[str, object]
    language: dict[str, object]
    overlay: dict[str, object]
    profile_sha256: str


def load_voice_profile(config: RepositoryConfig, account: str) -> VoiceProfile:
    if account not in config.accounts:
        raise VoiceError(f"unknown account: {account}")
    author_path = config.skill_root / config.voice_author_path
    overlay_path = config.skill_root / config.voice_accounts_root / f"{account}.toml"
    author = tomllib.loads(author_path.read_text(encoding="utf-8"))
    overlay = tomllib.loads(overlay_path.read_text(encoding="utf-8"))
    if int(author.get("schema_version", 0)) != 1 or int(overlay.get("schema_version", 0)) != 1:
        raise VoiceError("unsupported voice profile schema")
    canonical = json.dumps(
        {"author": author, "account": account, "overlay": overlay},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return VoiceProfile(
        schema_version=1,
        profile_version=str(author["profile_version"]),
        account=account,
        author=dict(author["author"]),
        language=dict(author["language"]),
        overlay=dict(overlay["account"]),
        profile_sha256=hashlib.sha256(canonical).hexdigest(),
    )
```

Add resolved voice paths to `RepositoryConfig`; do not add another config loader or an environment-variable override:

```python
@dataclass(frozen=True)
class RepositoryConfig:
    skill_root: Path
    repository_root: Path
    runtime_path: Path
    voice_author_path: Path
    voice_accounts_root: Path
    schema_version: int
    oss: OssConfig
    runtime: RuntimeConfig
    accounts: dict[str, AccountProfile]
```

`load_repository_config` sets these to `Path("config/voice/author.toml")` and `Path("config/voice/accounts")`. `load_voice_profile` resolves both relative paths under `config.skill_root` before reading.

- [ ] **Step 5: Run the focused tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_voice.VoiceProfileTest -v
```

Expected: both profile tests pass.

- [ ] **Step 6: Commit the profile contract**

```bash
git add publishing-wechat-articles/config/voice publishing-wechat-articles/scripts/wechat_pipeline/voice.py publishing-wechat-articles/scripts/wechat_pipeline/config.py tests/test_voice.py
git commit -m "feat: add layered author voice profiles"
```

### Task 2: Add deterministic brief and review contracts

**Files:**
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/voice.py`
- Modify: `tests/test_voice.py`
- Create: `tests/voice_helpers.py`

- [ ] **Step 1: Add complete shared valid fixtures**

```python
def valid_brief(profile_sha256: str = "a" * 64) -> dict[str, object]:
    return {
        "schema_version": 1,
        "profile_sha256": profile_sha256,
        "reader_problem": "读者只能得到一组去 AI 味词表",
        "source_baseline": "现有方案依赖固定禁用表达",
        "incremental_value": "把作者判断和证据变成写作前置条件",
        "thesis": "作者声音来自持续的内容选择，而不是口头禅",
        "tension": "统一反套路规则会制造新的统一套路",
        "reasoning_moves": ["描述现状", "指出二阶结果", "给出数据契约"],
        "evidence_refs": [],
        "personal_claims": [],
        "counterpoint": "机械检查仍适合发现结构和安全问题",
        "excluded_directions": ["本期不做模型微调"],
        "title_candidates": ["作者声音不是另一份禁词表", "去掉 AI 味之后，还剩下谁的判断", "把作者声音放进写作流水线"],
    }


def valid_review(article_sha256: str = "b" * 64, excerpt: str = "正文原句") -> dict[str, object]:
    names = ("attention", "judgment", "reasoning", "evidence", "language")
    return {
        "schema_version": 1,
        "article_sha256": article_sha256,
        "decision": "pass",
        "dimensions": [
            {"name": name, "status": "present", "excerpts": [excerpt], "note": f"{name} 有明确落点"}
            for name in names
        ],
        "blockers": [],
        "anonymous_paragraphs": [],
    }


def write_article(
    run_dir: Path,
    text: str = "## Swift Agent 工程化判断\n\n具体正文说明 Swift Agent 从原型到稳定运行的工程边界。\n",
) -> str:
    article = run_dir / "article.md"
    article.write_text(text, encoding="utf-8")
    return hashlib.sha256(article.read_bytes()).hexdigest()


def ingest_valid_brief(pipeline, workspace: Path, run_id: str):
    manifest = pipeline.status(run_id)
    source = workspace / f"{run_id}-brief-input.json"
    source.write_text(
        json.dumps(valid_brief(manifest.editorial["profile_sha256"]), ensure_ascii=False),
        encoding="utf-8",
    )
    return pipeline.ingest_brief(run_id, source)


def ingest_valid_review(pipeline, workspace: Path, run_id: str, run_dir: Path):
    digest = hashlib.sha256((run_dir / "article.md").read_bytes()).hexdigest()
    source = workspace / f"{run_id}-review-input.json"
    source.write_text(
        json.dumps(valid_review(digest, excerpt="具体正文"), ensure_ascii=False),
        encoding="utf-8",
    )
    return pipeline.ingest_voice_review(run_id, source)


def create_legacy_run_with_article(workspace: Path) -> str:
    run_id = "legacy-run"
    run_dir = workspace / "runs" / run_id
    run_dir.mkdir(parents=True)
    now = "2026-08-06T00:00:00+00:00"
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "authorization_mode": "prepare-only",
        "account": "tech",
        "title": "Swift Agent 工程化实践：从原型到稳定运行",
        "summary": "说明从原型到稳定运行的工程边界。",
        "state": "planned",
        "artifacts": {},
        "external": {},
        "errors": [],
        "created_at": now,
        "updated_at": now,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    write_article(run_dir)
    return run_id
```

- [ ] **Step 2: Write failing validation tests**

Add tests covering these exact behaviors:

```python
def test_brief_requires_author_increment_and_three_title_candidates(self):
    payload = valid_brief()
    payload["incremental_value"] = ""
    payload["title_candidates"] = ["one", "two"]
    with self.assertRaisesRegex(VoiceError, "incremental_value"):
        validate_author_brief(payload, expected_profile_sha256="a" * 64, evidence_ids=set())


def test_personal_claim_requires_existing_evidence(self):
    payload = valid_brief()
    payload["personal_claims"] = [{"claim": "我曾经上线过这套系统", "evidence_id": "launch-1"}]
    with self.assertRaisesRegex(VoiceError, "launch-1"):
        validate_author_brief(payload, expected_profile_sha256="a" * 64, evidence_ids=set())


def test_review_must_reference_current_article_hash_and_excerpts(self):
    payload = valid_review(article_sha256="b" * 64)
    with self.assertRaisesRegex(VoiceError, "article_sha256"):
        validate_voice_review(payload, expected_article_sha256="c" * 64, article_markdown="正文原句")
    payload = valid_review(article_sha256="c" * 64)
    payload["dimensions"][0]["excerpts"] = []
    with self.assertRaisesRegex(VoiceError, "excerpts"):
        validate_voice_review(payload, expected_article_sha256="c" * 64, article_markdown="正文原句")
```

- [ ] **Step 3: Run the tests and verify missing validators fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_voice -v
```

Expected: `ERROR` for undefined validation functions.

- [ ] **Step 4: Define the normalized `author-brief.json` contract**

The validator must accept only this top-level shape and return a normalized dictionary:

```json
{
  "schema_version": 1,
  "profile_sha256": "64 lowercase hex characters",
  "reader_problem": "读者正在面对的具体问题",
  "source_baseline": "原始资料已经说明的内容",
  "incremental_value": "这篇文章新增的判断或方法",
  "thesis": "作者准备证明的核心判断",
  "tension": "表面共识与二阶结果之间的冲突",
  "reasoning_moves": ["事实", "区别", "限制", "后果"],
  "evidence_refs": ["sample-or-note-id"],
  "personal_claims": [],
  "counterpoint": "最强反方观点及其成立边界",
  "excluded_directions": ["本篇不讨论的方向"],
  "title_candidates": ["标题一", "标题二", "标题三"]
}
```

Require non-empty strings, three distinct title candidates, at least two reasoning moves, and exact profile-hash equality. Every `personal_claims[].evidence_id` must exist in the local evidence index. `evidence_refs` may be empty when the article uses only captured public sources and makes no personal claim.

- [ ] **Step 5: Define the normalized `voice-review.json` contract**

```json
{
  "schema_version": 1,
  "article_sha256": "64 lowercase hex characters",
  "decision": "pass",
  "dimensions": [
    {"name": "attention", "status": "present", "excerpts": ["正文原句"], "note": "为什么只有这位作者会注意它"},
    {"name": "judgment", "status": "present", "excerpts": ["正文原句"], "note": "文章做出了什么取舍"},
    {"name": "reasoning", "status": "present", "excerpts": ["正文原句"], "note": "判断如何从证据推出"},
    {"name": "evidence", "status": "present", "excerpts": ["正文原句"], "note": "事实与亲历是否可追溯"},
    {"name": "language", "status": "present", "excerpts": ["正文原句"], "note": "语言是否服务于内容而非表演人设"}
  ],
  "blockers": [],
  "anonymous_paragraphs": []
}
```

Require all five dimension names exactly once. `status` is one of `present`, `weak`, or `missing`. Every cited excerpt must occur verbatim in the supplied article Markdown. `pass` requires every dimension to be `present`, no blockers, and no anonymous paragraphs. A `revise` decision remains valid input but must later block preparation. Do not calculate a synthetic numeric authenticity score.

- [ ] **Step 6: Implement validators and evidence-index loading**

Add pure functions `load_evidence_ids(vault_path)`, `validate_author_brief`, and `validate_voice_review`. Read optional evidence metadata from `workspace/vaults/<account>/voice/evidence.toml` using this format:

```toml
schema_version = 1

[[evidence]]
id = "stable-unique-id"
kind = "published_article"
path = "samples/article-file.md"
```

Reject duplicate IDs, absolute paths, `..` traversal, and paths that escape the account voice vault. Do not fail merely because the optional index does not exist; treat it as an empty evidence set.

- [ ] **Step 7: Run tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_voice -v
git add publishing-wechat-articles/scripts/wechat_pipeline/voice.py tests/test_voice.py tests/voice_helpers.py
git commit -m "feat: validate author briefs and voice reviews"
```

Expected: all voice tests pass.

### Task 3: Snapshot voice context and migrate manifests safely

**Files:**
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/manifest.py`
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/orchestrator.py`
- Modify: `tests/test_manifest.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing migration and snapshot tests**

```python
def test_schema_v1_manifest_loads_as_legacy_without_voice_gate(self):
    run_id = create_legacy_run_with_article(self.workspace)
    path = self.workspace / "runs" / run_id / "manifest.json"
    loaded = RunManifest.load(path)
    self.assertEqual(loaded.schema_version, 1)
    self.assertFalse(loaded.requires_voice)


def test_new_prepare_run_snapshots_voice_context(self):
    pipeline = Pipeline(self.config, self.workspace)
    manifest = pipeline.plan("Swift Agent 工程化实战", "摘要", "tech", run_id="voice-run")
    run_dir = self.workspace / "runs" / manifest.run_id
    context = json.loads((run_dir / "voice-context.json").read_text(encoding="utf-8"))
    self.assertEqual(manifest.schema_version, 2)
    self.assertEqual(context["account"], "tech")
    self.assertEqual(context["profile_sha256"], manifest.editorial["profile_sha256"])
    self.assertIn("voice_context", manifest.artifacts)
```

- [ ] **Step 2: Run focused tests and verify they fail**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_manifest tests.test_orchestrator -v
```

Expected: failure because schema 2, `editorial`, `requires_voice`, and the context artifact are absent.

- [ ] **Step 3: Add backward-compatible manifest schema 2**

Change `RunManifest` so new runs serialize `schema_version=2` and an `editorial` object. `load` must accept schemas 1 and 2, default `editorial={}` for schema 1, preserve the loaded schema number, and reject every other version.

```python
@property
def requires_voice(self) -> bool:
    return self.schema_version >= 2 and self.authorization_mode in {"prepare-only", "publish"}
```

The serialized editorial shape is:

```json
{
  "profile_version": "2026-08-06",
  "profile_sha256": "64 lowercase hex characters",
  "brief_status": "missing",
  "review_status": "missing"
}
```

- [ ] **Step 4: Snapshot the merged profile during `Pipeline.plan`**

For `prepare-only` and `publish`, load the routed account profile, write normalized `voice-context.json` into the run directory, record it as `voice_context`, and persist editorial metadata before returning. `collect-only` must not require a voice profile and must preserve its current local-only behavior.

Use atomic writes for the manifest. The context snapshot must contain the merged profile values and profile hash, but no private evidence content.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_manifest tests.test_orchestrator -v
git add publishing-wechat-articles/scripts/wechat_pipeline/manifest.py publishing-wechat-articles/scripts/wechat_pipeline/orchestrator.py tests/test_manifest.py tests/test_orchestrator.py
git commit -m "feat: snapshot voice context in writing runs"
```

Expected: schema-v1 compatibility and schema-v2 context tests pass.

### Task 4: Add canonical CLI ingestion for briefs and reviews

**Files:**
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/orchestrator.py`
- Modify: `publishing-wechat-articles/scripts/pipeline.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_brief_ingestion_normalizes_and_records_artifact(self):
    pipeline = Pipeline(self.config, self.workspace)
    planned = pipeline.plan("Swift Agent 工程化实战", "摘要", "tech", run_id="voice-run")
    source = self.workspace / "brief-input.json"
    source.write_text(
        json.dumps(valid_brief(planned.editorial["profile_sha256"]), ensure_ascii=False),
        encoding="utf-8",
    )
    manifest = pipeline.ingest_brief("voice-run", source)
    self.assertEqual(manifest.editorial["brief_status"], "ready")
    self.assertIn("author_brief", manifest.artifacts)


def test_review_ingestion_binds_to_current_article(self):
    pipeline = Pipeline(self.config, self.workspace)
    pipeline.plan("Swift Agent 工程化实战", "摘要", "tech", run_id="voice-run")
    ingest_valid_brief(pipeline, self.workspace, "voice-run")
    run_dir = self.workspace / "runs" / "voice-run"
    article = run_dir / "article.md"
    article.write_text("## 判断\n\n具体正文。\n", encoding="utf-8")
    digest = hashlib.sha256(article.read_bytes()).hexdigest()
    source = self.workspace / "review-input.json"
    source.write_text(json.dumps(valid_review(digest, excerpt="具体正文"), ensure_ascii=False), encoding="utf-8")
    manifest = pipeline.ingest_voice_review("voice-run", source)
    self.assertEqual(manifest.editorial["review_status"], "pass")
    self.assertIn("voice_review", manifest.artifacts)
```

Extend `test_all_commands_expose_help` with `brief` and `voice-review`.

- [ ] **Step 2: Run tests and verify missing commands fail**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli tests.test_orchestrator -v
```

Expected: command-help and missing method failures.

- [ ] **Step 3: Implement `Pipeline.ingest_brief`**

Require a schema-v2 writing run and an existing `voice_context` artifact. Read the input as JSON, load account evidence IDs, validate against the snapshotted profile hash, write normalized output to `author-brief.json`, record its hash, set `brief_status=ready`, and invalidate any existing review artifact because a changed brief changes the article's editorial basis.

- [ ] **Step 4: Implement `Pipeline.ingest_voice_review`**

Require `author-brief.json` and `article.md`. Calculate the article SHA-256, validate the review against that exact hash, write normalized output to `voice-review.json`, record its hash, and persist `review_status` as `pass` or `revise`.

- [ ] **Step 5: Expose the two CLI commands**

```bash
python3 publishing-wechat-articles/scripts/pipeline.py brief RUN_ID \
  --input /absolute/path/to/author-brief.input.json --json

python3 publishing-wechat-articles/scripts/pipeline.py voice-review RUN_ID \
  --input /absolute/path/to/voice-review.input.json --json
```

Both commands are local writes only. They must use the existing exception redaction path and may not construct a `Publisher`.

- [ ] **Step 6: Run tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli tests.test_orchestrator -v
git add publishing-wechat-articles/scripts/wechat_pipeline/orchestrator.py publishing-wechat-articles/scripts/pipeline.py tests/test_cli.py tests/test_orchestrator.py
git commit -m "feat: add author brief and voice review commands"
```

Expected: both commands expose help, normalize valid input, and reject invalid or stale input.

### Task 5: Enforce voice gates during preparation

**Files:**
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/orchestrator.py`
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/manifest.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing preparation-gate tests**

```python
def test_schema_v2_prepare_requires_ready_brief_and_passing_review(self):
    pipeline = Pipeline(self.config, self.workspace)
    pipeline.plan("Swift Agent 工程化实战", "摘要", "tech", run_id="voice-run")
    run_dir = self.workspace / "runs" / "voice-run"
    write_article(run_dir)
    with self.assertRaisesRegex(PipelineError, "author brief"):
        pipeline.prepare("voice-run", render_png=False)
    ingest_valid_brief(pipeline, self.workspace, "voice-run")
    with self.assertRaisesRegex(PipelineError, "voice review"):
        pipeline.prepare("voice-run", render_png=False)


def test_article_edit_invalidates_previous_review(self):
    pipeline = Pipeline(self.config, self.workspace)
    pipeline.plan("Swift Agent 工程化实战", "摘要", "tech", run_id="voice-run")
    run_dir = self.workspace / "runs" / "voice-run"
    write_article(run_dir)
    ingest_valid_brief(pipeline, self.workspace, "voice-run")
    ingest_valid_review(pipeline, self.workspace, "voice-run", run_dir)
    (run_dir / "article.md").write_text("## 已修改\n\n新的正文。\n", encoding="utf-8")
    with self.assertRaisesRegex(PipelineError, "stale voice review"):
        pipeline.prepare("voice-run", render_png=False)


def test_legacy_manifest_keeps_historical_prepare_path(self):
    run_id = create_legacy_run_with_article(self.workspace)
    pipeline = Pipeline(self.config, self.workspace)
    prepared = pipeline.prepare(run_id, render_png=False)
    self.assertEqual(prepared.state, Stage.RENDERED)
```

- [ ] **Step 2: Run the focused tests and verify the missing gate**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_orchestrator -v
```

Expected: new runs prepare without the required artifacts or fail for the wrong reason.

- [ ] **Step 3: Implement `_verify_editorial_gate` before title checking**

For a run where `manifest.requires_voice` is true, require:

- the `voice_context`, `author_brief`, and `voice_review` artifacts to exist and match their recorded SHA-256 values;
- brief profile hash to equal `manifest.editorial.profile_sha256`;
- review article hash to equal the current `article.md` hash;
- review decision to equal `pass`;
- all personal-claim evidence IDs to remain resolvable.

On failure, transition `WRITTEN -> NEEDS_REVIEW` after recording `article_markdown`, append a concise non-secret error, save the manifest, and raise `PipelineError`. Do not render HTML or a cover.

- [ ] **Step 4: Preserve valid recovery behavior**

A corrected brief invalidates the review. A corrected review may be ingested from `NEEDS_REVIEW` without manually editing `manifest.json`. `retitle` does not invalidate the voice review because it does not change `article.md`; it continues to invalidate title quality, rendered HTML, and cover artifacts exactly as today.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_orchestrator tests.test_manifest -v
git add publishing-wechat-articles/scripts/wechat_pipeline/orchestrator.py publishing-wechat-articles/scripts/wechat_pipeline/manifest.py tests/test_orchestrator.py tests/test_manifest.py
git commit -m "feat: enforce evidence-backed voice review before render"
```

Expected: missing, failed, and stale editorial artifacts block schema-v2 preparation; schema-v1 runs remain compatible.

### Task 6: Reconcile mechanical quality rules with author voice

**Files:**
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/quality.py`
- Modify: `tests/test_quality.py`
- Modify: `docs/superpowers/specs/2026-08-06-human-writing-quality-design.md`

- [ ] **Step 1: Write failing severity tests**

```python
def test_single_generic_transition_is_a_warning_not_a_blocker(self):
    markdown = "## 边界\n\n值得注意的是，这个限制只影响旧版本。\n"
    report = check_article(markdown, '<section id="nice"><h2>边界</h2></section>')
    self.assertNotIn("generic-language", {item.code for item in report.blocking})
    self.assertIn("generic-language", {item.code for item in report.warnings})


def test_absolute_jargon_and_structural_errors_remain_blocking(self):
    markdown = "## 方案\n\n这套组合拳形成价值闭环。\n\n---\n"
    report = check_article(markdown, '<section id="nice"><h2>方案</h2></section>')
    codes = {item.code for item in report.blocking}
    self.assertIn("hard-jargon", codes)
    self.assertIn("body-horizontal-rule", codes)
```

- [ ] **Step 2: Run the focused tests and confirm current severity fails**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_quality -v
```

Expected: the current `banned-word` error makes the first test fail.

- [ ] **Step 3: Split stylistic warnings from concrete blockers**

Replace the single `BANNED_PATTERNS` policy with named rule groups:

```python
GENERIC_LANGUAGE_PATTERNS = (
    (r"值得注意的是", "值得注意的是"),
    (r"总的来说|总而言之|综上所述", "空泛总结"),
    (r"首先.*其次.*最后", "固定路标"),
)

HARD_JARGON_PATTERNS = (
    (r"赋能|抓手|价值闭环|认知跃迁|组合拳", "无具体信息的黑话"),
)
```

Emit `generic-language` with `severity=warning` and include match count plus examples in `details`. Emit `hard-jargon` with `severity=error`. Keep code/frontmatter stripping and existing structural errors unchanged. Do not make warning count automatically escalate to an error.

- [ ] **Step 4: Amend the existing human-writing design**

Change its blocking-policy section to state that the author-voice plan supersedes blanket phrase blocking. Preserve the document's statistical-warning thresholds and narrow hard-jargon rules. Add a link to this plan so future implementation does not apply contradictory severity policies.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_quality -v
git add publishing-wechat-articles/scripts/wechat_pipeline/quality.py tests/test_quality.py docs/superpowers/specs/2026-08-06-human-writing-quality-design.md
git commit -m "refactor: make generic writing patterns advisory"
```

Expected: generic phrasing warns, concrete jargon and structural violations block.

### Task 7: Update agent-facing writing contracts and preflight

**Files:**
- Create: `publishing-wechat-articles/references/author-voice-contract.md`
- Modify: `publishing-wechat-articles/references/writing-contract.md`
- Modify: `publishing-wechat-articles/references/resource-map.md`
- Modify: `publishing-wechat-articles/SKILL.md`
- Modify: `publishing-wechat-articles/scripts/wechat_pipeline/preflight.py`
- Modify: `tests/test_skill_contract.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing contract and preflight tests**

```python
def test_skill_requires_voice_contract_before_editorial_work(self):
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    self.assertIn("references/author-voice-contract.md", skill)
    self.assertLess(skill.index("author-voice-contract.md"), skill.index("article.md"))


def test_prepare_preflight_detects_missing_voice_profile(self):
    config = load_repository_config(SKILL)
    broken = replace(config, voice_author_path=Path("missing-author.toml"))
    report = run_preflight(broken, "prepare-only", "tech", playwright_available=True)
    self.assertIn("voice_profile", report.failures)
```

- [ ] **Step 2: Run tests and verify the missing contract fails**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_skill_contract tests.test_cli -v
```

Expected: missing reference and preflight check failures.

- [ ] **Step 3: Write `author-voice-contract.md`**

The contract must state, in this order:

1. Read the run's `voice-context.json`; never read another account's vault.
2. Write and ingest `author-brief.json` before drafting.
3. Use personal experience only through evidence IDs; absence of personal experience is acceptable.
4. Draft for attention, judgment, reasoning, and evidence before language style.
5. After the draft is complete, review all five dimensions using exact excerpts.
6. Mark anonymous paragraphs that another author could publish unchanged as `revise`.
7. Ingest the review through the CLI; never edit `manifest.json` by hand.
8. Treat generic-language findings as editorial warnings, not proof of AI authorship.

- [ ] **Step 4: Update the canonical workflow**

Change the Write and Check gates in `SKILL.md` to require `voice-context.json`, `author-brief.json`, and a current passing `voice-review.json`. Add the exact `brief` and `voice-review` command examples. Keep `pipeline.py` as the only entry point and retain the explicit `publish --commit` gate verbatim.

Update `writing-contract.md` so its Account Voice section points to the layered profile instead of reducing voice to one adjective row. Update `resource-map.md` with checked-in profile paths, ignored evidence paths, and run-local artifact paths.

- [ ] **Step 5: Extend preflight without affecting collection**

For `prepare-only` and `publish`, verify the author profile and selected account overlay exist and parse. For `collect-only`, do not require voice configuration. Report a stable `voice_profile` failure key without exposing file contents.

- [ ] **Step 6: Run tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_skill_contract tests.test_cli -v
git add publishing-wechat-articles/references publishing-wechat-articles/SKILL.md publishing-wechat-articles/scripts/wechat_pipeline/preflight.py tests/test_skill_contract.py tests/test_cli.py
git commit -m "docs: add evidence-backed author voice workflow"
```

Expected: Skill contract and mode-sensitive preflight tests pass.

### Task 8: Add end-to-end acceptance and blind calibration protocol

**Files:**
- Create: `tests/fixtures/author-brief.json`
- Create: `tests/fixtures/voice-review.json`
- Modify: `tests/test_e2e.py`
- Modify: `publishing-wechat-articles/references/author-voice-contract.md`

- [ ] **Step 1: Write a failing end-to-end schema-v2 run test**

The test must execute this local sequence with fixture transport and no external adapters:

```text
plan prepare-only
-> capture fixture source
-> ingest fixture brief
-> write article.md
-> calculate article hash and ingest fixture review
-> prepare without PNG
-> status rendered
```

Assert that the manifest records `voice_context`, `author_brief`, `voice_review`, `article_markdown`, `title_quality_report`, `quality_report`, `article_html`, and `cover_html`. Assert the injected external hook remains an empty list.

- [ ] **Step 2: Run the end-to-end test and verify it fails before fixture support is complete**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_e2e -v
```

Expected: failure at the first unimplemented voice artifact or command.

- [ ] **Step 3: Add deterministic fixtures and make the test pass**

Use a technical article fixture with a clear thesis, one counterpoint, no personal claim, and five review dimensions citing exact article excerpts. Generate the review's `article_sha256` inside the test so the checked-in fixture contains no unstable hash.

- [ ] **Step 4: Document the manual blind calibration protocol**

Append this release gate to `author-voice-contract.md`:

- Select ten topics representative of both accounts.
- Produce one article with the historical workflow and one with the voice workflow from the same source pack.
- Hide workflow labels and randomize order.
- Require the author to prefer the voice version in at least eight of ten pairs.
- Ask an independent reader to identify the intended account; require at least 70% accuracy.
- Require zero unsupported personal claims and zero cross-account evidence references.
- Record rejected profile traits and revise the profile version instead of weakening evidence gates.

- [ ] **Step 5: Run full verification**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 /Users/nowcoder/Documents/MyCode/services/Skill/skill-hub/skills/.system/skill-creator/scripts/quick_validate.py publishing-wechat-articles
python3 publishing-wechat-articles/scripts/pipeline.py --help
python3 publishing-wechat-articles/scripts/pipeline.py preflight --mode prepare-only --title "Swift Agent 工程化实践" --json
git diff --check
```

Expected:

- all unit and integration tests pass;
- Skill validation prints `Skill is valid!`;
- CLI help lists `brief` and `voice-review`;
- prepare preflight reports `ready: true` on a correctly provisioned machine;
- `git diff --check` produces no output;
- no OSS upload, Feishu handoff, tracking write, or other external mutation occurs.

- [ ] **Step 6: Commit the acceptance coverage**

```bash
git add tests/fixtures tests/test_e2e.py publishing-wechat-articles/references/author-voice-contract.md
git commit -m "test: cover author voice pipeline end to end"
```

## Completion Criteria

Implementation is complete only when all of the following are true:

1. Every new writing run snapshots a versioned account-appropriate voice profile.
2. Drafting cannot begin under the documented workflow without a concrete author brief.
3. Schema-v2 preparation rejects missing, failed, stale, or unsupported voice evidence.
4. Schema-v1 manifests still load and complete through their historical path.
5. A single generic transition phrase does not block preparation.
6. Unsupported personal claims, hard jargon, structural errors, and unsafe resources remain blocking.
7. `prepare-only` performs no external writes and `publish` still requires both prior publish-mode planning and explicit `--commit`.
8. The blind calibration protocol meets its preference and account-recognition thresholds before the profile is treated as stable.
9. The full test suite, Skill validation, CLI smoke check, preflight, and `git diff --check` all pass.
