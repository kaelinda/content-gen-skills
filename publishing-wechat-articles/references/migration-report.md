# Migration Report

更新依据：迁移输入文件 `hermes-agent/wechat-publishing-migration-prompt.md`。

## 已迁移和已落实

- 将选题读者价值、官网优先、来源映射、重复检查和限制写入
  `selection-research-contract.md`，并由 `research-check` 验证记录完整性。
- 将技术号和育儿号的受众、主题、路由和发布字段集中到 `config/accounts.toml`。
- 将抓取、归档、标题评分、正文审核、封面、Markdown 渲染、OSS、飞书、状态清单和
  恢复流程收敛到 `scripts/pipeline.py` 及 `wechat_pipeline/`。
- 将安全审核扩展到 frontmatter、代码围栏、资源 URL、Markdown 表格、残留 marker、
  本机路径、Authorization/Cookie/API key 等敏感值。
- 技术号和育儿号的审核提示在同一个质量报告中区分：技术号关注工程判断和边界；
  育儿号关注适用年龄、具体话术和行动建议。
- 发布顺序、OSS/飞书回读、幂等、`needs_reconcile` 和“草稿不等于公开发布”规则
  保留在 `publishing-contract.md` 与发布实现中。
- 可选作者声音和可选图片生成继续保持显式启用、单次授权、无外部副作用的边界。
- 将 Hermes 中与本项目相关的内容研究、AI 检查、飞书追踪、育儿复审和 Agent 迁移
  Skill 收编到 `vendor/migrated-skills/`，并将历史经验整理到 `migrated-memory.md`。
- 将旧的 OSS/飞书脚本改为安全适配器映射，拒绝复制含硬编码凭证、固定聊天目标或
  旧本地路径的可执行脚本。

## 与建议目录的差异

迁移提示词中的多个独立 Skill 和脚本在本项目中没有复制成平行实现。它们由一个
canonical Skill 和一个 CLI 统一承载，避免技术写作、育儿写作、审核和发布规则漂移。
`vendor/hermes/` 只保留参考资源，不是运行时依赖。

仓库提供 `.env.example` 作为部署输入模板；真实 `.env` 被 Git 忽略，
`config/runtime.local.toml`
作为开发后备；字段和安全要求见 `environment-variables.md`。

## 实际验证

在仓库根目录执行：

```bash
python3 publishing-wechat-articles/scripts/preflight.py --mode prepare-only --title "Swift Agent 工程化实践" --json
python3 -m compileall publishing-wechat-articles/scripts
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q
```

实际结果：预检通过；Python 脚本编译通过；`106` 个测试全部通过。另用临时副本删除
`runtime.local.toml`，只注入环境变量，`publish` 预检仍返回 `ready=true`。本次没有执行
真实发布，因此没有上传 OSS、发送飞书消息或写入线上表格。

## 仍需人工确认

- 每篇文章的事实、来源段落、原创增量和目标读者价值；检查器不自动判真伪。
- 封面和正文图片的文字可读性、相关性、版权/使用限制及移动端效果。
- `publish --commit` 前的最终 Markdown、图片、HTML 和标题冻结。
- 公众号草稿或公开发布状态；飞书投递和记录成功不代表已经公开发布。

## 已知风险

- 频道差异化规则目前以机械检查和 warning 为主，不能替代技术专家或育儿专业人员
  的人工审核。
- `prepare` 对没有 `research.json` 的历史 run 保持兼容；新采编任务仍必须建立研究
  记录。
- 公网 URL 的可访问性和内容相关性需要在发布前实际回读和视觉检查。
