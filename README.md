# irnoti (Python)

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

## Behaviour shared by all irnoti SDKs

- **Auth:** `Authorization: Bearer irn_live_…`. Use an `irn_test_…` key with `lineId: "sandbox"` to try sends for free. Keys carry scopes (`sms.send`, `sms.read`, `wallet.read`, `phonebook.read|write`, `bot.send|read`, `verify.send|read`); a missing scope is a `403`.
- **Money** is integer **Rial** returned as a **string** (`"1960"`) — never parse it into a float.
- **Idempotency:** every send takes an idempotency key; retrying with the same key never sends twice (`replayed: true`). Automatic retries apply only to `GET`s and sends that carry a key.
- **Errors:** one error type carrying `status`, the API's machine `code` (`insufficient_balance`, `invalid_recipients`, `no_price`, … — empty for plain 401/403/404) and `details`, with helpers such as `isInsufficientBalance` / `isRateLimited` / `isUnauthenticated`.
- **Limits:** send 600 req/min, pattern 1200 req/min per IP (`429` when exceeded).
- **Webhooks:** verify the **raw** body against `X-Irnoti-Signature: t=<unix>,v1=<hex>` (HMAC-SHA256 of `"<t>.<body>"` with your `whsec_…` key); signatures older than 5 minutes are rejected.
- Bot creation/configuration and verify settings are panel-only and not exposed.

Sibling SDKs: [Laravel](https://github.com/irnoti/laravel-sms-panel-api) · [Node.js](https://github.com/irnoti/node-sms-panel-api) · [Python](https://github.com/irnoti/python-sms-panel-api) · [Go](https://github.com/irnoti/go-sms-panel-api) · [PHP](https://github.com/irnoti/php-sms-panel-api). API reference: [irnoti.com/docs](https://irnoti.com/docs).

MIT licensed.
