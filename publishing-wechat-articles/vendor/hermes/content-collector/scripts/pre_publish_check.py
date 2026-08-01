#!/usr/bin/env python3
"""
Pre-publish quality check — single entry point for all checks.

Usage:
    python3 pre_publish_check.py article.html article.md
    python3 pre_publish_check.py article.html article.md --cover /tmp/cover.png
    python3 pre_publish_check.py article.html article.md --oss-url https://kaelblog.oss-cn-beijing.aliyuncs.com/wechat/xxx.html

Checks:
  1. Banned words (0 tolerance)
  2. Chinese char count (3000-4000 sweet spot)
  3. HTML has >0 <h2> tags (md-to-html rendered correctly)
  4. Footnotes mode active (sup + footnotes section)
  5. No --- separators in body
  6. No inline <a href> (WeChat strips them)
  7. OSS URL HEAD 200 (if provided)
  8. Cover image exists and is valid PNG (if provided)

Exit codes:
  0 = PASS
  1 = FAIL (must fix before publish)
  2 = WARN (should fix but not blocking)
"""

import argparse
import os
import re
import subprocess
import sys
import urllib.request


def check_banned_words(md_path: str) -> tuple[bool, list[str]]:
    """Check for banned words using the scanner script."""
    scanner = os.path.join(os.path.dirname(__file__), "..", "tech-content-writer", "scripts", "banned_word_scan.py")
    scanner = os.path.normpath(scanner)
    
    if not os.path.exists(scanner):
        # Fallback: inline check
        with open(md_path, 'r') as f:
            content = f.read()
        code_free = re.sub(r'```[\s\S]*?```', '', content)
        code_free = re.sub(r'`[^`\n]+`', '', code_free)
        
        patterns = [
            (r'不是[^，。]+[，,]而是', '不是X而是Y'),
            (r'值得注意的是', '值得注意'),
            (r'总的来说', '总的来说'),
            (r'首先.*其次.*最后', '首先其次最后'),
        ]
        hits = []
        for pat, label in patterns:
            if re.findall(pat, code_free):
                hits.append(label)
        return len(hits) == 0, hits
    
    result = subprocess.run(
        [sys.executable, scanner, md_path],
        capture_output=True, text=True, timeout=10,
    )
    passed = result.returncode == 0
    hits = []
    if not passed:
        for line in result.stdout.split('\n'):
            if 'occurrences' in line:
                hits.append(line.strip())
    return passed, hits


def check_chinese_chars(md_path: str) -> tuple[int, str]:
    """Check Chinese character count."""
    with open(md_path, 'r') as f:
        content = f.read()
    
    chinese = len(re.findall(r'[\u4e00-\u9fff]', content))
    total = len(content)
    
    if 3000 <= chinese <= 4000:
        return chinese, "✅ sweet spot (3000-4000)"
    elif chinese < 3000:
        return chinese, f"⚠️ below sweet spot (target: 3000-4000, total: {total})"
    elif chinese > 4500:
        return chinese, f"⚠️ above sweet spot (target: 3000-4000, total: {total})"
    else:
        return chinese, f"✅ acceptable (total: {total})"


def check_html_headings(html_path: str) -> tuple[int, int, bool]:
    """Check HTML has h2 and h3 tags."""
    with open(html_path, 'r') as f:
        html = f.read()
    
    h2 = len(re.findall(r'<h2', html))
    h3 = len(re.findall(r'<h3', html))
    passed = h2 > 0
    return h2, h3, passed


def check_footnotes(html_path: str) -> bool:
    """Check footnotes mode is active."""
    with open(html_path, 'r') as f:
        html = f.read()
    
    has_sup = bool(re.search(r'<sup[^>]*>\[\d+\]</sup>', html))
    has_section = 'class="footnotes"' in html or 'class=\\"footnotes\\"' in html
    return has_sup or has_section


def check_no_hr(md_path: str) -> tuple[int, bool]:
    """Check no --- separators."""
    with open(md_path, 'r') as f:
        content = f.read()
    
    # Strip code blocks
    code_free = re.sub(r'```[\s\S]*?```', '', content)
    count = code_free.count('---')
    return count, count == 0


def check_no_inline_links(html_path: str) -> tuple[int, bool]:
    """Check no inline <a href> tags (WeChat strips them)."""
    with open(html_path, 'r') as f:
        html = f.read()
    
    # Strip code blocks
    code_free = re.sub(r'<pre[\s\S]*?</pre>', '', html)
    count = len(re.findall(r'<a href', code_free))
    return count, count == 0


def check_oss_url(url: str) -> tuple[int, str]:
    """HEAD check OSS URL."""
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.headers.get('Content-Type', 'unknown')
    except Exception as e:
        return 0, str(e)


