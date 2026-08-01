# 飞书 Bitable 字段类型 & 长度限制(实战沉淀)

2026-05 / 2026-06 多次实战中确认的飞书 Bitable 字段类型与限制,适用于「长文表」「GitHub项目表」「AINews表」三类内容收录表。

## 字段类型速查

| ui_type | type | 写入格式 | 典型字段 | 限制 |
|---|---|---|---|---|
| `Text` | 1 | 字符串 | 标题/来源/原文/发布标题/公众号/发布内容/封面/附件链接/小红书 | **单字段 ≤ 5000 字符**(实际 4800 字符以下安全,接近上限会被截断) |
| `MultiSelect` | 4 | 数组,值必须 match 已存在的 option_name | 标签 | option 由表 owner 预设,新增 option 需走元数据 API |
| `Date` | 5 | 毫秒时间戳(数字,不是字符串) | 创建日期 | — |
| `Checkbox` | 7 | boolean | 是否已发布 | — |
| `Attachment` | 17 | 需走单独的 attachment API,不支持直接 PUT | 附件 | — |
| `HyperLink` | 15 | `{"link": "url", "text": "显示文本"}` | 部分表的「来源」可能是此类型 | **必须先查 fields,不能默认按 URL 字符串传** |

## 关键 pitfall

1. **「来源」字段类型不固定**。长文表是 type=1 纯文本,直接传 URL 字符串;但其他表(如 GitHub项目表)的「来源」可能 type=15 超链接,需传 `{"link":..., "text":...}`。**写入前先 `lark-cli api GET ".../tables/{table_id}/fields?page_size=100" --as user`** 确认每个字段类型,不要凭印象。

2. **「原文」字段 5000 字符上限**(2026-06-05 cobi/hermes-desktop 案例实测)。长文 12147 字符,直接 POST 写入会被截断/报 8001。处理:
   - 截断到 ~4800 字符 + 末尾加 `...(完整原文见附件 OSS)` 标记
   - 完整 markdown 落 Obsidian `raw/articles/` 作为不可变源
   - 飞书记录的「原文」字段当作「摘要 + 索引」用,不当完整存档

3. **「封面」字段是 type=1 纯文本**(2026-06-05 发现),不是附件。需要先上传封面图到 OSS,拿到公网 URL,再把 URL 字符串作为字段值。旧 skill 的必填字段列表没列出此项,2026-06-05 才从 GET fields 返回的 12 个字段中确认。

4. **「标签」是 MultiSelect**(type=4),传数组,值必须 match 已存在的 option_name(不是 option_id)。例:`"标签": ["Hermes", "Agent工具链"]`。写错的 option_name 会被静默忽略或报 option not found,**建议先查表已有的 option 列表**。

5. **「是否已发布」是 Checkbox**(type=7),传 boolean:`"是否已发布": false`。

## 必填字段集合(2026-06-05 长文表最新验证)

12 个字段完整清单(从 GET fields 拿到):

```
fldxxxxx  标题              type=1  Text
fldxxxxx  来源              type=1  Text
fldxxxxx  标签              type=4  MultiSelect
fldPhPOi5P 原文              type=1  Text  (≤ 5000 chars)
fldxxxxx  发布标题          type=1  Text
fldKNMlG9V 发布内容          type=1  Text  (≤ 5000 chars)
fldaAJW0WO 小红书            type=1  Text
fldUmGmkGg 公众号            type=1  Text  (≤ 5000 chars)
fldl0sMG4z 附件              type=17 Attachment
fldppcZDbB 附件链接          type=1  Text
fld6LhX6GA 封面              type=1  Text  (OSS URL)
fldCiWKe6S 是否已发布        type=7  Checkbox
```

**实际写入必填集** (创建时如果都填,后续无需补):标题 + 来源 + 标签 + 原文 + 发布标题 + 公众号 + 发布内容 + 封面。附件/附件链接/小红书/是否已发布可选。

## 字段名区分大小写

**字段名必须精确匹配大小写和字符**(中文标点也算)。长文表的「原文」是「原文」不是「原文内容」,写错会报 `FieldNameNotFound`。**永远以 GET fields 返回的 `field_name` 字段为准,不要猜测**。

## 写入 JSON 大小限制(shell 层面)

单次 PUT 整个 JSON body 实测 ≤ 25KB 没问题。超过 30KB 时,`lark-cli` 可能报 shell 参数过长或 stdin 管道被截断,此时改用 `cat file | lark-cli api PUT ... --data -` 走 stdin 管道(对 `api` 子命令有效,对 `im +messages-send` 无效)。

## 案例参考

- 2026-06-03 Agent 工程化 Vol.06 (SkillOpt,3853 中文字符):POST 创建 + PUT 补「封面」,2 次 round-trip
- 2026-06-04 Agent 工程化 Vol.07 (Debug Mode,2881 中文字符):1 次 POST 创建带封面,1 次成功
- 2026-06-05 Hermes Desktop Vol.09 (cobi/hermes-desktop masterclass,2275 中文字符):1 次 POST 创建 + 1 次 PUT 补封面/公众号/发布内容/发布标题(把 4 个字段一起 PUT 比拆 2 次更省 round-trip)
