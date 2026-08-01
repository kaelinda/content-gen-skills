# OSS 封面图公开访问校验模式

适用场景：公众号封面图生成后、发给飞书助理前，必须验证 OSS URL 真的可公开访问。

## 为什么要做这一步

Playwright 渲染成功 + oss2 `put_object` 返回成功 + 本地 PNG 文件大小正常，都不能替代“公网可达”校验。
公众号编辑器只认公网 URL，外部图床 / 受限内网地址都会发布失败或被静默吞图。

## 推荐校验脚本（macOS 环境）

```python
import urllib.request, ssl

def verify_oss_public(url: str, timeout: int = 30):
    req = urllib.request.Request(url, method='HEAD')
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        print(r.status, r.headers.get('Content-Type'), r.headers.get('Content-Length'))
        return r.status == 200

verify_oss_public('https://kaelblog.oss-cn-beijing.aliyuncs.com/wechat/cover_xxx.png')
```

## 说明

- 本机 Python 常见 `CERTIFICATE_VERIFY_FAILED`，用 `ssl._create_unverified_context()` 做本地发布前验证
- 这不是鼓励永久跳过证书校验，而是发布流水线里的实用校验步骤
- 同一脚本也能校验文章正文里替换后的 OSS 图片链接

## 最小 checklist

- [ ] 封面图已上传 OSS
- [ ] OSS URL 返回 200
- [ ] Content-Type 为图片类型
- [ ] Content-Length 与本地文件一致（可选）
