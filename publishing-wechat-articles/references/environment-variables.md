# Environment and Credentials

## 当前策略

环境变量是推荐的部署输入；未设置的值从以下 TOML 文件读取：

```text
publishing-wechat-articles/config/runtime.example.toml
publishing-wechat-articles/config/runtime.local.toml
```

`runtime.local.toml` 是本地开发的兼容后备，必须由操作者在本机创建、权限设为 `0600`，
并保持 Git 忽略。任何凭证都不能打印到日志、manifest、文章或报告中。

## 配置项映射

| 配置区 | 用途 | 什么时候需要 |
|---|---|---|
| `[oss]` | 固定 bucket、endpoint、对象前缀 | 所有模式读取，只有发布模式实际写入 |
| `[feishu]` | 飞书应用和默认会话 | 发布模式 |
| `[accounts.tech]` | 技术号 chat/base/table 路由 | 技术号发布模式 |
| `[accounts.parenting]` | 育儿号 chat/base/table 路由 | 育儿号发布模式 |
| `[image_generation]` | 可选封面生成服务 | 明确授权付费生成时 |

## 环境变量名称

兼容迁移提示词中的无前缀名称；`WECHAT_*` 是等价的项目专用别名。环境变量优先级
高于 TOML：

```text
OSS_ACCESS_KEY_ID / WECHAT_OSS_ACCESS_KEY_ID
OSS_ACCESS_KEY_SECRET / WECHAT_OSS_ACCESS_KEY_SECRET
OSS_BUCKET / OSS_ENDPOINT / OSS_REGION / OSS_PREFIX
FEISHU_MODE / FEISHU_PRIMARY_CHAT_ID
FEISHU_TECH_APP_ID / FEISHU_TECH_APP_SECRET / FEISHU_TECH_CHAT_ID / FEISHU_TECH_BASE_ID / FEISHU_TECH_TABLE_ID
FEISHU_PARENTING_APP_ID / FEISHU_PARENTING_APP_SECRET / FEISHU_PARENTING_CHAT_ID / FEISHU_PARENTING_BASE_ID / FEISHU_PARENTING_TABLE_ID
FEISHU_BASE_ID (shared Base alias)
IMAGE_ENABLED / IMAGE_API_BASE / IMAGE_MODEL / OPENAI_API_KEY / IMAGE_TIMEOUT_SECONDS / IMAGE_ALLOWED_DOWNLOAD_HOSTS
```

`IMAGE_ALLOWED_DOWNLOAD_HOSTS` 使用逗号分隔。`IMAGE_ENABLED=true` 只打开能力，不代表
已经获得单次付费生成授权。

只设置内容准备所需的变量即可运行 `collect-only` 和 `prepare-only`。发布模式会检查
OSS、飞书应用、频道目标和布尔字段；当凭证来自环境变量时不要求本地 TOML 存在，
缺失变量仍会失败关闭。

## 迁移说明

旧 Hermes 环境中的 `OSS_ACCESS_KEY_ID`、Feishu 变量和图片变量可直接映射到上面的
接口。`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL` 属于外部写作代理，
当前流水线不会读取它们；文章正文仍由 Agent 写入 `article.md`。不要把 `.env` 文件
复制进仓库。
