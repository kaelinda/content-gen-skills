# Content Gen Skills

一个仓库内自包含的公众号文章协作流水线，同时支持 Codex 和 Claude Code。它可以完成公开资料抓取、知识库归档、中文文章质检、标题评分、主题 HTML 渲染和 1200×540 封面生成；只有显式授权后才允许执行 OSS 与飞书写操作。

项目的边界和迁移映射见 [SOURCE_OF_TRUTH.md](SOURCE_OF_TRUTH.md)、
[references/workflow.md](publishing-wechat-articles/references/workflow.md) 和
[references/migration-report.md](publishing-wechat-articles/references/migration-report.md)。

## 能力

- 一个规范入口：`publishing-wechat-articles/SKILL.md`
- 一个执行入口：`publishing-wechat-articles/scripts/pipeline.py`
- Codex 与 Claude Code 共享同一份 Skill，不复制规则
- 技术号与育儿号分别使用极客黑和橙心主题
- 标题评分、禁用词、正文结构和长度门禁
- frontmatter、链接/图片、代码围栏、Markdown 表格、残留 marker 和敏感信息审核
- 技术号与育儿号的频道差异化审核提示
- SSRF 防护、HTTPS 校验、重定向复核和下载大小限制
- 可恢复的运行清单、产物 SHA-256 与外部操作幂等检查
- 仓库内置 Hermes 参考资源，不读取 `~/.hermes`

## 环境与依赖安装

项目文件包含运行代码、模板、主题和参考资料。新机器还需要安装以下依赖，再加载
`.env`；无需复制全局 Skill 或私人 `runtime.local.toml`。

| 依赖 | 用途 | 什么时候需要 |
|---|---|---|
| Python 3.11+ | 运行统一 CLI | 必需 |
| `certifi` | HTTPS 证书校验 | 由 `requirements.txt` 安装 |
| `playwright` 与 Chromium | 将封面 HTML 渲染为 PNG | 生成 PNG 封面时 |
| `Pillow` | 正文图片处理与生成封面尺寸调整 | 由 `requirements.txt` 安装；CLI 启动时会导入 |
| Node.js 22.12+ 与 npm | 安装飞书 CLI、运行 Impeccable 等 Node 工具 | 使用这些能力时 |
| `lark-cli` | 飞书消息交接与多维表格记录 | `FEISHU_MODE=lark-cli` 时 |

以下命令从仓库根目录执行，适用于 macOS 和 Linux 的 bash/zsh。当前发布模块使用
Unix 文件锁；Windows 请在 WSL 中运行。

### 1. 安装 Python 依赖和浏览器

