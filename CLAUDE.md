# Repository Instructions

Use the project-local `publishing-wechat-articles` Skill for WeChat article collection, preparation, and publishing tasks. Its canonical entry point is:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py --help
```

Load `.claude/skills/publishing-wechat-articles/SKILL.md` and follow its authorization gates. Never execute legacy scripts under `vendor/hermes/` and never print `config/runtime.local.toml`.

迁移后的参考 Skill、脚本映射和编辑记忆均保存在仓库内；优先读取
`SOURCE_OF_TRUTH.md` 和 `publishing-wechat-articles/references/`，不要依赖用户目录下
的 Hermes 文件。环境变量配置见根目录 `.env.example`。
