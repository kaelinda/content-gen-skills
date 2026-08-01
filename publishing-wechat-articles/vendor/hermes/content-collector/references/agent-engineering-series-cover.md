# Agent 工程化系列公众号封面:布局决策表 + 已知坑

> Author: Hermes Agent
> Last verified: 2026-06-16 (Vol.09 cobi → Vol.14 Mortyx,14 个 cover 实战)
> 配套模板: `templates/cover-agent-engineering-series.html`(已用 Vol.12 验证)
> 配套 SKILL: `productivity/content-collector`

## 默认布局(known-good,不要再改)

| 元素 | left | top | right | width | font-size |
|---|---|---|---|---|---|
| series-tag | 80px | 50px | - | auto | 18px |
| **title** | 80px | 130px | 80px (短)/ 320px (长) | - | 78px (短) / 60px (长) |
| subtitle | 80px | 330px (短) / 300px (长) | - / 320px (长) | - | 22px |
| **code-card** | - | 110px | 40px | 300px | 14px |
| meta | 80px | bottom 50px | - | auto | 16px |

## 字号决策(核心)

**短标题(line1 + line2 中文 ≤ 10 字)** → 用默认 78px + title right 80px,code card 默认 40/300
**长标题(line1 + line2 > 10 字,或 line1 > 8 字)** → 60px + title right **320px** + code card top 上提到 110px,subtitle 也 right 320px

判断阈值很关键。**Dami 那个 cover 一开始用 line1 "22 秒解决 20 分钟老问题:"(13 字)→ 78px 直接被 code card 切到 "老同"**。改成 line1 "22 秒 vs 20 分钟:"(9 字) + 60px + right 320px,问题解决。

## 2 个反复踩的坑(模板里已修 default)

### 坑 1:code card 跟 title 区域重叠

**症状**:title line1 末尾 1-2 个字被 code card 遮挡
**根因**:code card 默认 right 60 / top 130 / width 320 → 太靠左 + 太靠上
**正解**:code card right **40** / top **110** / width **300**(已写入 default 模板)
**老模板位置**:Vol.06-09 都有这个 bug,改用模板就修

### 坑 2:code card 列表项编号重复("1. 1. Skill Map")

**症状**:渲染后看到 `1. 1. Skill Map` / `2. 2. Boundaries` 这种
**根因**:模板里既有 `<span class="kw">N.</span>` 又有 line 文本开头的 "1. Skill Map",两个编号叠在一起
**正解**:删掉 `<span class="kw">N.</span>` 前缀(已写入 default 模板)
**触发**:`hermes skills create` 第一次跑 cover 渲染时,务必视觉验证一次,看到重复编号就 patch

## 5 marker 替换 + 1 个长标题调整清单

每次生成新 cover 时的 6 步:

1. **拷贝模板** → `/tmp/cover_volNN.html`
2. **替换 6 个 marker**:
   - SERIES_TAG_LABEL / SERIES_VOL_NUM(系列标签 + 卷号)
   - TITLE_LINE_1 / TITLE_LINE_2(主标题两行)
   - SUBTITLE(副标题)
   - AUTHOR_META_1/2/3(作者元信息)
   - CODE_SNIPPET_HEADER + 5 个 CSNIPPET_LINE(代码卡片内容)
3. **长标题检测**:line1+line2 中文 > 10 字?
   - 是 → 改 3 处 CSS:title font-size 78→60px, title right 80→320px, subtitle right 80→320px
   - 否 → 跳过
4. **Playwright 渲染**:1200×514, device_scale_factor=2 → 2400×1028 PNG
5. **上传 OSS**:bucket=kaelblog, key=`wechat/cover-{author}-{topic}-vol{NN}-{date}.png`
6. **发布前视觉验证**(必做,见下)

## 发布前视觉验证 checklist(必做,3 个必查)

用 `vision_analyze` 渲染后必查 3 个点,任何一个没过就重做:

- [ ] **标题不被遮挡** — title line1 末尾 1-2 字清晰可见,不被 code card 切
- [ ] **code card 列表项编号不重复** — 没有 "1. 1." / "2. 2." 这种
- [ ] **中文渲染正常** — 字体清晰,无方框乱码

**真实失败案例**:
- Vol.10 Vox:code card 遮挡 title "集合**了**" → 把 default 改为 right 40/width 300(已修)
- Vol.10 Vox:列表项 "1. 1. Skill Map" → 删 kw prefix(已修)
- Vol.12 Dami:title "20 分钟老**同**" 被切 → 改 line1 长度 + 字号 60px + right 320px

### Vision API 不可用时的 fallback(Vol.14 实战 2026-06-16)

`vision_analyze` 和 `browser_vision` 可能返回 401 auth error(API key 过期/未配置)。**这是服务不可用,不是内容问题** — 区别对待:

- **vision 发现内容问题**(标题被遮、编号重复) → 必须修,不抱侥幸
- **vision 服务不可用**(401/timeout/500) → 走 fallback,不阻塞发布

Fallback 流程(当 vision 不可用时):
1. 对照上方「默认布局」表格逐项检查 CSS 值是否匹配 known-good 规则
2. 确认长标题模式:line1+line2 > 10 字 → font-size 60px + title right 320px + subtitle right 320px
3. 确认 code card:right 40 / top 110 / width 300,无 kw 前缀
4. 确认 PNG 文件大小 > 500KB(渲染成功的信号;< 100KB 可能为空白页)
5. 全部通过 → 上传 OSS 并发布,不等 vision 恢复

Vol.14 Mortyx 就是走 fallback 发的:60px 长标题 + right 320px + 模板默认 code card,无 vision 验证,发布正常。

## code card 内容设计

5 行 code snippet 是封面"信息密度第二高"的地方(仅次于标题)。3 个设计原则:

- **第 1 行(HEADER)**:用 `#` 注释,1 行总结主题(如 `# skill library · 5-layer + V1 6-things`)
- **第 2-4 行(主体)**:列文章的 3-4 个最核心模块/特性,**用 line class**(灰色)
- **第 5 行(HIGHLIGHT)**:用 hl class(黄色) + `→` 箭头,放最想读者记住的 takeaway
- **不要重复标题里的关键词**(分散注意力)

## 跨卷连贯性(系列感)

12 卷 (Vol.01-12) 都需要保持系列感。3 个不变量:

- **series-tag** 永远是 "Agent 工程化系列" + "Vol.NN" 粉色
- **meta** 永远是作者 @handle + Hermes Agent + 发布日期
- **code card 视觉**(5 行 + 黄色 highlight 末行)永远不变,变的是内容

变的是:

- **TITLE_LINE_1/2** 每卷一个新钩子
- **CODE_SNIPPET_HEADER + 5 行** 每卷对应文章核心结构
- **SUBTITLE** 每卷新副标题

## 字号 vs title 长度的实际映射表

| title 总字数(line1+line2 中文) | font-size | title right | code card top | subtitle top |
|---|---|---|---|---|
| ≤ 10 字 | 78px | 80px | 110px | 330px |
| 11-14 字 | 60px | 320px | 110px | 300px |
| 15-18 字 | 50px | 360px | 80px | 280px |
| > 18 字(不推荐) | 重写 | - | - | - |

**18 字以上的标题应该重写,不要靠压字号解决** — 压到 < 50px 在手机端看不清。
