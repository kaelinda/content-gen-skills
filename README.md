# Content Gen Skills

一个仓库内自包含的公众号文章协作流水线，同时支持 Codex 和 Claude Code。它可以完成公开资料抓取、知识库归档、中文文章质检、标题评分、主题 HTML 渲染和 1200×540 封面生成；只有显式授权后才允许执行 OSS 与飞书写操作。

## 能力

- 一个规范入口：`publishing-wechat-articles/SKILL.md`
- 一个执行入口：`publishing-wechat-articles/scripts/pipeline.py`
- Codex 与 Claude Code 共享同一份 Skill，不复制规则
- 技术号与育儿号分别使用极客黑和橙心主题
- 标题评分、禁用词、正文结构和长度门禁
- SSRF 防护、HTTPS 校验、重定向复核和下载大小限制
- 可恢复的运行清单、产物 SHA-256 与外部操作幂等检查
- 仓库内置 Hermes 参考资源，不读取 `~/.hermes`

## 环境

- Python 3.11+
- Node.js 22.12+（使用 Impeccable 或其他 Node 工具时）
- Playwright Chromium（生成 PNG 封面时）

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

## 快速开始

从仓库根目录运行只读预检：

```bash
python3 publishing-wechat-articles/scripts/pipeline.py preflight \
  --mode prepare-only \
  --title "文章标题" \
  --json
```

创建本地运行并抓取公开来源：

```bash
python3 publishing-wechat-articles/scripts/pipeline.py plan \
  --mode prepare-only \
  --account tech \
  --title "文章标题" \
  --summary "文章摘要" \
  --run-id example-article \
  --json

python3 publishing-wechat-articles/scripts/pipeline.py capture \
  example-article \
  "https://example.com/source" \
  --json
```

将原创稿件写入 `workspace/runs/example-article/article.md`，然后生成 HTML 和封面：

```bash
python3 publishing-wechat-articles/scripts/pipeline.py prepare \
  example-article \
  --json
```

`prepare` 会依次执行标题校验、正文质检、封面生成和 HTML 渲染。标题得分低于 80 时，使用 `retitle` 修改标题后重新生成。

## Codex 与 Claude Code

两个工具通过相对符号链接解析到同一个 Skill：

- Codex：`.agents/skills/publishing-wechat-articles`
- Claude Code：`.claude/skills/publishing-wechat-articles`

根目录的 `AGENTS.md` 和 `CLAUDE.md` 都要求使用统一 CLI，并禁止执行 `vendor/hermes/` 下的旧脚本。

## 配置与安全边界

`prepare-only` 和 `collect-only` 使用仓库内的 `config/runtime.example.toml`，无需凭证或环境变量。

需要发布时，在本机创建：

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
