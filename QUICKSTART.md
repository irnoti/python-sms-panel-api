# Quickstart (Python)

Goal: send your first SMS with the irnoti Python SDK in about 5 minutes, without spending money.

Full function list: [README → function reference](README.md#what-can-this-sdk-do-function-reference). Full API reference (the docs panel): [irnoti.com/docs](https://irnoti.com/docs).

## 1. Install

```bash
pip install irnoti        # Python 3.9+
```

## 2. Get an access key

In the irnoti panel create an **access key** (docs panel → *Authentication / Access keys*).

- `irn_test_…` — sandbox key: nothing is sent, nothing is charged. **Start with this.**
- `irn_live_…` — real key: sends real SMS and charges your wallet.

Keep it in an environment variable, never in source control:

```bash
export IRNOTI_API_KEY=irn_test_xxxxxxxx
```

## 3. Send a test SMS (sandbox, free)

```python
import os
from irnoti import Irnoti, IrnotiApiError

irnoti = Irnoti(api_key=os.environ["IRNOTI_API_KEY"])

try:
    # How much would it cost? (no send, no charge)
    print(irnoti.sms.quote("sandbox", "Hello", to="09121234567"))

    # Send. idempotency_key makes retries safe: the same key never sends twice.
    result = irnoti.sms.send("sandbox", "Hello", to="09121234567", idempotency_key="my-first-send")
    print(result)   # {'batchId': ..., 'count': 1, 'totalPrice': '...', 'replayed': False}
except IrnotiApiError as e:
    print(e.status, e.code, e.message)
```

`totalPrice` is an integer amount in **Rial, returned as a string** — don't convert it to float.

## 4. Go live

1. Switch to an `irn_live_…` key.
2. Find your sender number: `irnoti.lines.list()` → use its `id` as `line_id` instead of `"sandbox"`.
3. Check money: `irnoti.wallet.balance()`.
4. Always `quote()` first for big sends, and always pass an `idempotency_key` to `send()`.

```python
line = irnoti.lines.list()[0]["id"]
irnoti.sms.send(line, "Hello", to=["09121234567"], idempotency_key="order-1001")
```

## 5. Common tasks — which function, which docs section

| I want to… | Call | Docs section |
|---|---|---|
| Send one/many SMS | `irnoti.sms.send(line, text, to=[...])` | SMS |
| Send to a contact group | `irnoti.sms.send(line, text, group_ids=[12])` | SMS + Phonebook |
| Schedule / drip-send | `irnoti.sms.send(..., scheduled_at=..., gradual={"chunkSize": 500, "intervalMinutes": 10})` | SMS |
| Send an OTP with an approved template | `irnoti.sms.pattern("template_code", "0912…", {"code": "4821"})` | SMS → Pattern |
| Check delivery | `irnoti.messages.get(id)` or a webhook | SMS → Messages / Webhooks |
| Manage contacts | `irnoti.phonebook.create_group(...)`, `add_contacts(...)`, `import_csv(...)` | Phonebook |
| Check balance | `irnoti.wallet.balance()` | Wallet |
| Phone verification flow | `irnoti.verify.create(to="0912…", ttlSec=300)` | Verify |
| Telegram bot relay | `irnoti.broker.create(label, token)` | Telegram broker |

(Every function: [README reference table](README.md#what-can-this-sdk-do-function-reference).)

## 6. Handle errors

```python
try:
    irnoti.sms.send(line, "Hi", to="0912…")
except IrnotiApiError as e:
    if e.is_insufficient_balance:   # top up the wallet
        ...
    elif e.is_rate_limited:         # 429: slow down (send limit is 600 req/min)
        ...
    elif e.is_invalid_recipients:
        print(e.details)
    else:
        raise
```

## 7. Receive delivery webhooks

Verify the **raw** request body (not re-serialised JSON) against the `X-Irnoti-Signature` header with your `whsec_…` secret:

```python
# Flask
from flask import Flask, request, abort
from irnoti import parse_webhook

app = Flask(__name__)

@app.post("/irnoti/webhook")
def webhook():
    try:
        event = parse_webhook(request.get_data(), request.headers.get("X-Irnoti-Signature", ""), WEBHOOK_SECRET)
    except ValueError:
        abort(400)
    print(event)
    return "", 204
```

Signatures older than 5 minutes are rejected.

## Next

- Browse everything in the [function reference](README.md#what-can-this-sdk-do-function-reference).
- Use `help(irnoti.sms.send)` in a Python shell to see each function's arguments.
- Multi-tenant app? `irnoti.with_api_key(customer_key)`.
