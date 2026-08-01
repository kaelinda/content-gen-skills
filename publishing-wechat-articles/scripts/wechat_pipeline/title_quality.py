from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from .models import Finding


SENSATIONAL_PATTERNS = (
    (r"震惊|惊呆", "震惊体"),
    (r"炸裂|封神|逆天", "极端情绪词"),
    (r"史上最|全网最", "无依据最高级"),
    (r"必看|必转|速看", "强迫式诱导"),
    (r"错过.*后悔|不看.*亏", "损失恐吓"),
    (r"你绝对想不到|万万没想到", "悬念诱导"),
    (r"\b99%\b|百分之九十九", "虚假精确比例"),
    (r"彻底(?:颠覆|改变|解决|失业)", "绝对化承诺"),
    (r"秒杀|吊打|碾压", "攻击式比较"),
    (r"财富密码|真相了", "营销诱导"),
)

VAGUE_PATTERNS = (
    r"关于.+的一些思考",
    r"聊聊.+",
    r"谈谈.+",
    r"随便说说",
    r"一些想法",
    r"我的思考",
    r"有感$",
)

VALUE_SIGNALS = (
    "如何",
    "为什么",
    "怎么",
    "指南",
    "实战",
    "方法",
    "步骤",
    "清单",
    "避坑",
    "复盘",
    "原理",
    "工程化",
    "对比",
    "提升",
    "解决",
    "常见问题",
    "误区",
    "选择",
    "关键",
    "本质",
)

STOP_TERMS = {
    "关于",
    "一些",
    "思考",
    "如何",
    "为什么",
    "怎么",
    "方法",
    "指南",
    "实战",
    "工程化",
}
STOP_CHARS = set("的了是在和与把让从到这那一个篇")


@dataclass(frozen=True)
class TitleRules:
    hard_min: int = 6
    hard_max: int = 64
    recommended_min: int = 12
    recommended_max: int = 32
    minimum_score: int = 80
    minimum_body_overlap: float = 0.2


@dataclass(frozen=True)
class TitleQualityReport:
    title: str
    score: int
    findings: tuple[Finding, ...]
    metrics: dict[str, object]

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
            "title": self.title,
            "score": self.score,
            "passed": self.passed,
            "metrics": self.metrics,
            "findings": [asdict(item) for item in self.findings],
        }


def _title_terms(title: str) -> tuple[str, ...]:
    value = title.lower()
    terms: set[str] = {
        token
        for token in re.findall(r"[a-z][a-z0-9+#.-]+", value)
        if token not in {"the", "and", "with", "from"}
    }
    for segment in re.findall(r"[\u4e00-\u9fff]+", value):
        for size in (2, 3):
            for index in range(len(segment) - size + 1):
                term = segment[index : index + size]
                if term in STOP_TERMS or any(char in STOP_CHARS for char in term):
                    continue
                terms.add(term)
    for signal in VALUE_SIGNALS:
        terms.discard(signal.lower())
    return tuple(sorted(terms))


def check_title(title: str, markdown: str, rules: TitleRules = TitleRules()) -> TitleQualityReport:
    clean_title = " ".join(title.split())
    visible_length = len(re.sub(r"\s+", "", clean_title))
    findings: list[Finding] = []
    score = 100

    if not clean_title or visible_length < rules.hard_min or visible_length > rules.hard_max:
        findings.append(
            Finding(
                "title-hard-length",
                "error",
                f"标题长度必须在 {rules.hard_min}-{rules.hard_max} 个可见字符之间",
                {"length": visible_length},
            )
        )
        score -= 50
    elif visible_length < rules.recommended_min or visible_length > rules.recommended_max:
        findings.append(
            Finding(
                "title-length",
                "warning",
                f"标题建议控制在 {rules.recommended_min}-{rules.recommended_max} 个可见字符",
                {"length": visible_length},
            )
        )
        score -= 10

    sensational_hits = [label for pattern, label in SENSATIONAL_PATTERNS if re.search(pattern, clean_title, re.IGNORECASE)]
    if sensational_hits:
        findings.append(
            Finding(
                "title-sensational",
                "error",
                "标题包含夸张、诱导或无依据承诺",
                {"hits": sensational_hits},
            )
        )
        score -= min(60, 30 * len(sensational_hits))

    punctuation_count = len(re.findall(r"[!！?？]", clean_title))
    if punctuation_count > 1 or re.search(r"[!！?？]{2,}", clean_title):
        findings.append(
            Finding(
                "title-punctuation",
                "error",
                "标题的感叹号或问号过多",
                {"count": punctuation_count},
            )
        )
        score -= 20

    vague_hits = [pattern for pattern in VAGUE_PATTERNS if re.search(pattern, clean_title, re.IGNORECASE)]
    if vague_hits:
        findings.append(Finding("title-vague", "warning", "标题过于宽泛，未呈现具体重点"))
        score -= 20

    value_signals = [signal for signal in VALUE_SIGNALS if signal.lower() in clean_title.lower()]
    if re.search(r"\d", clean_title):
        value_signals.append("数字")
    if not value_signals:
        findings.append(Finding("title-value-signal", "warning", "标题没有呈现问题、收益、方法或具体范围"))
        score -= 15

    terms = _title_terms(clean_title)
    body = markdown.lower()
    matched_terms = [term for term in terms if term in body]
    body_overlap = len(matched_terms) / len(terms) if terms else 0.0
    if terms and body_overlap < rules.minimum_body_overlap:
        findings.append(
            Finding(
                "title-body-mismatch",
                "warning",
                "标题重点与正文内容缺少可验证的关键词呼应",
                {"matched_terms": matched_terms, "term_count": len(terms)},
            )
        )
        score -= 25

    score = max(0, min(100, score))
    if score < rules.minimum_score:
        findings.append(
            Finding(
                "title-low-score",
                "error",
                f"标题综合评分低于发布门槛 {rules.minimum_score}",
                {"score": score},
            )
        )

    metrics = {
        "visible_length": visible_length,
        "body_overlap": round(body_overlap, 3),
        "matched_terms": matched_terms,
        "value_signals": value_signals,
        "sensational_hits": sensational_hits,
        "minimum_score": rules.minimum_score,
    }
    return TitleQualityReport(clean_title, score, tuple(findings), metrics)
