#!/usr/bin/env python3
"""
Automated pre-publish audit for tech articles.

Runs all checkable dimensions programmatically:
  1. AI-style banned words (0 tolerance)
  2. Word count (sweet spot 3000-4000 Chinese chars)
  3. Link validity (HTTP HEAD check)
  4. Code block completeness (import, version, runnable)
  5. Structure validation (h2/h3 hierarchy, paragraph length)
  6. Image placeholder check (no broken ![alt](url) syntax)
  7. Horizontal rule check (--- breaks Feishu formatting)
  8. Frontmatter validation (if present)

Usage:
  python3 audit_auto.py <article.md>
  python3 audit_auto.py <article.md> --check-links    # include HTTP link checks (slower)
  python3 audit_auto.py <article.md> --json            # output JSON report
  python3 audit_auto.py <article.md> --output report.json  # save JSON to file

Exit codes:
  0 = all checks passed
  1 = errors found (blocking)
  2 = warnings only (non-blocking)

Tested: 2026-07-11
"""

import argparse
import json
import os
import re
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ── SSL for link checking ───────────────────────────────────────────────────
SSL_CTX = ssl._create_unverified_context()

# ── Banned Patterns (same as banned_word_scan.py) ──────────────────────────
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
    (r'(?<!\w)大概(?!\\w)', '大概'), (r'(?<!\w)似乎(?!\\w)', '似乎'),
    (r'一定程度上', '一定程度上'), (r'或多或少', '或多或少'),
    # 模糊词
    (r'(?<!\w)可能(?!\\w)', '可能'), (r'(?<!\w)应该(?!\\w)', '应该'),
    # 空洞修饰
    (r'(?<!\w)非常(?!\\w)', '非常'), (r'(?<!\w)十分(?!\\w)', '十分'),
    (r'(?<!\w)极其(?!\\w)', '极其'), (r'(?<!\w)相当(?!\\w)', '相当'),
    (r'(?<!\w)真正(?!\\w)', '真正'),
]

# ── Report Class ────────────────────────────────────────────────────────────

class AuditReport:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.checks = []
        self.errors = 0
        self.warnings = 0
        self.passed = 0

    def add(self, dimension: str, status: str, message: str, detail: str = ""):
        """Add a check result. status: pass / warn / error"""
        entry = {
            "dimension": dimension,
            "status": status,
            "message": message,
        }
        if detail:
            entry["detail"] = detail
        self.checks.append(entry)
        if status == "error":
            self.errors += 1
        elif status == "warn":
            self.warnings += 1
        else:
            self.passed += 1

    def summary(self) -> dict:
        return {
            "file": self.filename,
            "errors": self.errors,
            "warnings": self.warnings,
            "passed": self.passed,
            "total": len(self.checks),
            "verdict": "FAIL" if self.errors > 0 else ("WARN" if self.warnings > 0 else "PASS"),
        }

    def print_report(self):
        """Print human-readable report."""
        s = self.summary()
        print(f"\n{'='*60}")
        print(f"📋 Automated Audit Report")
        print(f"{'='*60}")
        print(f"File: {self.filename}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'─'*60}")

        # Group by dimension
        dims = {}
        for c in self.checks:
            d = c["dimension"]
            if d not in dims:
                dims[d] = []
            dims[d].append(c)

        for dim, checks in dims.items():
            icons = {"pass": "✅", "warn": "⚠️ ", "error": "❌"}
            dim_status = "pass"
            for c in checks:
                if c["status"] == "error":
                    dim_status = "error"
                    break
                elif c["status"] == "warn":
                    dim_status = "warn"
            print(f"\n{icons[dim_status]} {dim}")
            for c in checks:
                icon = icons[c["status"]]
                print(f"  {icon} {c['message']}")
                if c.get("detail"):
                    for line in c["detail"].split("\n")[:5]:
                        print(f"      {line}")

        print(f"\n{'─'*60}")
        verdict_icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
        print(f"{verdict_icon[s['verdict']]} Verdict: {s['verdict']} "
              f"({s['passed']} passed, {s['warnings']} warnings, {s['errors']} errors)")
        print(f"{'='*60}\n")


