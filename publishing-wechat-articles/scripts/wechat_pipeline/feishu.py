from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .config import RepositoryConfig


class FeishuError(RuntimeError):
    pass


class FeishuClient:
    API_BASE = "https://open.feishu.cn/open-apis"

    def __init__(self, config: RepositoryConfig, *, transport=None):
        self.config = config
        self.transport = transport or self._default_transport
        self._tokens: dict[str, str] = {}

    def _credentials(self, account: str) -> tuple[str, str]:
        runtime = self.config.runtime
        if account == "tech":
            return runtime.tech_app_id, runtime.tech_app_secret
        if account == "parenting":
            return runtime.parenting_app_id, runtime.parenting_app_secret
        raise FeishuError(f"unknown account: {account}")

    def _token(self, account: str) -> str:
        if account in self._tokens:
            return self._tokens[account]
        app_id, app_secret = self._credentials(account)
        payload = self._request_json(
            f"{self.API_BASE}/auth/v3/tenant_access_token/internal",
            {"app_id": app_id, "app_secret": app_secret},
            token=None,
        )
        token = payload.get("tenant_access_token")
        if not token:
            raise FeishuError("Feishu token response did not contain tenant_access_token")
        self._tokens[account] = token
        return token

    def send_handoff(self, account: str, title: str, summary: str, cover_url: str, html_url: str) -> str:
        account_runtime = self.config.runtime.accounts[account]
        chat_id = account_runtime.chat_id or self.config.runtime.primary_chat_id
        content = f"标题：{title}\n摘要：{summary}\n封面：{cover_url}\nHTML：{html_url}"
        query = urllib.parse.urlencode({"receive_id_type": "chat_id"})
        response = self._request_json(
            f"{self.API_BASE}/im/v1/messages?{query}",
            {"receive_id": chat_id, "msg_type": "text", "content": json.dumps({"text": content}, ensure_ascii=False)},
            token=self._token(account),
        )
        message_id = response.get("data", {}).get("message_id")
        if not message_id:
            raise FeishuError("Feishu response did not contain message_id")
        return message_id

    def destination_key(self, account: str) -> str:
        """Same chat across accounts shares a queue; do not persist raw chat IDs."""
        import hashlib
        return hashlib.sha256(self._chat_id(account).encode("utf-8")).hexdigest()

    def _chat_id(self, account: str) -> str:
        target = self.config.runtime.accounts[account]
        chat_id = target.chat_id or self.config.runtime.primary_chat_id
        if not chat_id:
            raise FeishuError("handoff destination chat is missing")
        return chat_id

    @staticmethod
    def handoff_text(title: str, summary: str, cover_url: str, html_url: str) -> str:
        return f"标题：{title}\n摘要：{summary}\n封面：{cover_url}\nHTML：{html_url}"

    def verify_handoff(self, account: str, message_id: str, title: str, summary: str, cover_url: str, html_url: str) -> dict:
        target = urllib.parse.quote(message_id, safe="")
        response = self._request_json(f"{self.API_BASE}/im/v1/messages/{target}", None, token=self._token(account))
        items = response.get("data", {}).get("items", [])
        matches = [item for item in items if item.get("message_id") == message_id]
        if len(matches) != 1:
            raise FeishuError("exact handoff message was not read back")
        message = matches[0]
        try:
            content = json.loads(message.get("body", {}).get("content", ""))
        except (ValueError, TypeError) as exc:
            raise FeishuError("handoff message content is not readable") from exc
        expected = self.handoff_text(title, summary, cover_url, html_url)
        if (message.get("chat_id") != self._chat_id(account) or message.get("msg_type") != "text"
                or message.get("deleted") is True or content != {"text": expected}):
            raise FeishuError("handoff message readback differs from the exact intended payload")
        return {"verified": True, "message_id": message_id, "text": expected, "method": "GET"}

    def verify_tracking(self, account: str, record_id: str, fields: dict[str, object]) -> dict:
        target = urllib.parse.quote(record_id, safe="")
        response = self._request_json(f"{self._tracking_url(account)}/records/{target}", None, token=self._token(account))
        record = response.get("data", {}).get("record", {})
        actual = record.get("fields", {})
        if record.get("record_id") != record_id or actual.get("是否已发布") is not False:
            raise FeishuError("exact tracking record with boolean false was not read back")
        for name, expected in fields.items():
            value = actual.get(name)
            if isinstance(value, list) and all(isinstance(part, dict) and isinstance(part.get("text"), str) for part in value):
                value = "".join(part["text"] for part in value)
            if name in {"内容", "封面"} and isinstance(value, dict):
                value = value.get("link")
            if value != expected:
                raise FeishuError(f"tracking record readback differs: {name}")
        return {"verified": True, "record_id": record_id, "fields": actual, "method": "GET"}

    def _tracking_url(self, account: str) -> str:
        target = self.config.runtime.accounts[account]
        base = urllib.parse.quote(target.base_token, safe="")
        table = urllib.parse.quote(target.table_id, safe="")
        return f"{self.API_BASE}/bitable/v1/apps/{base}/tables/{table}"

    def tracking_schema(self, account: str) -> dict[str, int]:
        schema = {}
        page_token = ""
        seen = set()
        while True:
            query = urllib.parse.urlencode({"page_size": 100, "page_token": page_token})
            response = self._request_json(f"{self._tracking_url(account)}/fields?{query}", None, token=self._token(account))
            data = response.get("data", {})
            items = data.get("items")
            if not isinstance(items, list):
                raise FeishuError("tracking field GET did not return a field list")
            for item in items:
                name, field_type = item.get("field_name"), item.get("type")
                if not isinstance(name, str) or type(field_type) is not int or name in schema:
                    raise FeishuError("invalid or duplicate tracking field schema")
                schema[name] = field_type
            if data.get("has_more") is False:
                return schema
            page_token = data.get("page_token")
            if data.get("has_more") is not True or not page_token or page_token in seen:
                raise FeishuError("tracking schema pagination is incomplete")
            seen.add(page_token)

    def create_tracking(self, account: str, fields: dict[str, object]) -> str:
        required = {"标题", "摘要", "封面", "内容", "是否已发布"}
        if set(fields) != required or fields.get("是否已发布") is not False:
            raise FeishuError("tracking requires the five handoff fields and boolean false")
        schema = self.tracking_schema(account)  # Fresh GET before every record creation.
        payload = {}
        for name, value in fields.items():
            allowed = {7} if name == "是否已发布" else ({1, 15} if name in {"封面", "内容"} else {1})
            if schema.get(name) not in allowed:
                raise FeishuError(f"missing or incompatible tracking field: {name}")
            if name != "是否已发布" and not isinstance(value, str):
                raise FeishuError(f"tracking field must be text: {name}")
            payload[name] = {"link": value, "text": value} if schema[name] == 15 else value
        response = self._request_json(
            f"{self._tracking_url(account)}/records",
            {"fields": payload}, token=self._token(account),
        )
        record_id = response.get("data", {}).get("record", {}).get("record_id")
        if not record_id:
            raise FeishuError("Feishu response did not contain record_id")
        return record_id

    def _request_json(self, url: str, body: dict[str, object] | None, *, token: str | None) -> dict[str, object]:
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=payload, method="GET" if body is None else "POST")
        request.add_header("Content-Type", "application/json; charset=utf-8")
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        status, _, raw = self.transport(request, 25)
        if status < 200 or status >= 300:
            raise FeishuError(f"Feishu request failed with HTTP {status}")
        response = json.loads(raw.decode("utf-8"))
        if int(response.get("code", 0)) != 0:
            raise FeishuError(f"Feishu API error {response.get('code')}: {response.get('msg', 'unknown')}")
        return response

    @staticmethod
    def _default_transport(request: urllib.request.Request, timeout: int):
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), {key.lower(): value for key, value in response.headers.items()}, response.read()