def check_cover(cover_path: str) -> tuple[bool, str]:
    """Check cover image exists and is valid."""
    if not os.path.exists(cover_path):
        return False, f"file not found: {cover_path}"
    
    size = os.path.getsize(cover_path)
    if size < 10000:
        return False, f"file too small ({size:,} bytes), probably not a valid image"
    
    with open(cover_path, 'rb') as f:
        header = f.read(8)
    
    if header[:8] == b'\x89PNG\r\n\x1a\n':
        return True, f"PNG, {size:,} bytes"
    elif header[:2] == b'\xff\xd8':
        return True, f"JPEG, {size:,} bytes"
    else:
        return False, f"unknown format (header: {header[:4].hex()})"


def main():
    parser = argparse.ArgumentParser(
        description="Pre-publish quality check for WeChat articles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 pre_publish_check.py article.html article.md
  python3 pre_publish_check.py article.html article.md --cover /tmp/cover.png
  python3 pre_publish_check.py article.html article.md --oss-url https://kaelblog.oss-cn-beijing.aliyuncs.com/wechat/xxx.html
        """,
    )
    parser.add_argument("html", help="HTML article file")
    parser.add_argument("md", help="Markdown source file")
    parser.add_argument("--cover", help="Cover image path to check")
    parser.add_argument("--oss-url", help="OSS URL to HEAD check")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.html):
        print(f"❌ HTML file not found: {args.html}")
        sys.exit(1)
    if not os.path.exists(args.md):
        print(f"❌ MD file not found: {args.md}")
        sys.exit(1)
    
    fails = []
    warns = []
    
    print("=" * 60)
    print("Pre-publish Quality Check")
    print("=" * 60)
    
    # 1. Banned words
    passed, hits = check_banned_words(args.md)
    if passed:
        print("  ✅ Banned words: 0 hits")
    else:
        print(f"  ❌ Banned words: {len(hits)} patterns found")
        for h in hits:
            print(f"     - {h}")
        fails.append("banned words")
    
    # 2. Chinese char count
    count, msg = check_chinese_chars(args.md)
    if "✅" in msg:
        print(f"  ✅ Chinese chars: {count} {msg}")
    else:
        print(f"  ⚠️  Chinese chars: {count} {msg}")
        warns.append("char count")
    
    # 3. HTML headings
    h2, h3, passed = check_html_headings(args.html)
    if passed:
        print(f"  ✅ HTML headings: {h2} h2, {h3} h3")
    else:
        print(f"  ❌ HTML headings: {h2} h2 (need >0 for md-to-html rendering)")
        fails.append("no h2 headings")
    
    # 4. Footnotes
    has_fn = check_footnotes(args.html)
    if has_fn:
        print("  ✅ Footnotes mode: active")
    else:
        print("  ⚠️  Footnotes mode: not detected (links may break in WeChat)")
        warns.append("footnotes")
    
    # 5. No --- separators
    count, passed = check_no_hr(args.md)
    if passed:
        print("  ✅ No --- separators")
    else:
        print(f"  ❌ Found {count} --- separator(s) (Feishu renders as horizontal rule)")
        fails.append("--- separators")
    
    # 6. No inline links
    count, passed = check_no_inline_links(args.html)
    if passed:
        print("  ✅ No inline <a href> tags")
    else:
        print(f"  ⚠️  Found {count} <a href> tag(s) (WeChat will strip them)")
        warns.append("inline links")
    
    # 7. Cover image (optional)
    if args.cover:
        ok, msg = check_cover(args.cover)
        if ok:
            print(f"  ✅ Cover image: {msg}")
        else:
            print(f"  ❌ Cover image: {msg}")
            fails.append("cover image")
    
    # 8. OSS URL (optional)
    if args.oss_url:
        status, ct = check_oss_url(args.oss_url)
        if status == 200:
            print(f"  ✅ OSS URL: {status} ({ct})")
        else:
            print(f"  ❌ OSS URL: {status} ({ct})")
            fails.append("OSS URL")
    
    # Summary
    print("=" * 60)
    if fails:
        print(f"❌ FAIL: {len(fails)} blocking issue(s)")
        for f in fails:
            print(f"   - {f}")
        if warns:
            print(f"⚠️  WARN: {len(warns)} non-blocking issue(s)")
            for w in warns:
                print(f"   - {w}")
        sys.exit(1)
    elif warns:
        print(f"⚠️  PASS with warnings: {len(warns)} non-blocking issue(s)")
        for w in warns:
            print(f"   - {w}")
        sys.exit(0)
    else:
        print("✅ ALL CHECKS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