先安装 [Python 3.11+](https://www.python.org/downloads/)；使用飞书 CLI 或 Node 工具时，
再安装 [Node.js 22.12+](https://nodejs.org/en/download)（包含 npm）。

```bash
python3 --version  # 确认版本为 3.11 或以上
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

Linux 服务器如果还缺少 Chromium 系统库，可将最后一步替换为
`python3 -m playwright install --with-deps chromium`，安装系统库时可能需要管理员权限。
重新打开终端后，先执行 `source .venv/bin/activate`，保证安装和运行使用同一个 Python。
`.venv/` 已被 Git 忽略，不需要提交或复制到其他机器。

### 2. 配置并加载环境变量

已有 `.env` 时跳过复制步骤；新机器先复制模板，再按需填写 OSS、飞书和可选生图配置：

```bash
cp .env.example .env
```

当前 CLI **不会自动读取 `.env`**。填写完成后，在运行命令的同一终端中加载：

```bash
set -a
source .env
set +a
```

部署时也可以由进程管理器直接注入同名环境变量。环境变量优先于本地 TOML；空值也会
覆盖对应配置，因此暂时不用的变量请删除或注释。真实 `.env` 已被 Git 忽略，不要提交。
收录和本地准备不需要发布凭证，也可以跳过此步骤。

### 3. 安装并登录飞书 CLI（使用飞书交接时）

默认 `.env.example` 使用 `FEISHU_MODE=lark-cli`。该模式需要在运行机器上单独安装 CLI，
完成应用配置和用户登录；项目 `.env` 中的飞书目标配置不会替代 CLI 的登录状态。

```bash
node --version
npm install -g @larksuite/cli
lark-cli --version
lark-cli config init
lark-cli auth login --domain im,base
lark-cli auth status
```

按交互提示选择飞书并完成应用配置、浏览器授权，登录用户需要具备目标会话和多维表格
的访问权限。安装说明见 [飞书 CLI 官方文档](https://github.com/larksuite/cli)。如果使用
直接 Open API 模式，则按 `.env.example` 填写对应频道的应用 ID 和 Secret，无需 CLI 登录。

### 4. 运行只读预检

```bash
python3 publishing-wechat-articles/scripts/pipeline.py --workspace output \
  preflight --mode prepare-only --json
```

返回 `ready: true` 表示本地准备的预检通过。需要 OSS 上传和飞书交接时，配置完成后再运行
同一命令，将模式改为 `--mode publish` 并指定 `--account tech` 或 `--account parenting`。
预检只检查本地配置与依赖，不代表已验证远端权限、CLI 登录或已完成发布。

## 快速开始

从仓库根目录运行只读预检：

```bash
python3 publishing-wechat-articles/scripts/pipeline.py --workspace output preflight \
  --mode prepare-only \
  --title "文章标题" \
  --json
```

创建本地运行并抓取公开来源：

```bash
python3 publishing-wechat-articles/scripts/pipeline.py --workspace output plan \
  --mode prepare-only \
  --account tech \
  --title "文章标题" \
  --summary "文章摘要" \
  --run-id example-article \
  --json

python3 publishing-wechat-articles/scripts/pipeline.py --workspace output capture \
  example-article \
  "https://example.com/source" \
  --json
```

将原创稿件写入 `output/runs/example-article/article.md`，然后生成 HTML 和封面：

```bash
python3 publishing-wechat-articles/scripts/pipeline.py --workspace output prepare \
  example-article \
  --json
```

`prepare` 会依次执行标题校验、正文质检、封面生成和 HTML 渲染。标题得分低于 80 时，使用 `retitle` 修改标题后重新生成。

质检报告写入 `output/runs/<run-id>/quality.json`。它包含阻断项和频道提示；自动检查
不能替代事实、图片和移动端排版的人工终审。

## Codex 与 Claude Code

两个工具通过相对符号链接解析到同一个 Skill：

- Codex：`.agents/skills/publishing-wechat-articles`
- Claude Code：`.claude/skills/publishing-wechat-articles`

根目录的 `AGENTS.md` 和 `CLAUDE.md` 都要求使用统一 CLI，并禁止执行 `vendor/hermes/` 下的旧脚本。

## 配置与安全边界

`prepare-only` 和 `collect-only` 无需发布凭证。配置优先读取环境变量，未设置的值读取
本机 `runtime.local.toml`；该文件不存在时使用仓库内的 `runtime.example.toml`。

发布推荐使用上面的 `.env` 加载方式，无需创建私人 TOML。本地开发也可以选择在本机创建：

```text
publishing-wechat-articles/config/runtime.local.toml
```

文件结构参考 `runtime.example.toml`，权限必须为 `0600`。该文件已被 Git 忽略，禁止提交、打印或复制其值。

外部写操作必须同时满足：

- 运行在创建时选择了 `--mode publish`
- 发布前预检通过
- 命令显式包含 `publish RUN_ID --commit`

没有这些条件时，流水线不会上传 OSS、发送飞书消息或写入飞书表格。

## 测试

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

当前示例文章和资料归档位于 `workspace/`，包括 Impeccable 的安装、进阶使用和已有工程接入指南。