# ── Check Functions ─────────────────────────────────────────────────────────

def check_banned_words(content: str, code_free: str, report: AuditReport):
    """Check for AI-style banned words (0 tolerance)."""
    hits = []
    for pattern, label in BANNED_PATTERNS:
        matches = re.findall(pattern, code_free)
        if matches:
            hits.append((label, len(matches), matches[:3]))

    if hits:
        detail_lines = []
        for label, count, examples in hits:
            detail_lines.append(f"{label}: {count}x — e.g. \"{examples[0][:50]}\"")
        report.add("AI 味禁用词", "error",
                     f"{len(hits)} 种禁用词命中（0 容忍）",
                     "\n".join(detail_lines))
    else:
        report.add("AI 味禁用词", "pass", "无禁用词命中")


def check_word_count(content: str, report: AuditReport):
    """Check Chinese character count against sweet spot."""
    chinese = len(re.findall(r'[\u4e00-\u9fff]', content))
    total = len(content)
    h3_count = len(re.findall(r'^### ', content, re.M))
    h2_count = len(re.findall(r'^## ', content, re.M))

    report.add("字数统计", "pass",
                f"中文字符: {chinese} | 总字符: {total} | h2: {h2_count} | h3: {h3_count}")

    # Determine article type
    code_blocks = len(re.findall(r'```', content)) // 2
    is_code_heavy = code_blocks >= 8

    if is_code_heavy:
        if total < 6000:
            report.add("字数检查", "warn",
                        f"代码密集型文章总字符 {total} 偏少（建议 ≥ 6000）")
        elif chinese < 1500:
            report.add("字数检查", "warn",
                        f"代码密集型文章中文字符 {chinese} 偏少（建议 ≥ 1500）")
        else:
            report.add("字数检查", "pass",
                        f"代码密集型文章字数达标（总字符 {total}, 中文 {chinese}）")
    else:
        if chinese < 2500:
            report.add("字数检查", "warn",
                        f"中文字符 {chinese} 低于甜点区（目标 3000-4000）")
        elif chinese > 4500:
            report.add("字数检查", "warn",
                        f"中文字符 {chinese} 超出甜点区（目标 3000-4000）")
        else:
            report.add("字数检查", "pass",
                        f"中文字符 {chinese} 在甜点区（3000-4000）")


def check_links(content: str, report: AuditReport, check_http: bool = False):
    """Check for link validity."""
    links = re.findall(r'https?://[^\s\)]+', content)

    if not links:
        report.add("链接检查", "pass", "无外部链接")
        return

    report.add("链接统计", "pass", f"发现 {len(links)} 个链接")

    if not check_http:
        report.add("链接有效性", "pass",
                    f"跳过 HTTP 检查（用 --check-links 启用）")
        return

    broken = []
    checked = 0
    for url in links:
        # Clean URL (remove trailing punctuation)
        url = re.sub(r'[.,;:!?]+$', '', url)
        if not url.startswith("http"):
            continue
        try:
            req = urllib.request.Request(url, method="HEAD", headers={
                "User-Agent": "Mozilla/5.0",
            })
            with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
                if resp.status >= 400:
                    broken.append((url[:80], resp.status))
        except urllib.error.HTTPError as e:
            broken.append((url[:80], e.code))
        except Exception as e:
            broken.append((url[:80], str(e)[:40]))
        checked += 1

    if broken:
        detail = "\n".join(f"  {url} → {status}" for url, status in broken[:10])
        report.add("链接有效性", "error",
                     f"{len(broken)}/{checked} 个链接失效", detail)
    else:
        report.add("链接有效性", "pass",
                     f"全部 {checked} 个链接可访问")


