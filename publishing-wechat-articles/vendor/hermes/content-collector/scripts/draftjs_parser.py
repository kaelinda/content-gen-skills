#!/usr/bin/env python3
"""Convert fxtwitter X Article Draft.js blocks + entityMap to Markdown.

Usage:
    import json
    from draftjs_parser import article_to_markdown

    with open('/tmp/fxtwitter.json') as f:
        data = json.load(f)
    article = data['tweet']['article']
    markdown = article_to_markdown(article)

Entity map shape (CRITICAL):
    entityMap is a list of {"key": str, "value": {data, type}} objects,
    NOT a flat list of {type, data} entities. The entity's type and data
    are nested under .value.

Supported entity types:
    - MARKDOWN: data.markdown already includes ``` fences, emit as-is
    - MEDIA: look up URL from article.media_entities by media_id
    - DIVIDER: emit \\n---\\n
    - LINK: inline [text](url)
    - TWEET: emit [embedded tweet]
    - TWEMOJI: skip (emoji URL, not useful in markdown)

Inline styles:
    - Bold -> **text**
    - (Italic/Code not commonly seen in X Articles)

Pitfalls:
    - entityMap[i]["value"]["type"], NOT entityMap[i]["type"]
    - Pre-fenced MARKDOWN content: do NOT wrap in additional ``` fences
    - block.entityRanges[].key is usually string, sometimes int
    - Atomic blocks with text=" " are entity placeholders, skip text
"""


def article_to_markdown(article):
    """Convert fxtwitter article.content.blocks + entityMap to Markdown."""
    blocks = article["content"]["blocks"]
    em_list = article["content"].get("entityMap", [])

    # Build lookup. em_list is [{key: str, value: {data, type}}]
    em = {}
    for idx, item in enumerate(em_list):
        if isinstance(item, dict) and "key" in item and "value" in item:
            em[str(item["key"])] = item["value"]
            em[str(idx)] = item["value"]

    md = []
    for b in blocks:
        btype = b.get("type", "unstyled")
        text = b.get("text", "")

        if btype == "atomic":
            for er in b.get("entityRanges", []):
                ent = em.get(str(er.get("key")), {})
                etype = ent.get("type", "")
                data = ent.get("data", {})
                if etype == "MARKDOWN":
                    md.append("\n" + data.get("markdown", "") + "\n")
                elif etype == "MEDIA":
                    for m in data.get("mediaItems", []):
                        mid = m.get("mediaId", "")
                        url = ""
                        for me in article.get("media_entities", []):
                            if str(me.get("media_id")) == str(mid):
                                url = me.get("media_info", {}).get("original_img_url", "")
                                break
                        md.append(f"\n![image-{mid}]({url})\n" if url else f"\n[image: {mid}]\n")
                elif etype == "DIVIDER":
                    md.append("\n---\n")
                elif etype == "LINK":
                    url = data.get("url", "")
                    md.append(f"[{url}]({url})")
                elif etype == "TWEET":
                    md.append("\n[embedded tweet]\n")
                # TWEMOJI: skip
            continue

        # Inline bold spans (reverse offset order)
        styles = b.get("inlineStyleRanges", [])
        bold = sorted(
            [(s["offset"], s["offset"] + s["length"]) for s in styles if s.get("style") == "Bold"],
            reverse=True,
        )
        for off_start, off_end in bold:
            text = text[:off_start] + "**" + text[off_start:off_end] + "**" + text[off_end:]

        # Link entities on non-atomic blocks
        for er in b.get("entityRanges", []):
            ent = em.get(str(er.get("key")), {})
            if ent.get("type") == "LINK":
                url = ent.get("data", {}).get("url", "")
                o, l = er["offset"], er["length"]
                link_text = text[o:o + l] if o + l <= len(text) else url
                text = text[:o] + f"[{link_text}]({url})" + text[o + l:]

        if btype == "header-one":
            md.append(f"\n# {text}\n")
        elif btype == "header-two":
            md.append(f"\n## {text}\n")
        elif btype == "header-three":
            md.append(f"\n### {text}\n")
        elif btype == "blockquote":
            md.append(f"\n> {text}\n")
        elif btype == "unordered-list-item":
            md.append(f"- {text}")
        elif btype == "ordered-list-item":
            md.append(f"1. {text}")
        elif text.strip():
            md.append(text + "\n")

    return "\n".join(md)
