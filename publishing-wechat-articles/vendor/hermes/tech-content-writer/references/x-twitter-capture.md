# X / Twitter 内容抓取 → 中文技术文章

把 X 推文（含长文 Article、推文串、引用推）转成中文技术公众号文章的输入阶段。本文件是 `tech-content-writer` 的 capture 子流程。

## 用户偏好（2026-06-14 已确认）

抓取优先级：
1. **opencli 复用 Chrome 登录态**（需 Playwright MCP Bridge，用户环境未安装时跳过）
2. **fxtwitter 公开 API**（无 auth，全文返回，默认首选）
3. **官方 x-cli / X API**（需付费 credentials，最后选择）

默认走 fxtwitter： `curl -sL "https://api.fxtwitter.com/{handle}/status/{tweet_id}"`

## ⚠️ 关键陷阱：`tweet.text` 经常为空

普通推文：`tweet.text` 字段就是正文。
**Twitter Article（长文，draft.js 格式）**：`tweet.text` 是空字符串、 `tweet.raw_text.text` 通常只是 URL 占位符。正文在 `tweet.article.content.blocks[]` 里。

**判断方法**：
```python
if "article" in tweet and tweet["article"].get("content", {}).get("blocks"):
    # 是 Twitter Article，走 blocks 抽取
else:
    # 普通推文/推文串，读 tweet.text 或 tweet.thread
```

> 用户 2026-06-15 实测踩坑：以为推文抓空了，其实是 Article 类型。

## Twitter Article 抽取：draft.js blocks → Markdown

```python
def blocks_to_md(blocks):
    out = []
    for b in blocks:
        t = b.get("type", "")
        # 抽 text（draft.js 的 text 在不同 type 字段里）
        text = ""
        if isinstance(b.get("text"), str):
            text = b["text"]
        elif isinstance(b.get("content"), list):
            for c in b["content"]:
                if isinstance(c, dict):
                    text += c.get("text", "")
        text = text.strip()
        if t == "header-two":
            out.append(f"## {text}")
        elif t == "header-three":
            out.append(f"### {text}")
        elif t == "unordered-list-item":
            out.append(f"- {text}")
        elif t == "ordered-list-item":
            out.append(f"1. {text}")
        elif t == "atomic":
            # 图片/嵌入/分隔线等媒体块；如需保留可输出 ![](url)
            continue
        elif t == "unstyled" and text:
            out.append(text)
    return "\n\n".join(out)
```

完整字段速查（实测覆盖常见 80% 场景）：

| block type | 含义 | 输出 |
|---|---|---|
| `unstyled` | 段落 | 纯文本 |
| `header-two` | H2 标题 | `## ` |
| `header-three` | H3 标题 | `### ` |
| `header-one` | H1（少见） | `# ` |
| `unordered-list-item` | 无序列表项 | `- ` |
| `ordered-list-item` | 有序列表项 | `1. ` |
| `blockquote` | 引用 | `> ` |
| `atomic` | 图片/嵌入/媒体 | 跳过（除非想保留 URL） |
| `code-block` | 代码块 | 包裹 ``` 围栏 |

## 普通推文 / 推文串

```python
# 单条推文
text = tweet["text"]

# 推文串（thread）
thread = tweet.get("thread", [])
for t in thread:
    print(t["text"], "\n---")
