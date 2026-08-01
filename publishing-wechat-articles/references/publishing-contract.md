# Publishing Contract

## Authorization Boundary

OSS uploads, Feishu messages, Feishu table writes, and WeChat actions are external side effects. They require a run created with `--mode publish` and a separate `publish RUN_ID --commit` command explicitly authorized by the user. A plan, capture, prepare, status, or dry run never grants that authority.

## Account Routing

Explicit `tech` or `parenting` intent wins. Otherwise route by title and tags using `config/accounts.toml`; unclear content defaults to `tech`. Destination chat, Base token, table ID, and app credentials come only from `config/runtime.local.toml` and must never be printed.

## Artifact Upload

Object keys include account, normalized slug, and a content-hash prefix. This makes retries idempotent and changed content collision-resistant. Preserve MIME type and verify the public cover as `image/*` and article as `text/html`; upload success without public verification is incomplete.

Publication remains blocked until the HTML URL 返回 200 and the cover URL returns 200 with an image content type.

Checkpoint each returned URL before the next side effect. On an ambiguous timeout, set `needs-reconcile` and inspect remote state manually before retrying.

## Feishu Handoff

只发送 1 条消息 with exactly:

```text
标题：<final title>
摘要：<summary>
封面：<public cover URL>
HTML：<public HTML URL>
```

Do not attach the image or send the body in chunks. Persist the message ID before creating the tracking row.
The fixed payload contract is `标题 + 摘要 + 封面 URL + HTML URL`.

## Tracking Record

The repository client calls the Feishu Open API directly with verified TLS. `是否已发布` is a JSON boolean and starts as `false`, never a string.

| Account | Field insertion order |
|---|---|
| `tech` | `内容`, `是否已发布`, `标题`, `摘要`, `封面` |
| `parenting` | `是否已发布`, `标题`, `摘要`, `封面`, `内容` |

`内容` stores the HTML URL. Persist the record ID immediately.

## State Evidence

| State | Evidence |
|---|---|
| `rendered` | Local Markdown, cover, HTML, hashes, passing checks |
| `uploaded` | Both public URLs persisted and verified |
| `handed_off` | Message ID persisted |
| `recorded` | Tracking record ID persisted with checkbox false |
| `published` | Explicit human or publishing-assistant confirmation |
| `needs_reconcile` | A remote result is ambiguous; automated retry is disabled |

Handoff is not publication. Report `待发布` until explicit confirmation, and update the checkbox only with separate authorization and an exact record ID.
