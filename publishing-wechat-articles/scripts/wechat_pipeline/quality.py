from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from .models import Finding


BANNED_PATTERNS = (
    (r"不是[^，。]+[，,]而是", "不是X，而是Y"),
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


def check_article(
    markdown: str,
    rendered_html: str | None = None,
    *,
    author_voice: bool = False,
) -> QualityReport:
    findings: list[Finding] = []
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
