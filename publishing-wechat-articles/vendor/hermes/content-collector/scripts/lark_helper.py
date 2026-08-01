#!/usr/bin/env python3
"""
lark-cli wrapper — handles all known parameter pitfalls.

Usage:
    from lark_helper import lark_send_markdown, lark_send_post, lark_create_record

    # Send markdown message
    lark_send_markdown("oc_xxx", "Hello **world**")

    # Send post message (title + content)
    lark_send_post("oc_xxx", "标题", "摘要", "封面URL", "HTML_URL")

    # Create table record
    lark_create_record("base_token", "table_id", {"字段1": "值1"})
"""

import json
import os
import re
import subprocess


def _run_lark(args: list[str], timeout: int = 30) -> dict:
    """Run lark-cli command with error handling.
    
    Pitfalls handled:
    - --as user flag doesn't exist for im +messages-send
    - --chat not --chat-id
    - "ok": true has a space, string matching fails
    - TLS timeout: add LARK_CLI_NO_PROXY=1
    - stderr contains [lark-cli] warnings, must filter
    """
    env = {**os.environ, "LARK_CLI_NO_PROXY": "1"}
    
    try:
        proc = subprocess.run(
            ["lark-cli"] + args,
            capture_output=True, text=True, timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    
    # Parse JSON from stdout (filter stderr warnings)
    stdout = re.sub(r'^\[lark-cli\].*?\n', '', proc.stdout, flags=re.MULTILINE).strip()
    
    if not stdout:
        return {"ok": False, "error": f"empty output (stderr: {proc.stderr[:200]})"}
    
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": f"invalid JSON: {stdout[:200]}"}
    
    return data


def lark_send_markdown(chat_id: str, content: str, as_user: bool = True) -> dict:
    """Send markdown message to Feishu chat.
    
    Args:
        chat_id: Chat ID (oc_xxx format)
        content: Markdown content
        as_user: If True, send as user (default). If False, send as bot.
    
    Returns:
        {"ok": True, "message_id": "..."} or {"ok": False, "error": "..."}
    
    Pitfalls:
    - Don't use --as user flag (doesn't exist for im +messages-send)
    - Don't use --chat, use --chat-id
    - Content > 900 chars: split by paragraphs first
    """
    args = ["im", "+messages-send", "--chat-id", chat_id, "--markdown", content]
    return _run_lark(args)


def lark_send_post(chat_id: str, title: str, summary: str, 
                    cover_url: str = "", html_url: str = "") -> dict:
    """Send post message (title + summary + URLs) to Feishu chat.
    
    Args:
        chat_id: Chat ID (oc_xxx format)
        title: Article title
        summary: Article summary
        cover_url: Cover image OSS URL
        html_url: HTML article OSS URL
    def lark_send_post(chat_id: str, title: str, summary: str,
                        cover_url: str = "", html_url: str = "") -> dict:
        """Send post message (title + summary + URLs) to Feishu chat.

        Uses --markdown directly (stdin pipe doesn't work with im +messages-send).
        """
        lines = [f"标题：{title}\n", f"摘要：{summary}\n"]
        if cover_url:
            lines.append(f"📎 封面图：{cover_url}\n")
        if html_url:
            lines.append(f"📄 HTML 版本：{html_url}")
        content = "\n".join(lines)

        args = ["im", "+messages-send", "--chat-id", chat_id, "--markdown", content]
        return _run_lark(args)
# ── Feishu Table Field Mappings ──────────────────────────────────────────────
# Field order must match table schema. Different accounts have different orders.

TABLE_FIELDS = {
    "tech": {
        "base_token": "B4kUbyJxeaSw1Xszsf1c0rARn0d",
        "table_id": "tbllNygCgg4a4eWM",
        "fields_order": ["内容", "是否已发布", "标题", "摘要", "封面"],
    },
    "parenting": {
        "base_token": "B4kUbyJxeaSw1Xszsf1c0rARn0d",
        "table_id": "tbl20LZ82JPLOnpM",
        "fields_order": ["标题", "摘要", "封面", "内容", "是否已发布"],
    },
}


def lark_create_article_record(account: str, title: str, summary: str,
                                cover_url: str = "", html_url: str = "",
                                published: bool = False) -> dict:
    """Create article record in Feishu bitable with correct field order.
    
    Args:
        account: "tech" or "parenting"
        title: Article title
        summary: Article summary
        cover_url: Cover image OSS URL
        html_url: HTML article OSS URL
        published: Whether already published (default False)
    
    Returns:
        {"ok": True, "record_id": "..."} or {"ok": False, "error": "..."}
    
    This function handles the fragile field order automatically:
    - tech: [内容, 是否已发布, 标题, 摘要, 封面]
    - parenting: [标题, 摘要, 封面, 内容, 是否已发布]
    """
    config = TABLE_FIELDS.get(account)
    if not config:
        return {"ok": False, "error": f"unknown account: {account}. Use 'tech' or 'parenting'"}
    
    # Build fields dict (order doesn't matter for the dict, but keys must match)
    field_values = {
        "标题": title,
        "摘要": summary,
        "封面": cover_url,
        "内容": html_url,
        "是否已发布": published,
    }
    
    return lark_create_record(
        config["base_token"],
        config["table_id"],
        field_values,
    )


def lark_create_record(base_token: str, table_id: str, fields: dict,
                        as_user: bool = True) -> dict:
    """Create a record in Feishu bitable.
    
    Args:
        base_token: Base token (e.g., B4kUbyJxeaSw1Xszsf1c0rARn0d)
        table_id: Table ID (e.g., tbllNygCgg4a4eWM)
        fields: Dict of field_name -> value
        as_user: If True, use --as user (required for bitable writes)
    
    Returns:
        {"ok": True, "record_id": "..."} or {"ok": False, "error": "..."}
    
    Pitfalls:
    - Must use --as user (bot has no bitable:field:write permission)
    - Must use +record-batch-create not +record-create
    - Field order must match table schema
    - Checkbox fields use boolean, not string
    - Large JSON: use stdin pipe, not CLI arg
    """
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records"
    
    data = {"fields": fields}
    
    # Write to temp file and pipe
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f, ensure_ascii=False)
        tmp_path = f.name
    
    try:
        args = ["api", "POST", url]
        if as_user:
            args.extend(["--as", "user"])
        args.extend(["--data", "-"])
        
        env = {**os.environ, "LARK_CLI_NO_PROXY": "1"}
        proc = subprocess.run(
            ["lark-cli"] + args,
            input=open(tmp_path).read(),
            capture_output=True, text=True, timeout=60, env=env,
        )
        stdout = re.sub(r'^\[lark-cli\].*?\n', '', proc.stdout, flags=re.MULTILINE).strip()
        try:
            result = json.loads(stdout) if stdout else {"ok": False, "error": "empty"}
            # Extract record_id if present
            if result.get("code") == 0 and "data" in result:
                rec = result["data"].get("record", {})
                result["record_id"] = rec.get("record_id")
            return result
        except json.JSONDecodeError:
            return {"ok": False, "error": f"invalid JSON: {stdout[:200]}"}
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    # Quick test
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 lark_helper.py <chat_id> <message>")
        sys.exit(1)
    result = lark_send_markdown(sys.argv[1], sys.argv[2])
    print(json.dumps(result, ensure_ascii=False, indent=2))
