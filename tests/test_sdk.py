import hashlib
import hmac
import json
import time
from datetime import datetime, timezone

import httpx
import pytest

from irnoti import Irnoti, IrnotiApiError, parse_webhook, verify_webhook


def make(status=200, payload=None):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return httpx.Response(status, json=payload) if payload is not None else httpx.Response(status)

    api = Irnoti("irn_test_x", base_url="https://irnoti.test/", retries=0,
                 http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    return api, calls


def test_send_builds_request():
    api, calls = make(201, {"batchId": "1", "count": 2, "totalPrice": "1960", "replayed": False})
    r = api.sms.send(1, "hi", to=["0912"], group_ids=[12], idempotency_key="k1",
                     scheduled_at=datetime(2026, 10, 20, 9, tzinfo=timezone.utc))
    assert r["totalPrice"] == "1960"
    req = calls[0]
    assert str(req.url) == "https://irnoti.test/v1/sms/send"
    assert req.headers["authorization"] == "Bearer irn_test_x"
    assert req.headers["idempotency-key"] == "k1"
    assert json.loads(req.content) == {"lineId": "1", "to": ["0912"], "groupIds": ["12"], "text": "hi",
                                       "scheduledAt": "2026-10-20T09:00:00+00:00"}


def test_query_skips_none_and_pattern_params_object():
    api, calls = make(200, [])
    api.messages.list(take=2, before=90)
    assert str(calls[0].url) == "https://irnoti.test/v1/sms/messages?take=2&before=90"
    api.bots.shop_orders(5)
    assert str(calls[1].url) == "https://irnoti.test/v1/botbuilder/bots/5/shop/orders"
    api.sms.pattern("k3f9a2", "0912")
    assert json.loads(calls[2].content)["params"] == {}


def test_errors():
    api, _ = make(400, {"statusCode": 400, "code": "invalid_recipients", "details": ["0912"]})
    with pytest.raises(IrnotiApiError) as ei:
        api.sms.send(1, "x", to="0912")
    e = ei.value
    assert (e.status, e.code, e.details) == (400, "invalid_recipients", ["0912"])
    assert e.is_invalid_recipients and e.is_validation_error

    api, _ = make(402, {"statusCode": 402, "code": "insufficient_balance", "message": ["Not", "enough"]})
    with pytest.raises(IrnotiApiError) as ei:
        api.wallet.balance()
    assert ei.value.is_insufficient_balance and str(ei.value) == "Not enough"

    api, _ = make(401, {"statusCode": 401, "message": "Invalid API key"})
    with pytest.raises(IrnotiApiError) as ei:
        api.lines.list()
    assert ei.value.is_unauthenticated and ei.value.code == ""


def test_204_and_csv_multipart():
    api, calls = make(204)
    assert api.batches.pause(7) is None
    assert str(calls[0].url) == "https://irnoti.test/v1/sms/batches/7/pause"
    api, calls = make(200, {"added": 1, "duplicates": 0, "invalid": 0})
    assert api.phonebook.import_csv(12, "0912,Ali\n")["added"] == 1
    assert calls[0].headers["content-type"].startswith("multipart/form-data")


def test_with_api_key():
    api, _ = make()
    assert api.with_api_key("irn_live_y") is not api


def test_webhook():
    body = '{"id":"1","event":"message.delivered","createdAt":"x","data":{}}'

    def sign(t, b=body):
        return f"t={t},v1=" + hmac.new(b"whsec", f"{t}.{b}".encode(), hashlib.sha256).hexdigest()

    now = int(time.time())
    assert verify_webhook(body, sign(now), "whsec")
    assert parse_webhook(body.encode(), sign(now), "whsec")["event"] == "message.delivered"
    assert not verify_webhook(body + " ", sign(now), "whsec")
    assert not verify_webhook(body, sign(now - 3600), "whsec")
    assert not verify_webhook(body, "junk", "whsec")
    with pytest.raises(ValueError):
        parse_webhook(body, "junk", "whsec")


def test_broker_routes_and_bodies():
    api, calls = make(200, {})
    api.broker.request(7, "sendMessage", {"chat_id": 1, "text": "hi"})
    api.broker.updates(7, limit=10, allowed_updates=["message"])
    api.broker.set_webhook(7, "https://example.com/hook", secret_token="s")
    api.broker.delete_webhook(7, True)
    api.broker.replace_token(7, "123456:ABCDEF-token")
    assert [(c.method, c.url.path) for c in calls] == [
        ("POST", "/v1/broker/bots/7/request"), ("POST", "/v1/broker/bots/7/updates"), ("PUT", "/v1/broker/bots/7/webhook"),
        ("DELETE", "/v1/broker/bots/7/webhook"), ("PUT", "/v1/broker/bots/7/token"),
    ]
    assert json.loads(calls[0].content) == {"method": "sendMessage", "params": {"chat_id": 1, "text": "hi"}}
    assert json.loads(calls[1].content) == {"limit": 10, "allowedUpdates": ["message"]}
    assert json.loads(calls[3].content) == {"dropPendingUpdates": True}
