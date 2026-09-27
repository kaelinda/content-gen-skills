# Repository Instructions

Use the project-local `publishing-wechat-articles` Skill for WeChat article collection, preparation, and publishing tasks. Its canonical entry point is:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py --help
```

Load `.agents/skills/publishing-wechat-articles/SKILL.md` and follow its authorization gates. Never execute legacy scripts under `vendor/hermes/` and never print `config/runtime.local.toml`.

迁移后的参考 Skill 快照位于 `publishing-wechat-articles/vendor/migrated-skills/`，历史
经验位于 `publishing-wechat-articles/references/migrated-memory.md`。它们属于项目内
Source of Truth 的参考资料；运行时仍只使用仓库 CLI 和安全适配器。

部署可使用根目录 `.env.example` 中的环境变量。环境变量优先于
`publishing-wechat-articles/config/runtime.local.toml`，真实 `.env` 不得提交。
