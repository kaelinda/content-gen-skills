#!/usr/bin/env python3
"""Banned word scan for tech articles.

Usage: python3 banned_word_scan.py <article.md>

Scans the FULL file (not just ===CONTENT=== section) for banned phrases
and weak modifiers. Reports count per pattern + structural stats
(Chinese chars, total chars, links, h3 sections).

Patterns covered:
- AI-style sentence patterns: 不是X而是Y, 与其X不如Y, 首先...其次...最后
- High-frequency AI words: 值得注意的是, 总的来说, 在当今, 不可否认, etc.
- Weak modifiers: 大概, 可能, 应该, 似乎
- Empty modifiers: 非常, 十分, 极其, 相当, 真正

Critical: scan the WHOLE file, not just ===CONTENT===, because banned
phrases can hide in ===TITLE=== / ===COVER_PROMPT=== sections (2026-06-15 bug).
"""
import re
import sys

BANNED_PATTERNS = [
    # AI 句式
    (r'不是[^，。]+[，,]而是', '不是X，而是Y'),
    (r'与其[说]?(?:[^，。]+)[，,]不[如说]', '与其X，不如Y'),
    # 高频 AI 味词
    (r'首先.*其次.*最后', '首先...其次...最后'),
    (r'值得注意的是', '值得注意'),
    (r'总的来说', '总的来说'), (r'总而言之', '总而言之'), (r'综上所述', '综上所述'),
    (r'在当今', '在当今'), (r'不可否认', '不可否认'),
    (r'众所周知', '众所周知'), (r'显而易见', '显而易见'),
    (r'不难发现', '不难发现'), (r'不言而喻', '不言而喻'),
    (r'毋庸置疑', '毋庸置疑'), (r'毫无疑问', '毫无疑问'),
    (r'正如我们所知', '正如我们所知'), (r'需要指出的是', '需要指出的是'),
    # 弱化语气
    (r'(?<!\w)大概(?!\w)', '大概'), (r'(?<!\w)似乎(?!\w)', '似乎'),
    (r'一定程度上', '一定程度上'), (r'或多或少', '或多或少'),
    # 模糊词
    (r'(?<!\w)可能(?!\w)', '可能'), (r'(?<!\w)应该(?!\w)', '应该'),
    # 空洞修饰（lookahead 用 \w 单反斜杠，\\w 是字面量 bug）
    (r'(?<!\w)非常(?!\w)', '非常'), (r'(?<!\w)十分(?!\w)', '十分'),
    (r'(?<!\w)极其(?!\w)', '极其'),
    (r'(?<!\w)相当(?=的|大|重要|高|多|复杂|困难|简单)', '相当(空洞修饰)'),
    (r'(?<!\w)真正(?!\w)', '真正'),
]


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 banned_word_scan.py <article.md>")
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()

    # Strip code blocks (```...``` and `inline code`) before scanning
    # to avoid false positives on prompt examples inside code (2026-06-20)
    code_free = re.sub(r'```[\s\S]*?```', '', content)
    code_free = re.sub(r'`[^`\n]+`', '', code_free)  # inline code

    # Find banned words (scan code-free version)
    hits = []
    for pattern, label in BANNED_PATTERNS:
        matches = re.findall(pattern, code_free)
        if matches:
            hits.append((label, len(matches), matches))

    if hits:
        print("❌ Banned words found:")
        for label, count, matches in hits:
            # Show first match in context for debugging
            preview = matches[0] if isinstance(matches[0], str) else matches[0][0]
            print(f"  {label}: {count} occurrences | first: {preview[:60]}")
        sys.exit(1)
    else:
        print("✅ No banned words found")

    # Stats (use code_free for heading count to skip code block comments)
    chinese = len(re.findall(r'[\u4e00-\u9fff]', content))
    links = re.findall(r'https?://[^\s)]+', content)
    h2 = len(re.findall(r'^## ', code_free, re.M))
    h3 = len(re.findall(r'^### ', code_free, re.M))
    sep = content.count('---')

    print(f"\nChinese: {chinese} | Total: {len(content)} | Links: {len(links)} | h2: {h2} | h3: {h3} | ---: {sep}")

    # Sweet spot warning
    if 3000 <= chinese <= 4000:
        print("✅ Chinese char count in sweet spot (3000-4000)")
    elif chinese < 3000:
        print(f"⚠️  Chinese char count {chinese} below sweet spot (target: 3000-4000)")
    elif chinese > 4500:
        print(f"⚠️  Chinese char count {chinese} above sweet spot (target: 3000-4000)")


if __name__ == "__main__":
    main()