def check_code_blocks(content: str, report: AuditReport):
    """Check code block completeness and syntax."""
    blocks = re.findall(r'```(\w*)\n(.*?)```', content, re.S)

    if not blocks:
        report.add("代码块", "pass", "无代码块")
        return

    issues = []
    stats = {"total": len(blocks), "with_lang": 0, "with_import": 0, "empty": 0}

    for lang, code in blocks:
        code = code.strip()
        if lang:
            stats["with_lang"] += 1
        if not code:
            stats["empty"] += 1
            continue
        if re.search(r'^import |^from .+ import', code, re.M):
            stats["with_import"] += 1

    if stats["empty"] > 0:
        issues.append(f"{stats['empty']} 个空代码块")

    no_lang = stats["total"] - stats["with_lang"]
    if no_lang > 0:
        issues.append(f"{no_lang} 个代码块缺少语言标注")

    if issues:
        report.add("代码块", "warn",
                     f"{stats['total']} 个代码块: " + "; ".join(issues),
                     f"有语言标注: {stats['with_lang']}/{stats['total']}\n"
                     f"含 import: {stats['with_import']}/{stats['total']}")
    else:
        report.add("代码块", "pass",
                     f"{stats['total']} 个代码块，全部有语言标注")


def check_structure(content: str, report: AuditReport):
    """Check document structure (h2/h3 hierarchy, paragraph lengths)."""
    lines = content.split("\n")

    # Check h2/h3 hierarchy
    h2_count = len(re.findall(r'^## ', content, re.M))
    h3_count = len(re.findall(r'^### ', content, re.M))

    if h2_count == 0 and h3_count == 0:
        report.add("标题结构", "warn", "无 h2/h3 标题（公众号需要章节标题）")
    elif h2_count == 0 and h3_count > 0:
        report.add("标题结构", "warn",
                     f"只有 h3（{h3_count} 个）没有 h2 — 公众号通过 h2 识别章节")
    else:
        report.add("标题结构", "pass",
                     f"h2: {h2_count} | h3: {h3_count}")

    # Check paragraph lengths
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    para_lengths = [len(p) for p in paragraphs if not p.startswith("#") and not p.startswith("```")]

    if para_lengths:
        avg_len = sum(para_lengths) / len(para_lengths)
        max_len = max(para_lengths)
        long_paras = [i for i, l in enumerate(para_lengths) if l > 500]

        if long_paras:
            report.add("段落长度", "warn",
                        f"{len(long_paras)} 个段落超过 500 字符（可能导致「没段落」感）",
                        f"平均段长: {avg_len:.0f} | 最长: {max_len} | 段落数: {len(para_lengths)}")
        else:
            report.add("段落长度", "pass",
                        f"段落长度合理（平均 {avg_len:.0f} 字符, 最长 {max_len}）")


def check_images(content: str, report: AuditReport):
    """Check image references."""
    # Find all image references
    img_refs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)
    img_placeholders = re.findall(r'!\[([^\]]*)\]\(\)', content)
    img_no_url = re.findall(r'!\[[^\]]*\]\([^h][^)]*\)', content)

    if img_placeholders:
        report.add("图片引用", "error",
                     f"{len(img_placeholders)} 个图片占位符无 URL",
                     "\n".join(f"  ![alt]()" for alt, _ in img_placeholders[:5]))
    elif img_refs:
        oss_count = sum(1 for _, url in img_refs if "oss-cn-beijing" in url or "oss" in url)
        report.add("图片引用", "pass",
                     f"{len(img_refs)} 张图片引用（{oss_count} 个 OSS 链接）")
    else:
        report.add("图片引用", "warn", "无图片引用（用户要求尽量嵌入原图）")


