from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Union

Id = Union[str, int]
Json = Dict[str, Any]


def _e(v: Id) -> str:
    from urllib.parse import quote

    return quote(str(v), safe="")


def _idem(key: Optional[str]) -> Optional[Dict[str, str]]:
    return {"Idempotency-Key": key} if key else None


def _ids(g: Optional[Iterable[Id]]) -> Optional[List[str]]:
    return [str(x) for x in g] if g else None


class _Resource:
    def __init__(self, t: Any):
        self._t = t


class Sms(_Resource):
    def send(
        self,
        line_id: Union[Id, str],
        text: str,
        to: Union[str, List[str], None] = None,
        group_ids: Optional[Iterable[Id]] = None,
        scheduled_at: Union[datetime, str, None] = None,
        gradual: Optional[Mapping[str, int]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Json:
        """Scope ``sms.send``. ``line_id="sandbox"`` + an ``irn_test_`` key sends nothing and costs nothing.

        ``scheduled_at``: 1 minute – 60 days ahead. ``gradual``: ``{"chunkSize": 500, "intervalMinutes": 10}``.
        Returns ``{batchId, count, totalPrice, replayed}`` (``totalPrice`` is integer Rial as a string).
        """
        return self._t.request("POST", "/sms/send", headers=_idem(idempotency_key), body={
            "lineId": str(line_id), "to": to, "groupIds": _ids(group_ids), "text": text,
            "scheduledAt": scheduled_at, "gradual": dict(gradual) if gradual else None,
        })

    def quote(self, line_id: Union[Id, str], text: str, to: Union[str, List[str], None] = None,
              group_ids: Optional[Iterable[Id]] = None) -> Json:
        """Scope ``sms.read``: exact cost without sending or charging."""
        return self._t.request("POST", "/sms/quote", body={
            "lineId": str(line_id), "to": to, "groupIds": _ids(group_ids), "text": text})

    def pattern(self, code: str, to: str, params: Optional[Mapping[str, Any]] = None,
                idempotency_key: Optional[str] = None) -> Json:
        """Approved template (OTP / transactional). Scope ``sms.send``."""
        return self._t.request("POST", "/sms/pattern", headers=_idem(idempotency_key),
                               body={"code": code, "to": to, "params": dict(params or {})})

    def sos(self, to: Union[str, List[str]], text: str, idempotency_key: Optional[str] = None) -> Json:
        """Guaranteed delivery with provider failover (<= 200 recipients, ``sms.sos`` tariff)."""
        return self._t.request("POST", "/sms/sos", headers=_idem(idempotency_key), body={"to": to, "text": text})


class Messages(_Resource):
    def list(self, take: Optional[int] = None, before: Optional[Id] = None) -> List[Json]:
        return self._t.request("GET", "/sms/messages", query={"take": take, "before": None if before is None else str(before)})

    def get(self, id: Id) -> Json:
        return self._t.request("GET", f"/sms/messages/{_e(id)}")

    def check(self, id: Id) -> Json:
        """Ask the operator for the final delivery state now (30/min)."""
        return self._t.request("POST", f"/sms/messages/{_e(id)}/check")


class Batches(_Resource):
    def scheduled(self) -> List[Json]:
        return self._t.request("GET", "/sms/scheduled")

    def cancel(self, batch_id: Id) -> Json:
        return self._t.request("POST", f"/sms/batches/{_e(batch_id)}/cancel")

    def pause(self, batch_id: Id) -> None:
        self._t.request("POST", f"/sms/batches/{_e(batch_id)}/pause")

    def resume(self, batch_id: Id) -> None:
        self._t.request("POST", f"/sms/batches/{_e(batch_id)}/resume")


class Lines(_Resource):
    def list(self) -> List[Json]:
        return self._t.request("GET", "/sms/lines")


class Wallet(_Resource):
    def balance(self) -> Json:
        return self._t.request("GET", "/wallet")

    def transactions(self) -> List[Json]:
        return self._t.request("GET", "/wallet/transactions")


class Phonebook(_Resource):
    def groups(self) -> List[Json]:
        return self._t.request("GET", "/phonebook/groups")

    def create_group(self, name: str) -> Json:
        return self._t.request("POST", "/phonebook/groups", body={"name": name})

    def delete_group(self, id: Id) -> None:
        self._t.request("DELETE", f"/phonebook/groups/{_e(id)}")

    def contacts(self, group_id: Id, take: Optional[int] = None, after: Optional[Id] = None, q: Optional[str] = None) -> Any:
        return self._t.request("GET", f"/phonebook/groups/{_e(group_id)}/contacts",
                               query={"take": take, "after": None if after is None else str(after), "q": q})

    def add_contacts(self, group_id: Id, contacts: List[Mapping[str, Any]]) -> Json:
        """Up to 10,000 per call; invalid/duplicate numbers are counted, not fatal."""
        return self._t.request("POST", f"/phonebook/groups/{_e(group_id)}/contacts", body={"contacts": contacts})

    def import_csv(self, group_id: Id, csv: Union[str, bytes], filename: str = "contacts.csv") -> Json:
        data = csv.encode() if isinstance(csv, str) else csv
        return self._t.request("POST", f"/phonebook/groups/{_e(group_id)}/import",
                               files={"file": (filename, data, "text/csv")})

    def update_contact(self, id: Id, **attributes: Any) -> Json:
        """camelCase API fields: mobile, name, lastName, company, email, city, note, birth, fields, optedOut."""
        return self._t.request("PATCH", f"/phonebook/contacts/{_e(id)}", body=attributes)

    def delete_contact(self, id: Id) -> None:
        self._t.request("DELETE", f"/phonebook/contacts/{_e(id)}")


class Services(_Resource):
    """regional, targeted, peyamap, smart, messenger, voice, international: quote -> create -> refresh -> cancel."""

    def prices(self) -> List[Json]:
        return self._t.request("GET", "/services/prices")

    def international_rates(self) -> Any:
        return self._t.request("GET", "/services/international/rates")

    def list(self, product: str) -> List[Json]:
        return self._t.request("GET", f"/services/{product}")

    def quote(self, product: str, body: Mapping[str, Any]) -> Json:
        return self._t.request("POST", f"/services/{product}/quote", body=dict(body))

    def create(self, product: str, body: Mapping[str, Any]) -> Json:
        return self._t.request("POST", f"/services/{product}", body=dict(body))

    def get(self, product: str, id: Id) -> Json:
        return self._t.request("GET", f"/services/{product}/{_e(id)}")

    def refresh(self, product: str, id: Id) -> Json:
        return self._t.request("POST", f"/services/{product}/{_e(id)}/refresh")

    def cancel(self, product: str, id: Id) -> Json:
        """Only before the provider starts; refunded."""
        return self._t.request("POST", f"/services/{product}/{_e(id)}/cancel")


class LinkTracker(_Resource):
    def send(self, line_id: Id, text: str, url: str, to: Optional[List[str]] = None,
             group_ids: Optional[Iterable[Id]] = None, variants: Optional[List[str]] = None,
             holdout_percent: Optional[int] = None, decide_after_minutes: Optional[int] = None) -> Json:
        return self._t.request("POST", "/link-tracker/send", body={
            "lineId": str(line_id), "text": text, "url": url, "to": to, "groupIds": _ids(group_ids),
            "variants": variants, "holdoutPercent": holdout_percent, "decideAfterMinutes": decide_after_minutes})

    def holdouts(self) -> List[Json]:
        return self._t.request("GET", "/link-tracker/holdouts")

    def send_now(self, holdout_id: Id) -> Json:
        return self._t.request("POST", f"/link-tracker/holdouts/{_e(holdout_id)}/send-now")

    def campaigns(self) -> List[Json]:
        return self._t.request("GET", "/link-tracker/campaigns")

    def campaign(self, batch_id: Id) -> Json:
        return self._t.request("GET", f"/link-tracker/campaigns/{_e(batch_id)}")


class NumberBanks(_Resource):
    def list(self) -> List[Json]:
        return self._t.request("GET", "/number-banks")

    def facets(self, bank_id: Id) -> Json:
        return self._t.request("GET", f"/number-banks/{_e(bank_id)}/facets")

    def _body(self, bank_id: Id, count: int, line_id: Id, text: str, filters: Optional[Mapping[str, str]]) -> Json:
        return {"bankId": str(bank_id), "count": count, "lineId": str(line_id), "text": text, "filters": dict(filters or {})}

    def quote(self, bank_id: Id, count: int, line_id: Id, text: str, filters: Optional[Mapping[str, str]] = None) -> Json:
        return self._t.request("POST", "/number-banks/quote", body=self._body(bank_id, count, line_id, text, filters))

    def send(self, bank_id: Id, count: int, line_id: Id, text: str, filters: Optional[Mapping[str, str]] = None,
             idempotency_key: Optional[str] = None) -> Json:
        return self._t.request("POST", "/number-banks/send", headers=_idem(idempotency_key),
                               body=self._body(bank_id, count, line_id, text, filters))


class Verify(_Resource):
    def info(self) -> Json:
        return self._t.request("GET", "/verify/info")

    def create(self, to: Optional[str] = None, bot: Optional[Mapping[str, Any]] = None, **options: Any) -> Json:
        """Exactly one of ``to`` (mobile) or ``bot`` (``{"id", "ref"}``). Options (camelCase): lineId, mode, length,
        ttlSec, maxAttempts, redirectUrl, callbackUrl, clientRef, brandName, brandColor."""
        return self._t.request("POST", "/verify/sessions", body={**options, "to": to, "bot": dict(bot) if bot else None})

    def list(self, take: Optional[int] = None, before: Optional[Id] = None) -> List[Json]:
        return self._t.request("GET", "/verify/sessions", query={"take": take, "before": None if before is None else str(before)})

    def get(self, id: Id) -> Json:
        return self._t.request("GET", f"/verify/sessions/{_e(id)}")

    def cancel(self, id: Id) -> None:
        self._t.request("POST", f"/verify/sessions/{_e(id)}/cancel")

    def stats(self) -> Json:
        return self._t.request("GET", "/verify/stats")


class Bots(_Resource):
    """Bot builder. Creating/configuring bots is panel-only; ``to``/``message`` follow the panel's bot sender shapes."""

    def info(self) -> Json:
        return self._t.request("GET", "/botbuilder/info")

    def list(self) -> List[Json]:
        return self._t.request("GET", "/botbuilder/bots")

    def get(self, bot_id: Id) -> Json:
        return self._t.request("GET", f"/botbuilder/bots/{_e(bot_id)}")

    def stats(self, bot_id: Id) -> Json:
        return self._t.request("GET", f"/botbuilder/bots/{_e(bot_id)}/stats")

    def subscribers(self, bot_id: Id, take: Optional[int] = None, before: Optional[Id] = None) -> List[Json]:
        return self._t.request("GET", f"/botbuilder/bots/{_e(bot_id)}/subscribers",
                               query={"take": take, "before": None if before is None else str(before)})

    def messages(self, bot_id: Id, take: Optional[int] = None, before: Optional[Id] = None) -> List[Json]:
        return self._t.request("GET", f"/botbuilder/bots/{_e(bot_id)}/messages",
                               query={"take": take, "before": None if before is None else str(before)})

    def send(self, bot_id: Id, to: Mapping[str, Any], message: Mapping[str, Any], idempotency_key: Optional[str] = None) -> Json:
        return self._t.request("POST", f"/botbuilder/bots/{_e(bot_id)}/send", headers=_idem(idempotency_key),
                               body={"to": dict(to), "message": dict(message)})

    def otp(self, bot_id: Id, to: Mapping[str, Any], length: Optional[int] = None, template: Optional[str] = None,
            idempotency_key: Optional[str] = None) -> Json:
        return self._t.request("POST", f"/botbuilder/bots/{_e(bot_id)}/otp", headers=_idem(idempotency_key),
                               body={"to": dict(to), "length": length, "template": template})

    def shop_orders(self, bot_id: Id, status: Optional[str] = None) -> List[Json]:
        return self._t.request("GET", f"/botbuilder/bots/{_e(bot_id)}/shop/orders", query={"status": status})

    def shop_stats(self, bot_id: Id) -> Json:
        return self._t.request("GET", f"/botbuilder/bots/{_e(bot_id)}/shop/stats")


class Broker(_Resource):
    """Telegram broker: register a bot token, get a private relay link, call the Bot API and pull updates through it."""

    def list(self) -> List[Json]:
        return self._t.request("GET", "/broker/bots")

    def get(self, id: Id) -> Json:
        return self._t.request("GET", f"/broker/bots/{_e(id)}")

    def create(self, label: str, token: str) -> Json:
        """Scope ``broker.write``, account owner only. The token is never returned afterwards; the response carries the relay ``link``."""
        return self._t.request("POST", "/broker/bots", body={"label": label, "token": token})

    def rename(self, id: Id, label: str) -> None:
        self._t.request("PATCH", f"/broker/bots/{_e(id)}", body={"label": label})

    def replace_token(self, id: Id, token: str) -> Json:
        """Swap in a regenerated BotFather token. Clears the return webhook."""
        return self._t.request("PUT", f"/broker/bots/{_e(id)}/token", body={"token": token})

    def rotate(self, id: Id) -> Json:
        """New relay link; the previous one stops working."""
        return self._t.request("POST", f"/broker/bots/{_e(id)}/rotate")

    def delete(self, id: Id) -> None:
        self._t.request("DELETE", f"/broker/bots/{_e(id)}")

    def request(self, id: Id, method: str, params: Optional[Mapping[str, Any]] = None) -> Json:
        """Scope ``broker.request``: call any Telegram Bot API method. Returns ``{status, response}``."""
        return self._t.request("POST", f"/broker/bots/{_e(id)}/request", body={"method": method, "params": dict(params or {})})

    def updates(self, id: Id, offset: Optional[int] = None, limit: Optional[int] = None, timeout: Optional[int] = None,
                allowed_updates: Optional[List[str]] = None) -> Json:
        """Scope ``broker.request``: pull updates (long-poll ``timeout`` <= 25 s)."""
        return self._t.request("POST", f"/broker/bots/{_e(id)}/updates",
                               body={"offset": offset, "limit": limit, "timeout": timeout, "allowedUpdates": allowed_updates})

    def webhook(self, id: Id) -> Json:
        return self._t.request("GET", f"/broker/bots/{_e(id)}/webhook")

    def set_webhook(self, id: Id, url: str, secret_token: Optional[str] = None, allowed_updates: Optional[List[str]] = None,
                    drop_pending_updates: Optional[bool] = None) -> Json:
        return self._t.request("PUT", f"/broker/bots/{_e(id)}/webhook",
                               body={"url": url, "secretToken": secret_token, "allowedUpdates": allowed_updates,
                                     "dropPendingUpdates": drop_pending_updates})

    def delete_webhook(self, id: Id, drop_pending_updates: Optional[bool] = None) -> Json:
        return self._t.request("DELETE", f"/broker/bots/{_e(id)}/webhook", body={"dropPendingUpdates": drop_pending_updates})


class Voip(_Resource):
    def calls(self) -> List[Json]:
        return self._t.request("GET", "/voip/calls")

    def price(self) -> Json:
        return self._t.request("GET", "/voip/price")

    def call(self, from_: str, to: str) -> Json:
        return self._t.request("POST", "/voip/calls", body={"from": from_, "to": to})