```

## 引用推（quote tweet）

引用推文本身只携带作者的评论，正文是它引用的那一条。fxtwitter 返回的 `tweet` 是**评论推文**，被引用的推文在 `tweet.quoted_tweet` 字段（实测有时缺失，需要再次请求被引用 tweet 的 URL）。

## 抓取后：转成中文文章的输入

1. **保存 raw 源**到本地（推荐 `/tmp/tweet_<id>.json` 完整 fxtwitter 响应），保留原始 URL 链接。
2. **用 blocks_to_md 把 Article 编译为 markdown**，再喂给 DeepSeek 写文章。
3. **prompt 中必须包含**：
   - 原始标题、预览（preview_text）
   - 原始 URL
   - 完整编译后的 markdown 正文
   - 必填的二次创作要求 + 真实案例
   - 明确字数目标（3000-4000 中文字符）

## 适配 DeepSeek Prompt 的模板

参考 `tech-content-writer` 的 "DeepSeek API 调用规范"。英文 → 中文改编类文章，prompt 必须强调：

- **不要照搬原文结构** —— 重新组织、补充独到分析、融入个人视角和实操案例
- **避免「不是 X，而是 Y」** —— 英文 "not X, but Y" 翻译时几乎本能映射为该句式
- **字数扩充** —— 英文长文 1500-2000 字典型，中文至少写到 2500 字以上

## Pitfalls

1. **空 text 字段先检查 article**：fxtwitter 抓到的 tweet，如果 `tweet.text == ""` 且 `raw_text.text` 是 URL，先看 `tweet.article.content.blocks`。
2. **Article blocks 的 text 字段位置不固定**：`unstyled` 块的 text 在 `block["text"]`；`atomic` 块没有 text 字段；要 robust 处理 `block.get("text")` 和 `block.get("content", [])` 两种来源。
3. **fxtwitter 长文截断**：超过 ~15000 字符的 Article 可能被截断（fxtwitter 没有分页）。如果 blocks 数量明显少于预览字符数估算，尝试用原始 ID 抓两次或用 Jina reader 兜底。
4. **Tweet Article 封面图**：`tweet.article.cover_media.media_info.original_img_url` 给出原作者设计的封面 —— 可以作为公众号封面的参考，但**不要直接用**（设计风格往往和公众号不匹配）。用 `wechat-cover-image` skill 重新生成 20:9 横向版。
5. **英文 → 中文几乎必然出现「不是 X，而是 Y」**：见 `tech-content-writer` SKILL 里的 "英文→中文改编是「不是X，而是Y」的重灾区" Pitfall。第一遍写完立即跑 BANNED_PATTERNS 扫描（含空洞修饰词），不要等所有文章写完再统一检查。

## 与其他 skill 的关系

- `tech-content-writer`（本 SKILL 的父 skill）— 写作风格 + 禁用词 + DeepSeek Prompt
- `tech-wechat-publish` — 写完后发布到飞书的流程（封面、OSS、lark-cli）
- `wechat-cover-image` — 20:9 横向封面生成
- `aliyun-oss-upload` — 封面图上传 OSS

## Thread 不存在时的回退策略（2026-06-18 v_pradeilles 实测）

当 `tweet.thread` 为空、fxtwitter 推文只有 1 张图 + 1 句话时，**直接进入"web 搜索 + 抓权威源"二次创作模式**。

### 判定 thread 不存在（4 步）

1. `tweet.thread` 数组是 `None` / `[]`？
2. `tweet.in_reply_to_status_id` 是 `None`？（是回复推文则看主推文）
3. `tweet.text` 含 `🧵` emoji 但 thread 字段空？（作者预告要开 thread 但实际未发）
4. 最准：用 `browser_navigate` 打开推文 URL，看 snapshot 中 "Read N replies" 文本（N=1 或 0 = 单条推文）

### Web 搜索 + 抓权威源（标准动作）

- **步骤 1**：`web_search` 搜 "主题 + 关键词" 找 3-5 家媒体（优先：官方公告、专门垂直媒体、知名科技媒体）
- **步骤 2**：`web_extract` 抓 2-3 篇最详细的文章，抽 8 个维度的要点
- **步骤 3**：把这些要点 + 源推文信息喂给 DeepSeek 写中文文章，prompt 中**显式声明**："源推文只有 1 句话 + 1 张封面图，本篇是基于官方公告 + 媒体二次报道的原创解读"
- **关键判断**：「thread 不存在」≠「主题没料」。1 张封面图 + 1 句话的推文，配合官方/媒体资料，能写出 3000+ 字的好文章。

### 避免

**反复尝试不同 thread reader 工具**（unrollnow、threadreaderapp、xcancel、nitter、thread-reader）—— 这些都抓不到尚未发出的 thread，纯属浪费时间。判定 thread 不存在后立即转入 web 搜索模式。

### 兜底 API

`https://cdn.syndication.twimg.com/tweet-result?id=<ID>&token=0` —— 返回的 `text` 字段对单条推文通常够用，但**也不带 thread**。仅在 fxtwitter 失败时使用。

## 验证清单

- [ ] fxtwitter 响应里 `tweet` 字段存在（不是 `code != 200`）
- [ ] 如果是 Article，`tweet.article.content.blocks` 是非空 list
- [ ] blocks_to_md 编译后行数 ≥ 5，字符数 ≥ 500（太短可能抽取失败）
- [ ] 原始 URL 已记入 prompt 末尾（让 DeepSeek 在资源区引用）
- [ ] 二次创作的真实案例已在 prompt 中给出（避免 AI 原文照搬）
