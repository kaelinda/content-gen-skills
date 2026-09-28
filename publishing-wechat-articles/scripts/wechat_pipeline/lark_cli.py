from __future__ import annotations

import hashlib
import json
import os
import subprocess
from urllib.parse import urlsplit

from .feishu import FeishuClient, FeishuError


class LarkCliFeishuClient(FeishuClient):
    """Use the logged-in user's lark-cli session for delivery and Bitable."""

    HANDOFF_CHAT_ID = "oc_a8a9c19552135fec945d861a967bb465"

    def _chat_id(self, account: str) -> str:
        configured = super()._chat_id(account)
        if configured != self.HANDOFF_CHAT_ID:
            raise FeishuError("lark-cli handoff chat does not match hermes-ali-ecs")
        return configured

    def _call(self, args: list[str], *, input_text: str | None = None) -> dict:
        try:
            result = subprocess.run(
                ["lark-cli", *args], input=input_text, capture_output=True, text=True,
                env={**os.environ, "LARK_CLI_NO_PROXY": "1"}, timeout=60, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise FeishuError(f"lark-cli result uncertain: {type(exc).__name__}") from exc
        try:
            response = json.loads(result.stdout or result.stderr)
        except ValueError as exc:
            raise FeishuError("lark-cli did not return JSON; remote result needs reconciliation") from exc
        if not isinstance(response, dict):
            raise FeishuError("lark-cli returned an unexpected JSON shape")
        if result.returncode or response.get("ok") is False or response.get("code", 0) != 0:
            error = response.get("error", {})
            raise FeishuError(f"lark-cli request failed: {error.get('code', response.get('code', result.returncode))}: {error.get('message', response.get('msg', 'unknown'))}")
        return response

    def _token(self, account: str) -> str:
        return "lark-cli-user"

    def _request_json(self, url: str, body: dict | None, *, token: str | None) -> dict:
        parsed = urlsplit(url)
        path = parsed.path
        args = ["api", "GET" if body is None else "POST", path, "--as", "user"]
        if parsed.query:
            from urllib.parse import parse_qs
            params = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
            args.extend(["--params", json.dumps(params)])
        if body is not None:
            args.extend(["--data", "-"])
        return self._call(args, input_text=json.dumps(body, ensure_ascii=False) if body is not None else None)

    @staticmethod
    def handoff_text(title: str, summary: str, cover_url: str, html_url: str) -> str:
        return (f"**{title}**\n\n{summary}\n\n📎 封面图：\n{cover_url}\n\n"
                f"📄 文章 HTML：\n{html_url}\n\n打开 HTML → Ctrl+A → 复制 → 粘贴到公众号编辑器")

    def send_handoff(self, account: str, title: str, summary: str, cover_url: str, html_url: str) -> str:
        message = self.handoff_text(title, summary, cover_url, html_url)
        key = hashlib.sha256((self._chat_id(account) + "\n" + message).encode()).hexdigest()[:32]
        response = self._call(["im", "+messages-send", "--chat-id", self._chat_id(account),
                               "--as", "user", "--markdown", message, "--idempotency-key", key])
        data = response.get("data", {})
        message_id = data.get("message_id") or data.get("message", {}).get("message_id")
        if not message_id:
            raise FeishuError("lark-cli response has no message_id; reconcile before retry")
        return message_id

    @staticmethod
    def _content_text(item: dict) -> str:
        try:
            content = json.loads(item.get("body", {}).get("content", ""))
        except (TypeError, ValueError, AttributeError):
            return ""
        if isinstance(content.get("text"), str):
            return content["text"]
        lines = content.get("content_v2") or content.get("content") or []
        return "\n".join("".join(str(part.get("text", "")) for part in line if isinstance(part, dict))
                         for line in lines if isinstance(line, list))

    def inspect_handoff_history(self, account: str, expected_text: str, *, since_ms: int) -> dict[str, object]:
        page_token = ""
        scanned = 0
        for _ in range(20):
            query = {"container_id_type": "chat", "container_id": self._chat_id(account),
                     "page_size": 50, "sort_type": "ByCreateTimeDesc"}
            if page_token:
                query["page_token"] = page_token
            from urllib.parse import urlencode
            result = self._request_json(f"{self.API_BASE}/im/v1/messages?{urlencode(query)}", None, token=None)
            data = result.get("data", {})
            items = data.get("items", [])
            if not isinstance(items, list):
                raise FeishuError("message history did not return items")
            for item in items:
                scanned += 1
                normalized = self._content_text(item).replace("\u200b\n", "\n")
                if (item.get("chat_id") == self._chat_id(account)
                        and item.get("sender", {}).get("sender_type") == "user"
                        and normalized == expected_text):
                    return {"found": True, "message_id": item.get("message_id"), "scanned": scanned, "covered_since": True}
                if int(item.get("create_time", "0")) < since_ms:
                    return {"found": False, "scanned": scanned, "covered_since": True}
            if data.get("has_more") is False:
                return {"found": False, "scanned": scanned, "covered_since": True}
            page_token = data.get("page_token", "")
            if not page_token:
                raise FeishuError("message history pagination is incomplete")
        return {"found": False, "scanned": scanned, "covered_since": False}

    def verify_handoff(self, account: str, message_id: str, title: str, summary: str,
                       cover_url: str, html_url: str) -> dict:
        from urllib.parse import quote
        response = self._request_json(f"{self.API_BASE}/im/v1/messages/{quote(message_id, safe='')}", None, token=None)
        items = response.get("data", {}).get("items", [])
        matches = [item for item in items if item.get("message_id") == message_id]
        expected = self.handoff_text(title, summary, cover_url, html_url)
        if (len(matches) != 1 or matches[0].get("chat_id") != self._chat_id(account)
                or matches[0].get("deleted") is True
                or matches[0].get("sender", {}).get("sender_type") != "user"):
            raise FeishuError("exact handoff message was not read back")
        actual = self._content_text(matches[0])
        for value in (title, summary, cover_url, html_url, "Ctrl+A"):
            if value not in actual:
                raise FeishuError("handoff message readback lacks required content")
        return {"verified": True, "message_id": message_id, "text": expected, "method": "GET user message"}

    def verify_draft_receipt(self, account: str, assistant_message_id: str, handoff_message_id: str,
                             title: str, draft_id: str) -> dict:
        from urllib.parse import quote
        def get(message_id: str) -> dict:
            response = self._request_json(f"{self.API_BASE}/im/v1/messages/{quote(message_id, safe='')}", None, token=None)
            items = response.get("data", {}).get("items", [])
            if len(items) != 1 or items[0].get("message_id") != message_id:
                raise FeishuError("draft receipt message was not read back")
            return items[0]
        handoff, reply = get(handoff_message_id), get(assistant_message_id)
        body = self._content_text(reply)
        if (reply.get("chat_id") != self._chat_id(account)
                or reply.get("sender", {}).get("sender_type") != "app"
                or reply.get("deleted") is True
                or int(reply.get("create_time", "0")) <= int(handoff.get("create_time", "0"))
                or title not in body or draft_id not in body or "草稿ID" not in body):
            raise FeishuError("assistant draft receipt does not match this handoff")
        return {"verified": True, "method": "GET assistant message", "message_id": assistant_message_id}
