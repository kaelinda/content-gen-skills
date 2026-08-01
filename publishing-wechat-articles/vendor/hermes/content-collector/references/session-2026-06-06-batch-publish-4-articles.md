# Session 2026-06-06: 4 公众号文章批量收录+发布

本次会话的完整工作流,作为未来同类任务的"做过的 4 个完整例子"参考。

## 本次发布的 4 篇(都是 Agent 工程化系列,延续 Vol.06-10 主线)

| Vol | 来源 | 标题 | Record ID | OSS Cover |
|---|---|---|---|---|
| 09 | cobi @cobi_bean (11k+ 字 X Article) | "chat 是入口,desktop 才是工作台" | `recvlErjXANVJc` | `cover-cobi-hermes-desktop-vol09-2026-06-04.png` |
| — | Shann³ @shannholmberg (英文长推) | (未发公众号,仅收录+学习) | `recvlJeX1Da1VT` | — |
| 10 | Vox @Voxyz_ai (12k+ 字 X Article) | "90% 的人搭 skill 库,第一步就错了" | `recvlLqGRNu4zW` | `cover-voxyz-skill-library-vol10-2026-06-05.png` |
| 11 | Khairallah @eng_khairallah1 (12k+ 字 X Article) | "我用 Claude 3 年,90% 的人把它当文件夹用" | `recvlLtTlhGh59` | `cover-khairallah-claude-projects-vol11-2026-06-06.png` |

## 4 篇形成的内部串联(可作为 future content 的串联模板)

→ **Vol.09 (cobi)**:Hermes Desktop 让 1 个 agent 在桌面**被看见**(visibility)
→ **Shann (未发)** :5 层 agent 树 + client pod 隔离(组织)
→ **Vol.10 (Vox)**:怎么从 0 搭第一个 skill 库(judgment-heavy 起步)
→ **Vol.11 (Khairallah)**:怎么搭承载 skill 的 project context(6 part 蓝图)

**3 篇 Vol.09/10/11 + Shann = Agent 系统工程 4 篇完整体系**:
- 桌面可见性(cobi) + 组织可见性(Shann) + skill 库(Vox) + project context(Khairallah)
- 每篇都先建立 wiki 链接(双向 [[wikilinks]]),让 4 篇互为脚注

## 收尾金句模板(已用过的,未来可换)

- Vol.09:"把重复的事交给基础设施,把创造力留给自己"
- Vol.10:"把重复的事交给基础设施,把判断力留给 agent"
- Vol.11:"把重复的事交给基础设施,把判断力留给 agent"(沿用,3 篇系列收束一致)

**3 句统一收束**到「基础设施 + agent 创造力/判断力」这个二分。这是 series 强识别。

## 本次会话踩到的 2 个真实坑(已修进 skill)

1. **POST 飞书表 record_id 被 stdout[:1500] 截断丢失 → 再 POST 一次 → 3 条重复**
   - 已写进 SKILL.md Pitfall + 实测教训
2. **封面图模板有 2 个布局 bug**(code card 遮挡标题、列表项编号重复)
   - Vol.10 第一版中招,Vol.11 修模板并 pre-bake
   - 关键发现:必须 `vision_analyze` 视觉验证后再上传 OSS,文件大小正常不等于视觉正常
   - 已写进 SKILL.md Pitfall + 模板 HTML 注释

## 私发飞书 P2P 助理 chat_id 复用

`oc_cde2971ca05c08d8b36f4a3f86a6544a` (私人助理 P2P)
- 每次 post 1 + markdown 8-11 段,12/12 全成功
- 助理侧会负责把 cover image 从 OSS 拉取上传 公众号 media(已用过的 4 次全部回执 OK)
- 助理处理时间通常 5-15 分钟,发布完成会主动回执用户

## 公众号文章字数实测范围(主模型 MiniMax-M3 自写)

- Vol.09: 2275 中文字符 / 7250 总字符(8 段 markdown)
- Vol.10: 2348 中文字符 / 8608 总字符(10 段 markdown,加了「3.5 陷阱」)
- Vol.11: 2246 中文字符 / 9232 总字符(11 段 markdown,加了「6.5 真实坑」)

**经验值**:每次扩充内容 +300~500 中文字符时,会多出 1 段 markdown。**主模型自写 + 一次扩充到 2200-2500 中文字符 = 最佳性价比**;再扩收益递减(参考 Vol.10/11 都是一次扩充就停手)。

## 标题候选公式(本次 3 个 Vol 都用了同一公式)

- Vol.09: "chat 是入口,desktop 才是工作台:一个 4 个月 agent 用户的复盘"
- Vol.10: "90% 的人搭 skill 库,第一步就错了"
- Vol.11: "我用 Claude 3 年,90% 的人把它当文件夹用"

**共同公式**:**具体时间/数字 + 反常识/痛点 + 身份代入**(90% / 我用 X 年 / 第一个 / 错了)。

3 个候选标题的 offer 模式保留(给用户挑),但实际用户没换过,证明这套公式命中率高。

## 系列钩子(3 段连续句式)

每次开篇都用"假设 → 但其实"反转结构(参考 Vol.09 开篇)或"3 个原因 → 正解"列表结构(参考 Vol.11)。
**统一钩子长度 = 6-10 段**(过短没钩子力,过长读者跑掉)。

## 未来的 next-action 提示

如果用户继续 收录 → 发公众号 流程,这套 skill + 模板 + P2P 助理已经稳定可复用。**预计下次的"踩坑点"会是新的 X 媒体下载(被墙)或新的 lark-cli 接口变化**,这两个 SKILL.md 里都有 pitfall 兜底。
