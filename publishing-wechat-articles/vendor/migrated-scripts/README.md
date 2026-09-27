# Migrated Script Notes

Hermes 侧曾有独立的 OSS 上传、批量飞书发送和文章审核脚本。涉及凭证、固定聊天
目标或旧本地路径的脚本没有原样复制，避免把 Secret 和不可迁移假设带入项目。

| 历史能力 | 当前项目替代 |
|---|---|
| OSS 上传 | `scripts/wechat_pipeline/oss.py` + `publish.py` |
| 飞书单消息与记录 | `scripts/wechat_pipeline/feishu.py` + `publish.py` |
| 文章审核 | `scripts/wechat_pipeline/quality.py` + `title_quality.py` |
| Markdown 转 HTML | `scripts/wechat_pipeline/render.py` |
| 封面生成/检查 | `scripts/wechat_pipeline/cover.py` + `image_generation.py` |
| 公开来源抓取 | `scripts/wechat_pipeline/capture.py` |

旧脚本只作为迁移线索，不作为运行入口。所有运行都从：

```bash
python3 publishing-wechat-articles/scripts/pipeline.py
```
