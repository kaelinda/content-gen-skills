---
name: aliyun-oss-upload
description: Upload and verify article artifacts through the repository OSS adapter.
---

# Aliyun OSS Upload

历史独立上传脚本已由 `scripts/wechat_pipeline/oss.py` 替代。凭证来自环境变量或本机
TOML，运行时不接受脚本内硬编码值；每个对象上传后必须用公网 GET/HEAD 按 MIME 和
字节证据验证。
