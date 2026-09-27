# Workflow

## 主流程

```text
选题/读者价值
  -> plan
素材研究与归档
  -> capture + research-check
文章写作
  -> article.md
自动质检与频道审核提示
  -> prepare
人工终审
  -> 确认标题、事实、图片和移动端排版
Markdown 转 HTML + 封面
  -> prepare 产物
OSS 上传与公网回读
  -> publish --commit
飞书单消息投递与回读
  -> tracking record + 状态回读
人工确认公众号状态
  -> draft-confirmed / published
```

## 授权模式

| 模式 | 本地读取/写入 | 外部写入 |
|---|---|---|
| `collect-only` | 来源原文、媒体和出处 | 无 |
| `prepare-only` | Markdown、质检报告、HTML、封面 | 无 |
| `publish` | 上述全部 | 仅 `publish RUN_ID --commit` |

发布顺序是固定的：冻结文章和 manifest，上传封面与 HTML，按返回 URL 做 MIME 和字节
回读，再发送一条包含标题、摘要、封面 URL、HTML URL 的飞书消息，最后读取消息和
表格记录。任何不确定的超时都会进入 `needs_reconcile`，禁止盲目重试。

## 人工审核边界

自动审核只能检查结构、安全和可机械判断的风格问题。人工仍需确认事实、来源映射、
图片可读性、标题承诺、移动端排版、专业边界以及是否真的值得推荐给目标读者。
