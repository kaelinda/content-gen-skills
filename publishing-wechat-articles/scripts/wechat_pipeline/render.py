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
    list_open = False
    code_open = False
    code_lines: list[str] = []
    code_language = ""

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            output.append("</ul>")
            list_open = False

    for line in lines:
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
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f'<h{level}><span class="content">{_inline(heading.group(2))}</span></h{level}>')
            continue
        item = re.match(r"^[-*+]\s+(.+)$", line)
        if item:
            flush_paragraph()
            if not list_open:
                output.append("<ul>")
                list_open = True
            output.append(f"<li>{_inline(item.group(1))}</li>")
            continue
        quote = re.match(r"^>\s?(.*)$", line)
        if quote:
            flush_paragraph()
            close_list()
            output.append(f"<blockquote>{_inline(quote.group(1))}</blockquote>")
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
    return (
        "<!doctype html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{html.escape(title)}</title>"
        f"<style>{safe_theme}</style></head><body><section id=\"nice\">{body}</section></body></html>\n"
    )
