# HTML Cover Image Templates

Ready-to-use HTML templates for WeChat cover images (1200×514, 20:9).

## Template 1: Dark Tech Gradient (通用科技风格)

Works well for: AI, Claude, settings, developer tools, productivity.

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: 1200px; height: 514px;
  background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
  display: flex; align-items: center; justify-content: center;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  overflow: hidden; position: relative;
}
.bg-pattern {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: 
    radial-gradient(circle at 20% 50%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
    radial-gradient(circle at 80% 30%, rgba(168, 85, 247, 0.12) 0%, transparent 40%),
    radial-gradient(circle at 60% 80%, rgba(59, 130, 246, 0.1) 0%, transparent 40%);
}
.grid {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
}
.content {
  position: relative; z-index: 10; text-align: center; padding: 0 80px;
}
.badge {
  display: inline-block; 
  background: rgba(167, 139, 250, 0.2); 
  border: 1px solid rgba(167, 139, 250, 0.4);
  color: #c4b5fd; font-size: 18px; font-weight: 600;
  padding: 6px 20px; border-radius: 20px; margin-bottom: 24px;
  letter-spacing: 2px;
}
h1 {
  color: #fff; font-size: 52px; font-weight: 800;
  line-height: 1.3; margin-bottom: 20px;
  text-shadow: 0 2px 20px rgba(0,0,0,0.3);
}
h1 .num { color: #a78bfa; }
.subtitle {
  color: rgba(255,255,255,0.6); font-size: 22px; font-weight: 400;
  letter-spacing: 1px;
}
</style>
</head>
<body>
  <div class="bg-pattern"></div>
  <div class="grid"></div>
  <div class="content">
    <div class="badge">BADGE TEXT</div>
    <h1>Title with <span class="num">Highlight</span></h1>
    <div class="subtitle">Subtitle text here</div>
  </div>
</body>
</html>
```

## Template 2: Green Trust (安全/信任/质量)

Works well for: code quality, trust layers, security, testing, review workflows.
Accent color: `#6ee7b7` (green) / `#10b981` (emerald).

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: 1200px; height: 514px;
  background: linear-gradient(135deg, #0c1a2e, #1a2f4b, #0d2137);
  display: flex; align-items: center; justify-content: center;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  overflow: hidden; position: relative;
}
.bg-pattern {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: 
    radial-gradient(circle at 15% 60%, rgba(16, 185, 129, 0.12) 0%, transparent 50%),
    radial-gradient(circle at 85% 30%, rgba(59, 130, 246, 0.1) 0%, transparent 40%),
    radial-gradient(circle at 50% 90%, rgba(239, 68, 68, 0.08) 0%, transparent 40%);
}
.grid {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
  background-size: 60px 60px;
}
.content {
  position: relative; z-index: 10; text-align: center; padding: 0 80px;
}
.badge {
  display: inline-block; 
  background: rgba(16, 185, 129, 0.15); 
  border: 1px solid rgba(16, 185, 129, 0.35);
  color: #6ee7b7; font-size: 16px; font-weight: 600;
  padding: 6px 20px; border-radius: 20px; margin-bottom: 24px;
  letter-spacing: 2px;
}
h1 {
  color: #fff; font-size: 48px; font-weight: 800;
  line-height: 1.3; margin-bottom: 16px;
  text-shadow: 0 2px 20px rgba(0,0,0,0.3);
}
h1 .highlight { color: #6ee7b7; }
.subtitle {
  color: rgba(255,255,255,0.55); font-size: 20px; font-weight: 400;
  letter-spacing: 1px; line-height: 1.5;
}
/* Tag pills: use .layer.green / .layer.yellow / .layer.red / .layer.blue */
.layers {
  display: flex; justify-content: center; gap: 16px; margin-top: 20px;
}
.layer {
  padding: 6px 16px; border-radius: 10px; font-size: 14px; font-weight: 500;
}
.layer.green { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); color: #6ee7b7; }
.layer.yellow { background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.25); color: #fcd34d; }
.layer.red { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5; }
.layer.blue { background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.25); color: #93c5fd; }
</style>
</head>
<body>
  <div class="bg-pattern"></div>
  <div class="grid"></div>
  <div class="content">
    <div class="badge">BADGE TEXT</div>
    <h1>Title <span class="highlight">Highlight</span></h1>
    <div class="subtitle">Subtitle</div>
    <div class="layers">
      <span class="layer green">Tag 1</span>
      <span class="layer blue">Tag 2</span>
      <span class="layer yellow">Tag 3</span>
      <span class="layer red">Tag 4</span>
    </div>
  </div>
</body>
</html>
```

## Template 3: Purple Framework (系统设计/架构/方法论)

Works well for: agent frameworks, system design, architecture, methodology.
Accent color: `#c084fc` (purple) / `#a78bfa` (violet).

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: 1200px; height: 514px;
  background: linear-gradient(135deg, #1a0a2e, #2d1b4e, #1a1040);
  display: flex; align-items: center; justify-content: center;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  overflow: hidden; position: relative;
}
.bg-pattern {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: 
    radial-gradient(circle at 25% 40%, rgba(139, 92, 246, 0.15) 0%, transparent 50%),
    radial-gradient(circle at 75% 60%, rgba(236, 72, 153, 0.1) 0%, transparent 40%),
    radial-gradient(circle at 50% 90%, rgba(59, 130, 246, 0.08) 0%, transparent 40%);
}
.grid {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 60px 60px;
}
.content {
  position: relative; z-index: 10; text-align: center; padding: 0 60px;
}
.badge {
  display: inline-block; 
  background: rgba(139, 92, 246, 0.2); 
  border: 1px solid rgba(139, 92, 246, 0.4);
  color: #c4b5fd; font-size: 16px; font-weight: 600;
  padding: 6px 20px; border-radius: 20px; margin-bottom: 20px;
  letter-spacing: 2px;
}
h1 {
  color: #fff; font-size: 42px; font-weight: 800;
  line-height: 1.3; margin-bottom: 16px;
  text-shadow: 0 2px 20px rgba(0,0,0,0.3);
}
h1 .highlight { color: #c084fc; }
h1 .green { color: #6ee7b7; }
.subtitle {
  color: rgba(255,255,255,0.55); font-size: 19px; font-weight: 400;
  letter-spacing: 1px; line-height: 1.5;
}
/* Numbered step pills */
.steps {
  display: flex; justify-content: center; gap: 14px; margin-top: 18px;
}
.step {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.65);
  padding: 5px 14px; border-radius: 10px;
  font-size: 13px; font-weight: 500;
}
.step .num { color: #c084fc; font-weight: 700; margin-right: 4px; }
</style>
</head>
<body>
  <div class="bg-pattern"></div>
  <div class="grid"></div>
  <div class="content">
    <div class="badge">BADGE TEXT</div>
    <h1>Title with <span class="highlight">Highlight</span></h1>
    <div class="subtitle">Subtitle</div>
    <div class="steps">
      <span class="step"><span class="num">①</span>Step 1</span>
      <span class="step"><span class="num">②</span>Step 2</span>
      <span class="step"><span class="num">③</span>Step 3</span>
    </div>
  </div>
</body>
</html>
```

## Template 4: Blue Productivity (工具/产品/工作流)

Works well for: Codex, Claude Code, productivity tools, workflow tips.
Accent color: `#38bdf8` (sky blue) / `#7dd3fc` (light blue).

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: 1200px; height: 514px;
  background: linear-gradient(135deg, #0a1628, #162d50, #0d1f3c);
  display: flex; align-items: center; justify-content: center;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  overflow: hidden; position: relative;
}
.bg-pattern {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: 
    radial-gradient(circle at 30% 40%, rgba(56, 189, 248, 0.12) 0%, transparent 50%),
    radial-gradient(circle at 70% 70%, rgba(16, 185, 129, 0.1) 0%, transparent 40%),
    radial-gradient(circle at 85% 20%, rgba(245, 158, 11, 0.08) 0%, transparent 35%);
}
.grid {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 60px 60px;
}
.content {
  position: relative; z-index: 10; text-align: center; padding: 0 60px;
}
.badge {
  display: inline-block; 
  background: rgba(56, 189, 248, 0.15); 
  border: 1px solid rgba(56, 189, 248, 0.35);
  color: #7dd3fc; font-size: 16px; font-weight: 600;
  padding: 6px 20px; border-radius: 20px; margin-bottom: 20px;
  letter-spacing: 2px;
}
h1 {
  color: #fff; font-size: 46px; font-weight: 800;
  line-height: 1.3; margin-bottom: 16px;
  text-shadow: 0 2px 20px rgba(0,0,0,0.3);
}
h1 .highlight { color: #38bdf8; }
.subtitle {
  color: rgba(255,255,255,0.55); font-size: 19px; font-weight: 400;
  letter-spacing: 1px; line-height: 1.5;
}
.roles {
  display: flex; justify-content: center; gap: 14px; margin-top: 20px;
}
.role {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.65);
  padding: 5px 14px; border-radius: 10px;
  font-size: 14px; font-weight: 500;
}
</style>
</head>
<body>
  <div class="bg-pattern"></div>
  <div class="grid"></div>
  <div class="content">
    <div class="badge">BADGE TEXT</div>
    <h1>Title <span class="highlight">Highlight</span></h1>
    <div class="subtitle">Subtitle</div>
    <div class="roles">
      <span class="role">🔥 Role 1</span>
      <span class="role">📊 Role 2</span>
      <span class="role">🧠 Role 3</span>
    </div>
  </div>
</body>
</html>
```

## Template 5: GitHub Dark (开发者工具/终端/CLI)

Works well for: developer tools, CLI tools, terminal-based workflows, coding agents.
Accent color: `#7ee787` (GitHub green) / `#79c0ff` (GitHub blue).
Includes a faint terminal code block in background for tech atmosphere.

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: 1200px; height: 514px;
  background: linear-gradient(135deg, #0d1117, #161b22, #0d1117);
  display: flex; align-items: center; justify-content: center;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', 'JetBrains Mono', monospace;
  overflow: hidden; position: relative;
}
.bg-pattern {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: 
    radial-gradient(circle at 20% 50%, rgba(136, 255, 136, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 80% 30%, rgba(88, 166, 255, 0.06) 0%, transparent 40%);
}
.grid {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
  background-size: 50px 50px;
}
.terminal {
  position: absolute; left: 50px; bottom: 40px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px; color: rgba(136, 255, 136, 0.12);
  line-height: 1.6; white-space: pre;
}
.content {
  position: relative; z-index: 10; text-align: center; padding: 0 60px;
}
.badge {
  display: inline-block; 
  background: rgba(136, 255, 136, 0.12); 
  border: 1px solid rgba(136, 255, 136, 0.3);
  color: #88ff88; font-size: 15px; font-weight: 600;
  padding: 6px 20px; border-radius: 20px; margin-bottom: 22px;
  letter-spacing: 3px; font-family: 'JetBrains Mono', monospace;
}
h1 {
  color: #e6edf3; font-size: 48px; font-weight: 800;
  line-height: 1.3; margin-bottom: 16px;
  text-shadow: 0 2px 20px rgba(0,0,0,0.5);
}
h1 .green { color: #7ee787; }
h1 .blue { color: #79c0ff; }
.subtitle {
  color: rgba(230,237,243,0.5); font-size: 19px; font-weight: 400;
  letter-spacing: 1px; line-height: 1.5;
}
.arch {
  display: flex; justify-content: center; gap: 16px; margin-top: 20px;
}
.arch-item {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: rgba(230,237,243,0.6);
  padding: 5px 14px; border-radius: 8px;
  font-size: 13px; font-weight: 500;
  font-family: 'JetBrains Mono', monospace;
}
</style>
</head>
<body>
  <div class="bg-pattern"></div>
  <div class="grid"></div>
  <div class="terminal">$ command --flag
$ install package-name
$ config --set key=value</div>
  <div class="content">
    <div class="badge">BADGE TEXT</div>
    <h1>Title <span class="green">Highlight</span></h1>
    <div class="subtitle">Subtitle</div>
    <div class="arch">
      <span class="arch-item">📦 Item 1</span>
      <span class="arch-item">📝 Item 2</span>
      <span class="arch-item">📚 Item 3</span>
    </div>
  </div>
</body>
</html>
```

## Template 6: Split Layout with SVG Concept Diagram (概念可视化)

Works well for: articles whose core idea has a natural visual representation — loops, pipelines, flows, hierarchies, 2-axis matrices, cycles.
Layout: left = title block (badge + title + subtitle + author), right = inline SVG diagram of the concept.

**Why this exists:** Templates 1–5 are centered text blocks with tag pills. But this user's content (agent engineering, AI workflows) often features a concept that *is* a diagram — inner/outer loops, pipelines, feedback cycles. A cover that shows the diagram communicates the idea in 1 second; text-only covers don't.

**How to use:** Copy the template, then replace the SVG block (the `<svg>` inside `.diagram`) with whatever shape your concept needs:
- Loops / cycles → concentric circles with arrows (as shown)
- Pipeline → horizontal boxes connected by arrows
- Hierarchy → stacked rectangles (pyramid)
- 2-axis matrix → 2×2 grid with labeled quadrants
- Flow → diamond/decision shapes with branches

Keep the SVG viewBox at `0 0 380 380` and the `.diagram` container at `380×380px` so the layout math doesn't break.

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1200px; height: 540px;
    font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden;
    background: linear-gradient(135deg, #0a0a1a 0%, #12122a 40%, #0d1525 100%);
    position: relative;
  }
  .grid-bg {
    position: absolute; inset: 0;
    background-image:
      linear-gradient(rgba(80,100,180,0.06) 1px, transparent 1px),
      linear-gradient(90deg, rgba(80,100,180,0.06) 1px, transparent 1px);
    background-size: 40px 40px; opacity: 0.5;
  }
  .glow-1 {
    position: absolute; width: 400px; height: 400px;
    top: -100px; right: -50px;
    background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
    border-radius: 50%;
  }
  .glow-2 {
    position: absolute; width: 300px; height: 300px;
    bottom: -80px; left: 200px;
    background: radial-gradient(circle, rgba(16,185,129,0.1) 0%, transparent 70%);
    border-radius: 50%;
  }
  .container {
    position: relative; z-index: 10;
    display: flex; height: 100%; padding: 50px 60px;
  }
  .text-area {
    flex: 1; display: flex; flex-direction: column;
    justify-content: center; max-width: 700px;
  }
  .tag {
    display: inline-block;
    background: rgba(99,102,241,0.2);
    border: 1px solid rgba(99,102,241,0.4);
    color: #a5b4fc; font-size: 14px; font-weight: 700;
    padding: 6px 16px; border-radius: 20px;
    margin-bottom: 20px; width: fit-content; letter-spacing: 1px;
  }
  .title {
    font-size: 42px; font-weight: 900; color: #f8fafc;
    line-height: 1.3; margin-bottom: 16px; letter-spacing: -0.5px;
  }
  .title .highlight {
    background: linear-gradient(90deg, #818cf8, #c084fc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .subtitle {
    font-size: 18px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px;
  }
  .author { font-size: 14px; color: #64748b; margin-top: auto; }
  .author span { color: #818cf8; font-weight: 700; }
  .diagram {
    width: 380px; height: 380px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 20px;
  }
  .diagram svg { width: 100%; height: 100%; }
</style>
</head>
<body>
  <div class="grid-bg"></div>
  <div class="glow-1"></div>
  <div class="glow-2"></div>
  <div class="container">
    <div class="text-area">
      <div class="tag">BADGE TEXT</div>
      <div class="title">
        Main Title<br>
        <span class="highlight">Highlight Phrase</span>
      </div>
      <div class="subtitle">Subtitle line one<br>Subtitle line two</div>
      <div class="author">原文 / <span>Author Name</span> · 中文 / <span>Translator</span></div>
    </div>
    <!-- REPLACE THIS SVG WITH YOUR CONCEPT DIAGRAM -->
    <div class="diagram">
      <svg viewBox="0 0 380 380" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#a855f7;stop-opacity:0.8"/>
            <stop offset="100%" style="stop-color:#6366f1;stop-opacity:0.8"/>
          </linearGradient>
          <linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#10b981;stop-opacity:0.8"/>
            <stop offset="100%" style="stop-color:#059669;stop-opacity:0.8"/>
          </linearGradient>
        </defs>
        <!-- Outer loop -->
        <circle cx="190" cy="190" r="165" fill="none" stroke="url(#g1)" stroke-width="2.5" stroke-dasharray="8 4" opacity="0.6"/>
        <!-- Inner loop -->
        <circle cx="190" cy="190" r="95" fill="rgba(16,185,129,0.05)" stroke="url(#g2)" stroke-width="2.5"/>
        <!-- Labels -->
        <text x="190" y="195" text-anchor="middle" fill="#6ee7b7" font-size="18" font-weight="900" font-family="'Noto Sans SC',sans-serif">Concept A</text>
        <text x="190" y="25" text-anchor="middle" fill="#d8b4fe" font-size="14" font-weight="700" font-family="'Noto Sans SC',sans-serif">Concept B</text>
      </svg>
    </div>
  </div>
</body>
</html>
```

**Verified session:** 2026-06-18 Codex inner/outer loops cover. Title left, concentric dual-loop SVG right. 709KB PNG, 1200×540×2x. Used green/purple to match inner (fast/green) vs outer (slow/purple) semantics.

## Theme Selection Guide

| Content Theme | Template | Accent Color |
|---|---|---|
| AI 通用 / Claude / 设置 | T1 Dark Tech | Purple `#a78bfa` |
| 代码质量 / 信任 / 安全 | T2 Green Trust | Green `#6ee7b7` |
| 系统设计 / 架构 / 方法论 | T3 Purple Framework | Violet `#c084fc` |
| 工具 / 产品 / 工作流 | T4 Blue Productivity | Sky `#38bdf8` |
| 开发者工具 / CLI / 终端 | T5 GitHub Dark | Green `#7ee787` |
| 概念可视化 / 循环 / 流程 / 层级 | T6 Split+SVG | Multi (green+purple) |
| 知识系统 / 方法论 / 概念对比 (N rules / N 步类) | T7 Knowledge System Diagram | Indigo/Pink `#a5b4fc`+`#ec4899` |

## Template 7: Knowledge System Diagram (知识系统 / 方法论 主题)

`templates/cover-knowledge-system-diagram.html`

适合 "X rules" / "X 步" / "N 维心智模型" 类文章。**左侧标题 + 右侧信息卡 + 大数字水印**，信息密度比 T1-T5 更高，数字突出。

**为什么独立成模板**：T1-T6 都不是"信息密集型"封面（只有标题+几个 tag pill）。但知识系统/方法论文章的核心信息是**结构本身**——比如 Karpathy LLM Wiki 模式，三层所有权是核心论点，"9 rules"是核心数字——一个普通 cover 完全传达不了这种密度。

**Layout 决策**（已验证，2026-06-27 LLM Second Brain cover）：
- 左侧：badge + 标题（带 highlight） + 双行副标题 + 底部 3 个 meta pill
- 右侧：暗色透明 card，**第一组 3 个 layer（带 owner 区分）+ 中间分隔箭头 + 第二组 2 个对比 row**
- **大数字水印**（如 "9"）放在 card 内右下角，用 `rgba(236, 72, 153, 0.85)` 紫红色 + 90px 字号

**实测案例（2026-06-27 LLM Second Brain Karpathy）**：
- 标题"让你的 Obsidian vault 自己维护自己" (60px / 紫粉渐变 highlight)
- 副标题 "Karpathy 的 9 rules + 10 步实操 / 把死掉的笔记堆变成会复利的第二大脑"
- 右侧 card 三层所有权 (`raw/` 你 / `wiki/` 模型 / `CLAUDE.md` 双方) + 编译 ≠ 检索
- 大数字 "9" 紫红水印
- 1MB PNG, vision 验证无遮挡, 飞书发布成功

**已知坑**（必须遵守的 layout 约束）：
- title 用 `right: 380px`（不能是 60/80，会跟 card 重叠）
- card 用 `right: 60px / width: 300px`（不是 320，320 会遮挡长标题）
- 大数字放在 **card 内右下角** 不是 card 外（避免压到底部 meta）
- highlight 颜色用 `#a5b4fc → #ec4899` 渐变（不要纯白 + 单色高亮，对比度不够）

## Usage

1. Write HTML to `/tmp/cover_xxx.html`
2. `browser_navigate(url="file:///tmp/cover_xxx.html")`
3. `browser_vision(question="Take a screenshot")`
4. Upload screenshot to OSS via aliyun-oss-upload
5. Use OSS URL as cover image in publish request

## Customization Tips

- Long titles (>15 chars): reduce `h1 { font-size }` to 40-44px
- Many tag pills (5+): reduce font-size to 12-13px and gap to 10-12px
- Decorative emoji: use `.emoji-bg` class with low opacity (0.05-0.08) for background decoration
- Terminal code: use `.terminal` class for developer-focused covers, keep opacity low
