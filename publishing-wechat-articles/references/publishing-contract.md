# Publishing Contract

## Authorization Boundary

OSS uploads, Feishu messages, Feishu table writes, and WeChat actions are external side effects. They require a run created with `--mode publish` and a separate `publish RUN_ID --commit` command explicitly authorized by the user. A plan, capture, prepare, status, or dry run never grants that authority.

## Account Routing

Explicit `tech` or `parenting` intent wins. Otherwise route by title and tags using `config/accounts.toml`; unclear content defaults to `tech`. In `FEISHU_MODE=lark-cli`, both accounts hand off to `hermes-ali-ecs` (`oc_a8a9c19552135fec945d861a967bb465`) as the logged-in user. The account selects its own Bitable table. Credentials and table settings come from environment variables first, then the local runtime config; never print secrets.

## Artifact Upload

Object keys include account, normalized slug, and a content-hash prefix. This makes retries idempotent and changed content collision-resistant. Preserve MIME type and verify the public cover as `image/*` and article as `text/html`; upload success without public verification is incomplete.

Publication remains blocked until the HTML URL 返回 200 and the cover URL returns 200 with an image content type.

Checkpoint each returned URL before the next side effect. On an ambiguous timeout, set `needs-reconcile` and inspect remote state manually before retrying.

## Feishu Handoff

只发送 1 条 Markdown 消息 via `lark-cli im +messages-send --chat-id ... --as user --markdown ...`:

```markdown
**<final title>**

<summary>

📎 封面图：
<public cover URL>

📄 文章 HTML：
<public HTML URL>

打开 HTML → Ctrl+A → 复制 → 粘贴到公众号编辑器
```

Do not attach the image or send the body in chunks. Use a deterministic idempotency key, parse the full JSON response, persist the message ID, and read back the exact user-sent message before creating the tracking row.
The fixed payload contract is `标题 + 摘要 + 封面 URL + HTML URL`.

## Tracking Record

In `lark-cli` mode, the repository client reads field types and creates/reads records with `lark-cli api --as user`. `是否已发布` is a JSON boolean and starts as `false`, never a string.

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

After receiving a draft receipt, run `confirm-downstream` with the exact draft ID and assistant message ID. The CLI reads both the handoff and assistant reply before recording `draft-confirmed`. Handoff and draft creation are not public publication. Report `待发布` until a public WeChat article URL is confirmed, and update the checkbox only with separate authorization and an exact record ID.
