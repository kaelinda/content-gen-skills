# Source of Truth

本仓库是公众号文章准备与发布的唯一运行源。Codex 和 Claude Code 都通过
`.agents/skills/publishing-wechat-articles` 或 `.claude/skills/publishing-wechat-articles`
指向同一份 Skill；业务逻辑只维护在 `publishing-wechat-articles/` 内。

## 运行入口

```bash
python3 publishing-wechat-articles/scripts/pipeline.py --help
```

`publishing-wechat-articles/scripts/preflight.py` 只是兼容入口，内部转发到同一
CLI，不维护第二套规则。`vendor/hermes/` 是经过筛选的参考快照，禁止直接执行其中
的旧脚本。

## 配置真相

- 频道、主题、路由关键词：`publishing-wechat-articles/config/accounts.toml`
- 无凭证的安全默认值：`publishing-wechat-articles/config/runtime.example.toml`
- 环境变量模板：`.env.example`（真实 `.env` 被忽略）
- 本机发布凭证：环境变量优先，也可使用 `publishing-wechat-articles/config/runtime.local.toml`
- 运行时状态和文章产物：`workspace/runs/<run_id>/`

项目不读取用户目录下的 Hermes 配置。运行时优先读取环境变量，未提供的值再从本地
TOML 读取；这样迁移后的项目可以直接启动，也保留本地复现方式。Secret 不会写入日志、
manifest 或文章产物。

## 状态真相

`manifest.json` 是每次运行的状态机和产物索引。它记录授权模式、频道、阶段、产物
SHA-256、外部 ID、回读证据和错误。OSS 上传、飞书投递、飞书记录和下游公众号状态
必须分别记录，不能用“工具返回成功”代替远端读回。

## 频道边界

| 频道 | 账号 | 主题 | 审核重点 |
|---|---|---|---|
| 技术号 | `tech` / AICoder | 极客黑 | 工程判断、版本/API、代码和风险 |
| 育儿号 | `parenting` / 育儿育己 | 橙心 | 科学依据、年龄适配、具体话术和行动 |

频道选择由 `plan` 的 `--account` 或标题/标签路由决定；准备阶段会把频道传入
质量检查，频道提示会写入 `quality.json`。
