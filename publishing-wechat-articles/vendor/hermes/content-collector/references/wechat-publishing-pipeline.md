# 公众号发布完整流水线（X Article → 公众号）

从收录 X Article 到发布公众号的标准化流程，每次执行相同步骤。

## Publishing target routing (2026-07-09 更新)

**首选**：hermes-ali-ecs (`oc_a8a9c19552135fec945d861a967bb465`)
- 所有公众号文章统一发送到此

**备选**（当 hermes-ali-ecs 不可用时）：
- 技术文章 → AICoder内容助手 (`oc_cde2971ca05c08d8b36f4a3f86a6544a`)
- 育儿文章 → 育儿育己 (`oc_4e795533760520c636df4e7a0260c29f`)

执行约定：
1. 发布前先判断文章类别。
2. 若类别模糊，先停一下问用户。
3. 不要在聊天中回显 app_secret。
4. Bot 凭证存储在 `tech-wechat-publish/references/bots.yaml`。

## 流水线总览

```
fxtwitter 抓取 → Obsidian 存档 → 飞书长文表 → 下载封面图 → OSS 上传 → 生成自定义封面 → 写公众号文章 → 按类别路由到目标飞书机器人发布
```

## Step 1: 抓取 X Article

```bash
curl -sL "https://api.fxtwitter.com/{username}/status/{tweet_id}" | python3 -c "
import json, sys
data = json.load(sys.stdin)
article = data.get('tweet', {}).get('article', {})
blocks = article.get('content', {}).get('blocks', [])
entity_map = article.get('content', {}).get('entityMap', [])
# 遍历 blocks，按 type 转换 markdown
"
```

要点：
- fxtwitter 能抓取 Twitter Article 长文（article.content.blocks）
- `header-two` → `## 标题`，`unstyled` → 段落，`atomic` → 从 entityMap 渲染
- inlineStyleRanges 中 Bold → `**text**`
- 封面图在 `article.cover_media.media_info.original_img_url`

## Step 2: 保存 Obsidian

路径：`/Users/nowcoder/Documents/Obsidian/TechnologyHub/raw/articles/{author}-{slug}-{date}.md`

Frontmatter 必须包含：source_url, ingested, sha256, source_type, capture_method, raw_format, tags, category

## Step 3: 写入飞书长文表

- 表 ID：`tblip19KlJtjnH3j`（在 app `JcjhbuXtja0FMrsI7wpcuhClnLh` 下）
- 必须用 `--as user`（bot 会 91403）
- 字段全为 type=1 纯文本（标题/来源/原文/发布标题/公众号/发布内容），标签为 type=4 多选
- 用 stdin 管道传 JSON：`--data -`，不要通过 shell 参数

## Step 4: 下载封面图 + 上传 OSS

⚠️ **必须用 terminal 执行，不能用 execute_code**（oss2 不在沙箱中）

```bash
python3 -c "
import urllib.request, ssl, oss2
# 下载 Twitter 原图
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
ctx = ssl._create_unverified_context()
with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
    with open('/tmp/cover.jpg', 'wb') as f: f.write(resp.read())
# 上传 OSS
auth = oss2.Auth('__MIGRATED_TO_RUNTIME_LOCAL__', '__MIGRATED_TO_RUNTIME_LOCAL__')
bucket = oss2.Bucket(auth, 'https://oss-cn-beijing.aliyuncs.com', 'kaelblog')
with open('/tmp/cover.jpg', 'rb') as f:
    bucket.put_object('wechat/{filename}.jpg', f, headers={'Content-Type': 'image/jpeg'})
"
```

## Step 5: 生成公众号自定义封面 (20:9)

- 当前实现建议直接把完整 JSON 字符串传给 `--data '{...}'`；`im +messages-send` 不支持 `--data -`，不要混用 `api` 子命令和 `im` 子命令的传参方式
- 用 Python subprocess 读取 JSON 文件内容再传字符串，避免 shell 转义 / stdout 截断导致 record_id 丢失

模板参考 `references/html-cover-templates.md`

## Step 6: 写公众号文章

风格要求：
- 标题：数字+痛点+悬念
- 正文：去 AI 味、口语化、短句、有观点
- 小标题用 **加粗**（公众号不渲染 markdown）
- 段落间留空行，emoji 适度
- 字数：3000-5000 字

保存到 `/tmp/wechat_{slug}_article.md`

## Step 7: 按 chat_id 路由发送到目标飞书机器人（两步走）

⚠️ **本节是硬规则（用户 2026-06-23 第三次强调、2026-06-25 重申、2026-06-26 更新 chat_id）。** 不要默认走私人助理，必须按文章类别路由：

| 类别 | 飞书机器人 | chat_id |
|---|---|---|
| **技术类文章** | AICoder 内容助手 | `oc_71044801151e68862ec4f3a518825b87` |
| **教育育儿类文章** | 育儿育己 | `oc_4e795533760520c636df4e7a0260c29f` |
| **类别未明 / 用户显式指定** | 私人助理 P2P | `oc_cde2971ca05c08d8b36f4a3f86a6544a` |

**判断流程**（不要在 chat 中回显询问，自动判断即可）：
1. 概念页 tags 包含 `parenting` / `育儿` / 选题入池 → 育儿育己
2. tags 包含 `agent` / `llm` / `claude` / `developer-tools` / 等等技术标签 → AICoder
3. 没有明确技术/育儿标签 → 默认 AICoder（技术号主战场）
4. 用户指令里显式提到机器人名 → 优先用户指令

**第 0 步（必做）**：生成文章时**必须同时生成一份摘要**（发给飞书机器人的 post content 用），不要只发文章不摘要。

**第一步：post 格式发布请求**（标题 + 摘要 + 封面图 OSS URL）
```python
post_content = {
    "zh_cn": {
        "title": "公众号文章发布请求",
        "content": [
            [{"tag": "text", "text": "请帮忙发布公众号文章\n\n"}],
            [{"tag": "text", "text": f"标题：{title}\n\n"}],
            [{"tag": "text", "text": f"摘要：{summary}\n\n"}],
            [{"tag": "text", "text": f"封面图：{oss_cover_url}\n\n"}],
            [{"tag": "text", "text": "完整文案见下方消息。"}]
        ]
    }
}
```

**第二步：markdown 分段发送**（每段 ≤1000 字符）
- chat_id: `oc_cde2971ca05c08d8b36f4a3f86a6544a`
- 长文本必须拆段，每段单独 `lark-cli im +messages-send --markdown`
- 清理 `---` 水平分割线（飞书会渲染）

## 批量收录模式

当连续收录多篇文章时，每篇独立走完整流水线，但可以：
- 并行执行 Step 1-3（抓取+存档+飞书表）和 Step 4-5（封面图）
- 文章写完后统一发送到私人助理
- 每篇之间保持系列串联感（文末收束语）

## lark-cli + 飞书表操作陷阱

详见 `tech-wechat-publish` 技能下的 `references/lark-cli-feishu-table-traps.md`（4 步对照清单 + 9 个失败案例 + 验证脚本 + 字段类型速查表）。本文件不重复。
