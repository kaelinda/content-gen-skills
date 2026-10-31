# Migration Report

更新依据：既有迁移输入、现行公众号编辑规则，以及本轮跨 Agent 快速迁移验收。

## 本轮快速迁移增量

- 根目录 `scripts/bootstrap.py` 提供单命令准备环境；默认只处理项目，显式选择后才
  为 Hermes、Codex、Claude 或指定 skills 目录创建薄入口。
- 根目录 `.env` 自动读取，不依赖 cwd、不执行 shell；进程环境优先，TOML 作为后备。
- 真实 `.env` 保留已有值、权限 `0600`、Git 忽略；公开 `.env.example` 补齐可选写作
  变量。私密凭证、浏览器 Cookie、OAuth 文件均不进入提交和桥接目录。
- `editorial-playbook.md` 收拢读者价值、技术/育儿文风、分阶段审核、来源标题、
  不编造经历、长度选择、图片与交接技巧，隔离历史快照中的冲突指令。
- 更新迁移/配置/资源/图片/发布合同，修正路径基准和对现有能力的过度承诺。
- 根目录 `AGENTS.md`、`CLAUDE.md` 保留原样；现有入口仍指向同一主 Skill。

### 本轮实际验收范围

在路径包含空格的隔离副本中，排除真实 `.env`、本地 TOML 与用户原有未提交改动，
使用独立 Python 虚拟环境和独立浏览器缓存完成真实依赖/Chromium 安装与本地预检。
四种 Agent 桥接均创建并读回验证，重复安装保持一致；技术号和育儿号均实际渲染
HTML 与可解码的 1200×540 PNG。无发布凭证的副本在发布预检中正确阻断。

本机 `.env` 自动读取以及两个频道的本地发布预检也已验证；预检不证明远端权限。
精确测试数量以当次提交的实际测试记录为准；下方旧版数字仅为历史记录。

### 没有随仓库自动迁移的能力

- 目标 Agent 的真实对话验收、飞书用户登录、浏览器登录态和外部知识库连接。
- DeepSeek 调用（变量集中存放，但发布 CLI 不代写正文）。
- Codex 订阅生图适配器及其认证；现有 Images API 库函数也不是已接通的 CLI 命令。
- 真实 OSS/飞书写操作、付费生成和公众号发布。本轮迁移没有执行这些操作。

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

## 历史版本实际验证（非本轮测试数量）

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