def check_horizontal_rules(content: str, report: AuditReport):
    """Check for --- horizontal rules (breaks Feishu formatting)."""
    # Only check --- that's on its own line (not YAML frontmatter)
    lines = content.split("\n")
    in_frontmatter = False
    hr_lines = []
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if i == 0 or (i == 1 and lines[0].strip() == ""):
                in_frontmatter = True
                continue
            if in_frontmatter:
                in_frontmatter = False
                continue
            hr_lines.append(i + 1)

    if hr_lines:
        report.add("分隔符", "error",
                     f"{len(hr_lines)} 个 --- 分隔符（飞书渲染为水平线，破坏格式）",
                     f"行号: {', '.join(str(l) for l in hr_lines[:10])}")
    else:
        report.add("分隔符", "pass", "无 --- 分隔符")


def check_frontmatter(content: str, report: AuditReport):
    """Check frontmatter if present."""
    m = re.match(r'^---\n(.*?)\n---\n', content, re.S)
    if not m:
        report.add("Frontmatter", "pass", "无 frontmatter（非必需）")
        return

    fm_text = m.group(1)
    required_fields = ["title"]
    recommended_fields = ["series", "author", "status", "created"]

    found = set()
    for line in fm_text.split("\n"):
        if ":" in line:
            key = line.split(":")[0].strip()
            found.add(key)

    missing_req = [f for f in required_fields if f not in found]
    missing_rec = [f for f in recommended_fields if f not in found]

    if missing_req:
        report.add("Frontmatter", "error",
                     f"缺少必填字段: {', '.join(missing_req)}")
    elif missing_rec:
        report.add("Frontmatter", "warn",
                     f"缺少推荐字段: {', '.join(missing_rec)}")
    else:
        report.add("Frontmatter", "pass", "frontmatter 完整")


def check_disabled_content(content: str, code_free: str, report: AuditReport):
    """Check for disabled/risky content patterns."""
    issues = []

    # Unverified code patterns
    if re.search(r'TODO|FIXME|HACK|XXX', code_free, re.I):
        issues.append("包含 TODO/FIXME/HACK 标记")

    # Security risks
    if re.search(r'password\s*=\s*["\'][^"\']+["\']', code_free, re.I):
        issues.append("可能包含硬编码密码")
    if re.search(r'api_key\s*=\s*["\'][^"\']+["\']', code_free, re.I):
        issues.append("可能包含硬编码 API Key")

    # Factual claims without source
    if re.search(r'据[统调]查|数据显[示]|研[究报]告', code_free):
        if not re.search(r'\[.*?\]\(https?://', code_free):
            issues.append("引用数据/研究但未附来源链接")

    if issues:
        report.add("内容风险", "warn", f"{len(issues)} 项潜在风险",
                     "\n".join(f"  - {i}" for i in issues))
    else:
        report.add("内容风险", "pass", "无内容风险")


# ── Main ────────────────────────────────────────────────────────────────────

def audit(filepath: str, do_check_links: bool = False) -> AuditReport:
    """Run full audit on a markdown file."""
    report = AuditReport(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Strip code blocks for banned word scanning
    code_free = re.sub(r'```[\s\S]*?```', '', content)

    # Run all checks
    check_banned_words(content, code_free, report)
    check_word_count(content, report)
    check_links(content, report, check_http=do_check_links)
    check_code_blocks(content, report)
    check_structure(content, report)
    check_images(content, report)
    check_horizontal_rules(content, report)
    check_frontmatter(content, report)
    check_disabled_content(content, code_free, report)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Automated pre-publish audit for tech articles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("filepath", help="Path to markdown article")
    parser.add_argument("--check-links", action="store_true",
                        help="Run HTTP HEAD checks on all links (slower)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON report to stdout")
    parser.add_argument("--output", "-o", help="Save JSON report to file")

    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"❌ File not found: {args.filepath}")
        sys.exit(1)

    report = audit(args.filepath, do_check_links=args.check_links)

    if args.json or args.output:
        result = {
            "summary": report.summary(),
            "checks": report.checks,
            "timestamp": datetime.now().isoformat(),
        }
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Report saved to: {args.output}")
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        report.print_report()

    # Exit code
    if report.errors > 0:
        sys.exit(1)
    elif report.warnings > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
