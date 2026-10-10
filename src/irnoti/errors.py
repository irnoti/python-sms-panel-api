from __future__ import annotations

from typing import Any


class IrnotiError(Exception):
    """Base class for all SDK errors."""


class IrnotiApiError(IrnotiError):
    """Non-2xx answer. ``code`` is the API's machine-readable code ('' for plain 401/403/404)."""

    def __init__(self, message: str, status: int, code: str = "", details: Any = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.details = details

    @property
    def is_validation_error(self) -> bool:
        return self.code in ("validation_error", "invalid_recipients", "missing_params")

    @property
    def is_invalid_recipients(self) -> bool:
        return self.code == "invalid_recipients"

    @property
    def is_insufficient_balance(self) -> bool:
        return self.status == 402 or self.code == "insufficient_balance"

    @property
    def is_no_price(self) -> bool:
        return self.code == "no_price"

    @property
    def is_rate_limited(self) -> bool:
        return self.status == 429

    @property
    def is_unauthenticated(self) -> bool:
        return self.status == 401

    @property
    def is_forbidden(self) -> bool:
        return self.status == 403

    @property
    def is_not_found(self) -> bool:
        return self.status == 404

    @property
    def is_conflict(self) -> bool:
        return self.status == 409

    @property
    def is_server_error(self) -> bool:
        return self.status >= 500

    def __repr__(self) -> str:
        return f"IrnotiApiError(status={self.status}, code={self.code!r}, message={self.message!r})"
