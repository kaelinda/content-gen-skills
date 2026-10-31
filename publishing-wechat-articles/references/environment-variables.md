# Environment and Credentials

## 当前策略

环境变量是推荐的部署输入。CLI 自动读取**本仓库根目录**的 `.env`，不依赖当前
工作目录，不搜索其他 Agent 的配置，也不会执行 `source`、shell 命令或变量替换。

优先级按层处理（包括兼容别名）：

1. 进程环境变量；
2. 根目录 `.env`；
3. `publishing-wechat-articles/config/runtime.local.toml`；
4. `publishing-wechat-articles/config/runtime.example.toml` 和账号默认配置。

同层优先使用规范名称，然后使用别名。显式空字符串仍覆盖后备值。
`bootstrap` 在 `.env` 不存在时复制模板；已有文件只收紧权限，不覆盖配置内容。
真实 `.env` 和本地 TOML 必须保持 `0600`、Git 忽略，不能打印到日志、manifest、
文章或报告。`.env.example` 是无密钥的公开模板。

## `.env` 格式

支持单行 `KEY=value`、`export KEY=value`、注释、单双引号及空值。例如：

```dotenv
FEISHU_MODE=lark-cli
OSS_PREFIX='wechat'
IMAGE_ENABLED=false
```

不要写 shell 脚本，不使用多行值、命令替换或依赖 `${VAR}` 展开。
解析器把值当数据，不执行它；语法错误只报告位置，不回显原始内容。
符号链接形式的 `.env` 不受支持。不要把凭证文件放进共享可写目录。

## 配置项映射

| 配置区 | 变量 | 何时需要 |
|---|---|---|
| OSS 凭证 | `OSS_ACCESS_KEY_ID`、`OSS_ACCESS_KEY_SECRET` | 授权上传 |
| OSS 位置 | `OSS_BUCKET`、`OSS_ENDPOINT`、`OSS_REGION`、`OSS_PREFIX` | 上传目标 |
| 飞书模式 | `FEISHU_MODE` | `lark-cli` 或直接 Open API |
| 共享会话/Base | `FEISHU_PRIMARY_CHAT_ID`、`FEISHU_BASE_ID` | 交接和跟踪 |
| 技术号应用 | `FEISHU_TECH_APP_ID`、`FEISHU_TECH_APP_SECRET` | 直接 Open API 模式 |
| 育儿号应用 | `FEISHU_PARENTING_APP_ID`、`FEISHU_PARENTING_APP_SECRET` | 直接 Open API 模式 |
| 技术号目标 | `FEISHU_TECH_CHAT_ID`、`FEISHU_TECH_BASE_ID`、`FEISHU_TECH_TABLE_ID` | 技术号交接 |
| 育儿号目标 | `FEISHU_PARENTING_CHAT_ID`、`FEISHU_PARENTING_BASE_ID`、`FEISHU_PARENTING_TABLE_ID` | 育儿号交接 |
| 可选 Images API | `IMAGE_ENABLED`、`IMAGE_API_BASE`、`IMAGE_MODEL`、`OPENAI_API_KEY` | 单独授权的图片适配器 |
| 图片限制 | `IMAGE_TIMEOUT_SECONDS`、`IMAGE_ALLOWED_DOWNLOAD_HOSTS` | 超时与下载允许名单 |
| 可选中文写作 | `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL` | 目标 Agent 的写作适配器 |

`WECHAT_*` 兼容别名继续保留，完整名称以 `config.py` 为准。
频道 Base ID 优先于共享 `FEISHU_BASE_ID`；每个频道使用自己的 Table ID。
技术和育儿可共用交接会话，但不能因此混写表格。

`IMAGE_ALLOWED_DOWNLOAD_HOSTS` 用逗号分隔。`IMAGE_ENABLED=true` 仅打开能力，
不代表授权单次调用。当前 Images API 适配器只接受其代码中明确支持的模型；
迁移没有验证提供商权限、可用性，也没有增加 Codex 订阅生图适配器。
普通 API Key、代理 Key 和订阅认证不能互换。

`DEEPSEEK_*` 集中存放便于目标写作 Agent 使用，**发布 CLI 不调用 DeepSeek**。
正文仍由 Agent 写入本地 `article.md`，可以用 Agent 自身模型；不能声称配置了
Key 就已经完成模型调用或生成质量验证。

## 不能靠 `.env` 迁移的状态

- `FEISHU_MODE=lark-cli` 需要新机器独立安装 CLI 并完成用户登录；App Secret 不替代
  用户 OAuth，登录用户仍须有目标会话和表格权限。
- 浏览器 Cookie、Codex 登录文件、SSH 私钥不复制进仓库或 `.env`。需要相应能力时
  在新机器使用官方登录流程。
- 模型、图片服务、OSS 公网访问、飞书权限都要在实际任务中核实；预检只是本地检查。
- Knowledge Base/IMA/Obsidian 属于可选外部能力；没有接入时使用仓库本地产物，不能
  报告已同步。文章内容或历史私人资料不随技能自动搬运。

## 安全迁移

Git 仅传代码、Skill、模板与 `.env.example`。真实 `.env` 通过受信私密通道单独放到
新仓库根目录，然后 `chmod 600 .env`。不要在聊天里贴值、提交 `.env`、复制完整旧
Agent 配置，或把业务凭证嵌入桥接 Skill。发布仍需明确的 `publish --commit`。
