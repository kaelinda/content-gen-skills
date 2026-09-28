from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from urllib.parse import urlsplit

from .models import Finding
from .security import sanitize_resource_url


BANNED_PATTERNS = (
    (r"不是[^\n，。]+[，,]而是", "不是X，而是Y"),
    (r"与其[说]?(?:[^，。]+)[，,]不[如说]", "与其X，不如Y"),
    (r"首先.*其次.*最后", "首先...其次...最后"),
    (r"值得注意的是", "值得注意的是"),
    (r"总的来说|总而言之|综上所述", "空泛总结"),
    (r"在当今|不可否认|众所周知|显而易见", "陈词滥调"),
    (r"不难发现|不言而喻|毋庸置疑|毫无疑问", "无依据断言"),
    (r"正如我们所知|需要指出的是", "AI 过渡语"),
    (r"一定程度上|或多或少", "模糊表达"),
    (r"(?<!\w)(?:大概|似乎|可能|应该|非常|十分|极其|真正)(?!\w)", "弱化或空洞修饰"),
    (r"(?<!\w)相当(?=的|大|重要|高|多|复杂|困难|简单)", "空洞修饰"),
)


@dataclass(frozen=True)
class QualityReport:
    findings: tuple[Finding, ...]
    chinese_characters: int

    @property
    def blocking(self) -> tuple[Finding, ...]:
        return tuple(item for item in self.findings if item.severity == "error")

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(item for item in self.findings if item.severity == "warning")

    @property
    def passed(self) -> bool:
        return not self.blocking

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "chinese_characters": self.chinese_characters,
            "findings": [asdict(item) for item in self.findings],
        }


def _without_code(markdown: str) -> str:
    value = re.sub(r"```[\s\S]*?```", "", markdown)
    return re.sub(r"`[^`\n]+`", "", value)


def _without_frontmatter(markdown: str) -> str:
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return markdown
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :])
    return markdown


def _frontmatter(markdown: str) -> tuple[dict[str, str], str | None]:
    """Read the small YAML subset used by article frontmatter.

    The project intentionally does not depend on a YAML parser for this
    metadata. Values are kept as strings because the quality gate only needs
    to verify presence and avoid silently interpreting article content.
    """
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "frontmatter is missing"
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            values: dict[str, str] = {}
            for line in lines[1:index]:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if ":" not in line:
                    return {}, "frontmatter contains a malformed line"
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                if key:
                    values[key] = value
            return values, None
    return {}, "frontmatter closing delimiter is missing"


def _resource_findings(markdown: str) -> list[Finding]:
    findings: list[Finding] = []
    # Images and links are audited before rendering, because the renderer
    # intentionally drops unsafe URLs instead of producing unsafe HTML.
    pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|\[[^\]]+\]\(([^)]+)\)")
    for match in pattern.finditer(_without_code(markdown)):
        raw = (match.group(1) or match.group(2) or "").strip().strip('<>')
        if not raw:
            findings.append(Finding("resource-url", "error", "链接或图片 URL 不能为空"))
            continue
        if not sanitize_resource_url(raw):
            findings.append(Finding("resource-url", "error", "链接或图片 URL 不安全或不受支持", {"url": raw}))
            continue
        parsed = urlsplit(raw)
        if parsed.scheme == "https" and not parsed.hostname:
            findings.append(Finding("resource-url", "error", "HTTPS URL 缺少主机名", {"url": raw}))
    return findings


def _markdown_structure_findings(markdown: str) -> list[Finding]:
    findings: list[Finding] = []
    fence_count = len(re.findall(r"(?m)^\s*```", markdown))
    if fence_count % 2:
        findings.append(Finding("code-fence", "error", "代码块围栏未闭合"))

    markers = re.findall(r"(?i)(?:TODO|TBD|FIXME|待补充|待确认)", _without_code(markdown))
    if markers:
        findings.append(Finding("residual-marker", "error", "正文残留未完成标记", {"count": len(markers)}))

    secret_patterns = (
        r"(?i)\b(?:authorization\s*:\s*bearer|cookie\s*:|x-api-key\s*:)",
        r"(?i)\b(?:api[_-]?key|access[_-]?key|secret|token)\s*[=:]\s*[^\s`]{12,}",
        r"(?i)\b(?:sk|rk)-[A-Za-z0-9_-]{16,}\b",
    )
    for pattern in secret_patterns:
        if re.search(pattern, markdown):
            findings.append(Finding("sensitive-value", "error", "正文疑似包含凭证、Cookie 或 Authorization"))
            break

    local_path = re.compile(r"(?:file://|/Users/|/home/|[A-Za-z]:\\|(?:^|[\s(`])workspace/|runtime\.local\.toml)")
    if local_path.search(markdown):
        findings.append(Finding("local-path", "error", "正文不能包含本机路径或私有运行时文件名"))
    return findings


