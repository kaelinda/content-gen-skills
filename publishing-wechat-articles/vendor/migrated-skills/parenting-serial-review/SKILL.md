---
name: parenting-serial-review
description: 每30分钟一篇串行复审育儿九稿并向 hermes-ali-ecs 发送修订版。
---

# parenting-serial-review

## 工作空间
- 队列与脚本：`<local-path>s/MyCode/services/hermes-agent/outputs/parenting-serial-review/queue.json`
- 每篇独立子目录 `01/…10/`，含 `original.md`、`article.md`、`editor-notes.md`、`cover.png`、`audit.md`、`audit.json`、`html/article.html`、`receipt.json`、`delivery-readback.json`
- 原始素材保持只读；下载目录 `<local-path>s/parenting-nine-drafts` 仅做核对，不修改
- 上一份编辑报告备份为 `previous-editorial-review.md`

## 调度节奏
- 周期：30 分钟/篇，调度表达式 `*/30 * * * *`；相邻实际发送至少 1800 秒
- 不并发、不补发追赶；首项 `pending` 才处理，已 sent 或 blocked 不重审
- `run.lock` 是单实例锁；进入时原子 mkdir，结束 rmdir；遇锁直接结束本轮
- 失败不擅自删锁，必须人工确认无活跃运行后再清理

## 每轮必须执行的步骤
1. 进入锁 → 读 queue.json → 判断首项与节流（1800 秒）→ 记录 reviewing、started_at
2. 加载 skills：`parenting-content-writer`、`parenting-content-audit`、`dbs-ai-check`、`parenting-wechat-publish`（含 references/wechat-aigc-compliance.md）、`productivity/md-to-html`、`lark-cli`、`aliyun-oss-upload`；必要时加载 `ego-browser` 做手机端布局检查
3. 通读本篇 original/article/editor-notes 与 previous-editorial-review.md；逐条执行五大维度（正向基调、科学准确性、实操性、AI 味、AIGC 合规）
4. 真实性与隐私硬门槛：
   - 9 篇先前均标 `author_review_required`，含占位场景/台词/统计，无作者确认记录 → 不认定真实、不擅自改写为建议稿、不擅自删除占位改写事实
   - 09 篇涉及可识别邻居儿童隐私 → 必须作者出具同意记录，否则标 blocked
   - 不能用“典型情境/通用建议”等措辞替换真实经历，绕过确认
5. 可做轻量编辑：错字、引用补充、排版、空泛模板化措辞；保留原稿事实
6. 通过后再生成橙心 HTML → 校验 DOM 表格行/列 → 320/375/390/430px 无溢出 → 删 `## 📌 发布备注` 段落
7. 上传 HTML 到 OSS：`parenting/serial-review/{id}/article.html`，封面复用既有 OSS URL；unset 代理后 GET 回读比对 SHA256
8. lark-cli `--as user --chat-id <redacted-id>` 单条消息发送；`--idempotency-key parenting-nine-revised-{id}` 防重；消息包含“育儿育己｜复审修订版”标记、标题、摘要、封面 OSS URL、HTML OSS URL、简短审核结论，明确“仅人工预览，不授权自动发表或群发”
9. 回读 `GET /open-apis/im/v1/messages/{message_id}` 匹配目标 chat、deleted=false，body.content 与原消息精确比对；回读通过后才标 sent
10. 原子替换写回 queue.json；最终回复只汇报本篇实际结果/阻塞，不在飞书批量倾倒审核报告

## 决策表
| decision | queue.status | 动作 |
|---|---|---|
| `approved_for_feishu` | sent | 正常发飞书并回读 |
| `needs_author_confirmation` | blocked | 记录待确认清单，本轮不发 |
| `needs_revision` | blocked | 列可编辑项，等作者决定 |
| `delivery_unverified` | delivery_unverified | 已发但回读失败；不重发，后续回读 |

## 禁手
- 在一个调度周期处理多篇
- 跳过审核直接发、跳过 OCR/DOM 校验、跳过回读
- 把 AI 痕迹/“典型情境”当作已确认真实经历
- 09 篇未取得同意即发送
- 把旧批次 sent 当作本轮修订版已发
- 把 lark-cli 送达等同于公众号发表
