from __future__ import annotations

import html
import re

from .security import sanitize_resource_url


INLINE_PATTERN = re.compile(
    r"!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|(?<!\*)\*([^*]+)\*(?!\*)"
)


def _strip_frontmatter(markdown: str) -> str:
    lines = markdown.splitlines()
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                return "\n".join(lines[index + 1 :])
    return markdown


def _inline(value: str) -> str:
    output: list[str] = []
    position = 0
    for match in INLINE_PATTERN.finditer(value):
        output.append(html.escape(value[position : match.start()]))
        image_alt, image_url, link_text, link_url, code, bold, italic = match.groups()
        if image_alt is not None:
            safe_url = sanitize_resource_url(image_url)
            if safe_url:
                output.append(
                    f'<figure><img src="{html.escape(safe_url, quote=True)}" alt="{html.escape(image_alt, quote=True)}"><figcaption>{html.escape(image_alt)}</figcaption></figure>'
                )
            else:
                output.append(html.escape(image_alt))
        elif link_text is not None:
            safe_url = sanitize_resource_url(link_url)
            if safe_url:
                output.append(
                    f'<a href="{html.escape(safe_url, quote=True)}" rel="noopener noreferrer">{html.escape(link_text)}</a>'
                )
            else:
                output.append(html.escape(link_text))
        elif code is not None:
            output.append(f"<code>{html.escape(code)}</code>")
        elif bold is not None:
            output.append(f"<strong>{html.escape(bold)}</strong>")
        else:
            output.append(f"<em>{html.escape(italic or '')}</em>")
        position = match.end()
    output.append(html.escape(value[position:]))
    return "".join(output)


def markdown_body(markdown: str) -> str:
    lines = _strip_frontmatter(markdown).splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    list_kind = ""
    code_open = False
    code_lines: list[str] = []
    code_language = ""

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            output.append(f"</{list_kind}>")
            list_kind = ""

    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if line.startswith("```"):
            flush_paragraph()
            close_list()
            if code_open:
                language_class = f' class="language-{html.escape(code_language, quote=True)}"' if code_language else ""
                output.append(f"<pre class=\"custom\"><code{language_class}>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                code_open = False
            else:
                code_language = line[3:].strip()
                code_open = True
            continue
        if code_open:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            close_list()
            continue
        if index < len(lines) and "|" in line and re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", lines[index]):
            flush_paragraph()
            close_list()
            headings = [cell.strip() for cell in line.strip().strip("|").split("|")]
            output.append("<div class=\"table-scroll\"><table><thead><tr>" + "".join(
                f"<th>{_inline(cell)}</th>" for cell in headings
            ) + "</tr></thead><tbody>")
            index += 1
            while index < len(lines) and lines[index].strip() and "|" in lines[index]:
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                output.append("<tr>" + "".join(f"<td>{_inline(cell)}</td>" for cell in cells) + "</tr>")
                index += 1
            output.append("</tbody></table></div>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f'<h{level}><span class="content">{_inline(heading.group(2))}</span></h{level}>')
            continue
        item = re.match(r"^([-*+]|\d+\.)\s+(.+)$", line)
        if item:
            flush_paragraph()
            kind = "ol" if item.group(1).endswith(".") else "ul"
            if list_kind != kind:
                close_list()
                output.append(f"<{kind}>")
                list_kind = kind
            output.append(f"<li>{_inline(item.group(2))}</li>")
            continue
        quote = re.match(r"^>\s?(.*)$", line)
        if quote:
            flush_paragraph()
            close_list()
            output.append(f"<blockquote>{_inline(quote.group(1))}</blockquote>")
            continue
        if re.fullmatch(r"!\[[^\]]*\]\([^)]+\)", line.strip()):
            flush_paragraph()
            close_list()
            output.append(_inline(line.strip()))
            continue
        paragraph.append(line.strip())

    if code_open:
        output.append(f"<pre class=\"custom\"><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    flush_paragraph()
    close_list()
    return "\n".join(output)


def render_markdown(markdown: str, theme_css: str, *, title: str = "WeChat Article") -> str:
    body = markdown_body(markdown)
    safe_theme = theme_css.replace("</style", "<\\/style")
    mobile_css = (
        "#nice .table-scroll{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;}"
        "#nice .table-scroll table{min-width:540px;border-collapse:collapse;}"
        "#nice pre{max-width:100%;overflow-x:auto;white-space:pre-wrap;overflow-wrap:anywhere;}"
        "#nice img{max-width:100%;height:auto;}"
    )
    return (
        "<!doctype html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{html.escape(title)}</title>"
        f"<style>{safe_theme}{mobile_css}</style></head><body><section id=\"nice\">{body}</section></body></html>\n"
    )
