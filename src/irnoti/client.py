from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping, Optional, Union

import httpx

from .errors import IrnotiApiError
from .resources import (
    Batches, Bots, Lines, LinkTracker, Messages, NumberBanks, Phonebook, Services, Sms, Verify, Voip, Wallet,
)

DEFAULT_BASE_URL = "https://api.irnoti.com"


class Transport:
    def __init__(self, api_key: str, base_url: str, timeout: float, retries: int, client: Optional[httpx.Client]):
        if not api_key:
            raise ValueError("irnoti: api_key is required")
        self._base = base_url.rstrip("/") + "/v1"
        self._retries = retries
        self._http = client or httpx.Client(timeout=timeout)
        self._headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Mapping[str, Any]] = None,
        body: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        params = {k: v for k, v in (query or {}).items() if v is not None}
        hdrs = {**self._headers, **(headers or {})}
        # Only calls that are safe to repeat are retried: GETs and sends carrying an Idempotency-Key.
        attempts = 1 + (self._retries if method == "GET" or "Idempotency-Key" in hdrs else 0)
        last: Optional[Exception] = None
        for i in range(attempts):
            try:
                res = self._http.request(
                    method, self._base + path, params=params or None, headers=hdrs,
                    json=_clean(body) if body is not None and not files else None, files=files,
                )
            except httpx.TransportError as exc:
                last = exc
                continue
            if res.status_code >= 500 and i < attempts - 1:
                continue
            return self._unwrap(res)
        assert last is not None
        raise last

    @staticmethod
    def _unwrap(res: httpx.Response) -> Any:
        try:
            data = res.json() if res.content else None
        except ValueError:
            data = None
        if res.is_success:
            return data
        msg = data.get("message") if isinstance(data, dict) else None
        if isinstance(msg, list):
            msg = " ".join(map(str, msg))
        raise IrnotiApiError(
            msg or f"irnoti API error (HTTP {res.status_code})",
            res.status_code,
            str(data.get("code", "")) if isinstance(data, dict) else "",
            data.get("details") if isinstance(data, dict) else None,
        )


def _clean(value: Any) -> Any:
    """Drop ``None`` values (optional fields are omitted) and serialise datetimes."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items() if v is not None}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class Irnoti:
    """Entry point. ``Irnoti(api_key="irn_live_…").sms.send(line_id=1, to="0912…", text="hi")``"""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
        retries: int = 1,
        http_client: Optional[httpx.Client] = None,
    ):
        self._cfg = dict(base_url=base_url, timeout=timeout, retries=retries, http_client=http_client)
        t = Transport(api_key, base_url, timeout, retries, http_client)
        self.sms = Sms(t)
        self.messages = Messages(t)
        self.batches = Batches(t)
        self.lines = Lines(t)
        self.wallet = Wallet(t)
        self.phonebook = Phonebook(t)
        self.services = Services(t)
        self.link_tracker = LinkTracker(t)
        self.number_banks = NumberBanks(t)
        self.verify = Verify(t)
        self.bots = Bots(t)
        self.voip = Voip(t)

    def with_api_key(self, api_key: str) -> "Irnoti":
        """A new independent client bound to another key (multi-tenant apps)."""
        return Irnoti(api_key, **self._cfg)  # type: ignore[arg-type]
