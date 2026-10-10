from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from typing import Any, Union

_SIG = re.compile(r"^t=(\d+),v1=([0-9a-f]{64})$")


def verify_webhook(raw_body: Union[str, bytes], signature_header: str, secret: str, tolerance: int = 300) -> bool:
    """Check ``X-Irnoti-Signature`` (``t=<unix>,v1=<hex>``): HMAC-SHA256 of ``"<t>.<raw body>"`` with your ``whsec_`` key.

    Pass the RAW request body, not re-serialised JSON.
    """
    m = _SIG.match(signature_header or "")
    if not m:
        return False
    if abs(time.time() - int(m.group(1))) > tolerance:
        return False
    body = raw_body.encode() if isinstance(raw_body, str) else raw_body
    expected = hmac.new(secret.encode(), m.group(1).encode() + b"." + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, m.group(2))


def parse_webhook(raw_body: Union[str, bytes], signature_header: str, secret: str, tolerance: int = 300) -> dict[str, Any]:
    """Verify and decode; raises ``ValueError`` on a bad signature."""
    if not verify_webhook(raw_body, signature_header, secret, tolerance):
        raise ValueError("Invalid irnoti webhook signature")
    return json.loads(raw_body)
