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

    def create_tracking(self, account: str, fields: dict[str, object]) -> str:
        target = self.config.runtime.accounts[account]
        response = self._request_json(
            f"{self.API_BASE}/bitable/v1/apps/{target.base_token}/tables/{target.table_id}/records",
            {"fields": fields},
            token=self._token(account),
        )
        record_id = response.get("data", {}).get("record", {}).get("record_id")
        if not record_id:
            raise FeishuError("Feishu response did not contain record_id")
        return record_id

    def _request_json(self, url: str, body: dict[str, object], *, token: str | None) -> dict[str, object]:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=payload, method="POST")
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
