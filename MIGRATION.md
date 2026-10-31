# 快速迁移到另一个 Agent

本仓库保存 Skill、写作经验、渲染器、审核器和发布流水线；根目录 `.env` 保存
**本机私密配置**。不需要搬整套 Hermes，不需要原会话记忆。

## 最短路径

把这个仓库的最新工作版本放到新机器。在仓库根目录执行：

```bash
python3 scripts/bootstrap.py
```

默认只准备当前仓库：创建/复用 `.venv`、安装 `requirements.txt` 和 Chromium、
无 `.env` 时复制模板并设为 `0600`、检查项目 Skill 入口、运行本地准备预检。
**不会**生成文章、调用模型、生图、上传 OSS、发飞书或改全局 Skill。

需要 Python 3.11+。macOS/Linux 可直接运行；Windows 使用 WSL。
Linux 缺 Chromium 系统库时按错误提示安装 Playwright 系统依赖，可能需要管理员权限。
首次安装需要下载浏览器，慢网络下可能持续数分钟；安装器会显示当前阶段。不要用
很短的外层超时中断下载。已有匹配的 Chromium 时可用 `--skip-browser` 跳过下载，
但真实预检仍检查浏览器是否可用。

### 给目标 Agent 安装入口

三选一，仅在你明确选择的目标目录创建一份薄桥接，不复制业务代码和凭证：

```bash
python3 scripts/bootstrap.py --agent hermes
python3 scripts/bootstrap.py --agent codex
python3 scripts/bootstrap.py --agent claude
```

| 选择 | 入口位置 |
|---|---|
| 默认 `project` | 检查仓库现有 `.agents/skills/` 和 `.claude/skills/` |
| `hermes` | `$HERMES_HOME/skills/`，未设置时为当前用户的 `~/.hermes/skills/` |
| `codex` | 当前用户的 `~/.agents/skills/` |
| `claude` | 当前用户的 `~/.claude/skills/` |
| `generic` | 必须用 `--skills-dir` 指定目标 Agent 的 skills 目录 |

例如给其他支持 `SKILL.md` 的 Agent 安装，先查看计划：

```bash
python3 scripts/bootstrap.py --agent generic --skills-dir /path/to/agent/skills --dry-run
```

确认目标无误后去掉 `--dry-run`。`--skills-dir` 也可覆盖命名 Agent 的默认目录。
不要指向其他用户或其他 profile，除非已明确获得授权。

桥接指向**当前仓库的实际路径**，不是第二份真源。相同内容重复安装不覆盖；遇到
已有同名但不同内容的 Skill 会报冲突，由你检查并处理，不会静默替换。
仓库搬家后检查旧入口，清理自己确认过的旧桥接，再在新路径安装。
完整支持程度仍需在目标 Agent 的新会话中验证；创建桥接不等于已完成真实 Agent 对话验收。

## 私密配置单独迁移

- 已有 `.env`：保留它；安装器不覆盖值。
- 新机器：编辑安装器创建的 `.env`，或通过受信私密通道单独复制原 `.env`。
- 执行 `chmod 600 .env`；不上传聊天、不放公开网盘、不提交 Git。
- CLI 自动读取仓库根目录 `.env`，不必运行 `source .env`。
- 优先级：进程环境 > `.env` > 本地 TOML > 示例默认值。
- 不使用的变量删除/注释；显式空值仍覆盖后备值。

详细映射和边界见
[publishing-wechat-articles/references/environment-variables.md](publishing-wechat-articles/references/environment-variables.md)。

## 哪些能力需要额外准备

| 能力 | 额外事项 | 本次安装能证明什么 |
|---|---|---|
| 本地审核、封面模板、HTML | Python 依赖、Chromium | 实际预检结果；模板不是 AI 生图 |
| 中文写作 | Agent 自身模型；也可单独接 `DEEPSEEK_*` | 发布 CLI 不调用写作模型 |
| OSS | `.env` 中的 Bucket/Endpoint/Key | 本地配置完整性，不代表远端写权限 |
| 飞书用户交接 | `lark-cli` 安装并登录，配置目标会话/Base/Table | 本地配置，不代表登录或目标权限有效 |
| Images API 生图 | 可用模型/Key/端点、逐次授权 | 本次没有付费调用 |
| Codex 订阅生图、登录态抓取 | 目标 Agent 自己的能力与独立登录 | 不复制登录 token，不自动迁移该适配器 |
| 外部知识库 | 单独配置连接和权限 | 不自动搬运私人笔记、文章或声称已同步 |

飞书 CLI 的登录说明见 README。浏览器登录态、OAuth、SSH 私钥不属于 `.env`。

## 给新 Agent 的第一条消息

```text
请读取本仓库 AGENTS.md 和 publishing-wechat-articles/SKILL.md，
再读 references/editorial-playbook.md（相对于主 Skill）。
使用 .venv/bin/python 和仓库统一 CLI，所有产物放 output/。
配置自动从根目录 .env 读取，不要打印密钥。
先评估读者价值和审核阶段，默认只准备、不发布。
先完成本地预检，告诉我当前可用能力和缺项，再处理我指定的选题。
```

## 自己验证

```bash
.venv/bin/python publishing-wechat-articles/scripts/pipeline.py --workspace output \
  preflight --mode prepare-only --account tech --json
.venv/bin/python publishing-wechat-articles/scripts/pipeline.py --workspace output \
  preflight --mode publish --account parenting --json
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -q
git check-ignore .env
```

`preflight --mode publish` 仍然是本地只读检查，没有执行发布。
实际交接前需要当前账号的权限检查、终审与明确授权；不得为“测试迁移”擅自发消息。

## 以后只维护哪里

- `publishing-wechat-articles/SKILL.md`：唯一主入口。
- `publishing-wechat-articles/references/editorial-playbook.md`：当前可移植写作技巧。
- `publishing-wechat-articles/references/*-contract.md`：研究、写作、图片和交付约束。
- `publishing-wechat-articles/scripts/wechat_pipeline/`：业务运行实现；根目录 `scripts/bootstrap.py` 只管安装。
- `.env.example`：无密钥的变量模板；`.env`：本机值，不进入版本控制。

`vendor/` 是脱敏历史参考，不安装成一堆平行 Skill，也不执行旧发布脚本。
