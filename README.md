# irnoti (Python)

[![PyPI](https://img.shields.io/pypi/v/irnoti.svg)](https://pypi.org/project/irnoti/) [![tests](https://github.com/irnoti/python-sms-panel-api/actions/workflows/tests.yml/badge.svg)](https://github.com/irnoti/python-sms-panel-api/actions/workflows/tests.yml) [![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.md)

Python SDK for the irnoti API, built on `httpx`.

```bash
pip install irnoti
```

```python
from irnoti import Irnoti, IrnotiApiError, parse_webhook

irnoti = Irnoti(api_key="irn_live_…")  # base_url, timeout, retries, http_client are optional

try:
    line = irnoti.lines.list()[0]["id"]
    irnoti.sms.quote(line, "Hi", to="09121234567")
    irnoti.sms.send(line, "Hi", to=["09121234567"], group_ids=[12], idempotency_key="k1")
    irnoti.sms.pattern("k3f9a2", "09121234567", {"code": "4821"})
    irnoti.services.create("regional", {"province": "tehran", "count": 5000, "text": "Sale"})
except IrnotiApiError as e:
    if e.is_insufficient_balance:
        ...  # top up
    else:
        raise

# Flask: verify against the raw body
event = parse_webhook(request.get_data(), request.headers["X-Irnoti-Signature"], WEBHOOK_SECRET)
```

Multi-tenant: `irnoti.with_api_key(customer_key)` returns an independent client. Optional request fields use the API's camelCase names where they are passed as `**options` / dicts (e.g. `verify.create(to=…, ttlSec=300)`).

## Quickstart

New here? Follow **[QUICKSTART.md](QUICKSTART.md)**: install, get a key, send your first (free, sandbox) SMS in 5 minutes.

## What can this SDK do? (function reference)

Everything hangs off one client, `irnoti = Irnoti(api_key=...)`. Each group below is a *resource* (`irnoti.<resource>.<function>()`), and each links to its section in the API docs at [irnoti.com/docs](https://irnoti.com/docs) (open the docs panel and look for the section named in the "Docs section" column).

| Resource | Docs section | What it is for | Functions |
|---|---|---|---|
| `irnoti.sms` | SMS | Send text messages | `send` (single / bulk / group / scheduled / gradual), `quote` (exact price, no send), `pattern` (approved OTP/transactional template), `sos` (guaranteed delivery with failover) |
| `irnoti.messages` | SMS → Messages | Look up sent messages | `list`, `get`, `check` (ask operator for final delivery state) |
| `irnoti.batches` | SMS → Batches | Control scheduled/gradual sends | `scheduled`, `cancel`, `pause`, `resume` |
| `irnoti.lines` | SMS → Lines | Your sender numbers (you need a `line_id` to send) | `list` |
| `irnoti.wallet` | Wallet | Balance and history | `balance`, `transactions` |
| `irnoti.phonebook` | Phonebook | Contact groups and contacts | `groups`, `create_group`, `delete_group`, `contacts`, `add_contacts`, `import_csv`, `update_contact`, `delete_contact` |
| `irnoti.services` | Services | Provider products: `regional`, `targeted`, `peyamap`, `smart`, `messenger`, `voice`, `international` | `prices`, `international_rates`, `list`, `quote`, `create`, `get`, `refresh`, `cancel` |
| `irnoti.link_tracker` | Link tracker | SMS with tracked links, A/B variants, holdout | `send`, `holdouts`, `send_now`, `campaigns`, `campaign` |
| `irnoti.number_banks` | Number banks | Send to purchased/filtered number banks | `list`, `facets`, `quote`, `send` |
| `irnoti.verify` | Verify | OTP verification sessions (SMS or bot) | `info`, `create`, `list`, `get`, `cancel`, `stats` |
| `irnoti.bots` | Bot builder | Read bots, send messages/OTP through them (creating bots is panel-only) | `info`, `list`, `get`, `stats`, `subscribers`, `messages`, `send`, `otp`, `shop_orders`, `shop_stats` |
| `irnoti.broker` | Telegram broker | Run Telegram bots through a private relay | `list`, `get`, `create`, `rename`, `replace_token`, `rotate`, `delete`, `request`, `updates`, `webhook`, `set_webhook`, `delete_webhook` |
| `irnoti.voip` | VoIP | Click-to-call | `calls`, `price`, `call` |

Top-level helpers (no network call):

| Function | What it does |
|---|---|
| `Irnoti(api_key, base_url=, timeout=, retries=, http_client=)` | Create the client |
| `irnoti.with_api_key(key)` | New independent client for another customer key (multi-tenant) |
| `verify_webhook(raw_body, signature, secret)` | `True`/`False`: is this webhook really from irnoti? |
| `parse_webhook(raw_body, signature, secret)` | Verify and return the decoded event, raises `ValueError` if the signature is bad |
| `IrnotiApiError` | Raised on any non-2xx answer; has `.status`, `.code`, `.details` and helpers like `.is_insufficient_balance` |

Every function is a thin wrapper over one HTTP endpoint and returns the API's JSON as plain `dict`/`list`. Read the docstring in [`src/irnoti/resources.py`](src/irnoti/resources.py) for exact arguments, e.g. `help(irnoti.sms.send)`.

> Typical flow: `lines.list()` (pick a sender) → `sms.quote()` (see the cost) → `sms.send()` (with an `idempotency_key`) → `messages.get()` / webhook (delivery result). Use an `irn_test_…` key and `line_id="sandbox"` while experimenting: nothing is sent or charged.

### Telegram broker

```python
bot = irnoti.broker.create("Shop bot", botfather_token)    # scope broker.write (account owner); returns the relay `link`
irnoti.broker.request(bot["id"], "sendMessage", {"chat_id": 123, "text": "Hi"})   # scope broker.request
irnoti.broker.updates(bot["id"], limit=20)                  # pull mode
irnoti.broker.set_webhook(bot["id"], "https://example.com/tg", secret_token="s3cret")  # push mode
```

## Behaviour shared by all irnoti SDKs

- **Auth:** `Authorization: Bearer irn_live_…`. Use an `irn_test_…` key with `lineId: "sandbox"` to try sends for free. Keys carry scopes (`sms.send`, `sms.read`, `wallet.read`, `phonebook.read|write`, `bot.send|read`, `broker.read|write|request`, `verify.send|read`); a missing scope is a `403`.
- **Money** is integer **Rial** returned as a **string** (`"1960"`) — never parse it into a float.
- **Idempotency:** every send takes an idempotency key; retrying with the same key never sends twice (`replayed: true`). Automatic retries apply only to `GET`s and sends that carry a key.
- **Errors:** one error type carrying `status`, the API's machine `code` (`insufficient_balance`, `invalid_recipients`, `no_price`, … — empty for plain 401/403/404) and `details`, with helpers such as `isInsufficientBalance` / `isRateLimited` / `isUnauthenticated`.
- **Limits:** send 600 req/min, pattern 1200 req/min per IP (`429` when exceeded).
- **Webhooks:** verify the **raw** body against `X-Irnoti-Signature: t=<unix>,v1=<hex>` (HMAC-SHA256 of `"<t>.<body>"` with your `whsec_…` key); signatures older than 5 minutes are rejected.
- Bot-builder creation/configuration and verify settings are panel-only; Telegram broker bots can be managed through the API.

Sibling SDKs: [Laravel](https://github.com/irnoti/laravel-sms-panel-api) · [Node.js](https://github.com/irnoti/node-sms-panel-api) · [Python](https://github.com/irnoti/python-sms-panel-api) · [Go](https://github.com/irnoti/go-sms-panel-api) · [PHP](https://github.com/irnoti/php-sms-panel-api). API reference: [irnoti.com/docs](https://irnoti.com/docs).

MIT licensed.
