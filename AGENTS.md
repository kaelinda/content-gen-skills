# Repository Instructions

Use the project-local `publishing-wechat-articles` Skill for WeChat article collection, preparation, and publishing tasks. Its canonical entry point is:

```bash
python3 publishing-wechat-articles/scripts/pipeline.py --help
```

Load `.agents/skills/publishing-wechat-articles/SKILL.md` and follow its authorization gates. Never execute legacy scripts under `vendor/hermes/` and never print `config/runtime.local.toml`.
