---
name: content-publication-delivery
description: Deliver frozen article artifacts through verified OSS and Feishu checkpoints.
---

# Content Publication Delivery

只使用统一 CLI 的 `publish RUN_ID --commit`。顺序固定为：冻结 manifest，上传封面与
HTML，公网回读，发送一条飞书交接消息，回读消息和表格记录。任何不确定错误进入
`needs_reconcile`，禁止猜测成功或重复发送。