def _table_findings(markdown: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = _without_frontmatter(markdown).splitlines()
    for index, line in enumerate(lines[:-1]):
        if "|" not in line or "|" not in lines[index + 1]:
            continue
        if not re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", lines[index + 1]):
            continue
        separator = lines[index + 1].strip().strip("|")
        cells = [cell.strip() for cell in separator.split("|")]
        if len(cells) < 2 or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            if re.search(r"\S+\s*\|", line):
                findings.append(Finding("markdown-table", "error", "Markdown 表格分隔行格式不完整"))
    return findings


def _account_findings(markdown: str, account: str | None) -> list[Finding]:
    if account not in {"tech", "parenting"}:
        return []
    body = _without_code(_without_frontmatter(markdown))
    findings: list[Finding] = []
    if account == "tech":
        if not re.search(r"(?i)(代码|实现|接口|版本|实测|工程|边界|取舍|风险)", body):
            findings.append(Finding("tech-editorial-signal", "warning", "技术文章缺少工程判断、实现或边界信号"))
    else:
        if not re.search(r"(?:岁|月龄|年龄|学龄|青春期)", body):
            findings.append(Finding("parenting-age", "warning", "育儿文章未明确适用年龄或阶段"))
        if not re.search(r"(?:可以这样说|你可以说|行动清单|试试看|建议)", body):
            findings.append(Finding("parenting-action", "warning", "育儿文章缺少具体话术或行动建议"))
    return findings


def check_article(
    markdown: str,
    rendered_html: str | None = None,
    *,
    author_voice: bool = False,
    account: str | None = None,
) -> QualityReport:
    findings: list[Finding] = []
    frontmatter, frontmatter_error = _frontmatter(markdown)
    if frontmatter_error:
        findings.append(Finding("frontmatter", "warning", frontmatter_error))
    else:
        for field in ("title", "summary"):
            if not frontmatter.get(field):
                findings.append(Finding("frontmatter", "warning", f"frontmatter 缺少 {field}"))

    findings.extend(_markdown_structure_findings(markdown))
    findings.extend(_resource_findings(markdown))
    findings.extend(_table_findings(markdown))
    findings.extend(_account_findings(markdown, account))
    code_free = _without_code(markdown)
    for pattern, label in BANNED_PATTERNS:
        matches = list(re.finditer(pattern, code_free, flags=re.MULTILINE))
        if matches:
            code = "generic-language" if author_voice else "banned-word"
            severity = "warning" if author_voice else "error"
            message = f"通用表达，需结合作者判断复核: {label}" if author_voice else f"禁用表达: {label}"
            findings.append(Finding(code, severity, message, {"count": len(matches)}))

    body = _without_code(_without_frontmatter(markdown))
    rules = re.findall(r"(?m)^\s*(?:---+|\*\*\*+)\s*$", body)
    if rules:
        findings.append(Finding("body-horizontal-rule", "error", "正文中不能使用水平分隔线", {"count": len(rules)}))

    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", markdown))
    if chinese_count < 2500 or chinese_count > 4500:
        findings.append(Finding("article-length", "warning", "正文中文字符数不在建议的 2500-4500 范围", {"count": chinese_count}))

    if not re.search(r"(?m)^##\s+\S", body):
        findings.append(Finding("missing-h2", "error", "文章至少需要一个二级标题"))
    if rendered_html is not None and not re.search(r"<h2(?:\s|>)", rendered_html, re.IGNORECASE):
        findings.append(Finding("rendered-missing-h2", "error", "渲染结果缺少 h2"))
    return QualityReport(tuple(findings), chinese_count)
