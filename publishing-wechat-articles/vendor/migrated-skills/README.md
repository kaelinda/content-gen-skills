# Migrated Skill Snapshots

这些文件是从本机 Hermes 环境收编的可复用方法论快照，已移除本机绝对路径、
具体会话 ID 和凭证。它们不是第二套运行时入口；文章流水线仍只执行
`publishing-wechat-articles/scripts/pipeline.py`。

## Included
- `content-research-writer/SKILL.md`
- `dbs-agent-migration/SKILL.md`
- `dbs-ai-check/SKILL.md`
- `dbs-content/SKILL.md`
- `dbs-content-system/SKILL.md`
- `feishu-article-tracker/SKILL.md`
- `parenting-serial-review/SKILL.md`
- `parenting-content-writer/SKILL.md`
- `parenting-content-audit/SKILL.md`
- `tech-content-audit/SKILL.md`
- `content-publication-delivery/SKILL.md`
- `aliyun-oss-upload/SKILL.md`
- `md-to-html/SKILL.md`

## Runtime mapping

- 内容研究与写作规则 -> `references/selection-research-contract.md` and `writing-contract.md`
- AI 写作检查 -> `scripts/wechat_pipeline/quality.py`
- 飞书文章记录 -> `scripts/wechat_pipeline/feishu.py` and `publish.py`
- 育儿串行复审 -> `references/workflow.md` and the `parenting` account gates
- Agent 工作台迁移 -> `SOURCE_OF_TRUTH.md` and the repository-local bridges
