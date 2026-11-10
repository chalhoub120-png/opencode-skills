"""Secret redaction and sensitive-data masking.

Single source of truth for audit logging, request validation and any response
that may echo user-supplied text. Patterns target well-known credential
formats so ordinary prose (for example "token budget") is preserved.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

# Keys whose values are always secret, regardless of the value's shape.
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "password_hash",
        "secret",
        "secret_key",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "id_token",
        "authorization",
        "jwt",
        "jwt_secret",
        "private_key",
        "ssh_key",
        "client_secret",
        "vault_token",
        "otp",
        "totp",
    }
)

_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_OPENAI = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")
_AWS = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GITHUB = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")
_SLACK = re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")
_BEARER = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{12,}")
_URL_CREDENTIALS = re.compile(
    r"(?i)\b(postgres(?:ql)?(?:\+asyncpg)?|mysql|mariadb|redis|rediss|amqp|mongodb(?:\+srv)?)"
    r"://([^\s:@/]+):([^\s@/]+)@"
)
_KEY_VALUE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token)"
    r"\b\s*[:=]\s*(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)

_IPV4 = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")
_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")


def _mask_url(match: re.Match[str]) -> str:
    scheme, user = match.group(1), match.group(2)
    return f"{scheme}://{user}:{REDACTED}@"


def _mask_key_value(match: re.Match[str]) -> str:
    return f"{match.group(1)}={REDACTED}"


def redact_text(value: str) -> str:
    """Redact credential-like substrings from free text."""
    if not value:
        return value
    out = _URL_CREDENTIALS.sub(_mask_url, value)
    out = _JWT.sub(REDACTED, out)
    out = _OPENAI.sub(REDACTED, out)
    out = _AWS.sub(REDACTED, out)
    out = _GITHUB.sub(REDACTED, out)
    out = _SLACK.sub(REDACTED, out)
    out = _BEARER.sub(lambda m: f"{m.group(1)} {REDACTED}", out)
    out = _KEY_VALUE.sub(_mask_key_value, out)
    return out


def sanitize(value: Any, *, depth: int = 0, max_depth: int = 6) -> Any:
    """Recursively redact a JSON-like structure before logging or returning it."""
    if depth > max_depth:
        return "[TRUNCATED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            if name.lower() in SENSITIVE_KEYS:
                clean[name] = REDACTED
            else:
                clean[name] = sanitize(item, depth=depth + 1, max_depth=max_depth)
        return clean
    if isinstance(value, (list, tuple, set)):
        return [sanitize(item, depth=depth + 1, max_depth=max_depth) for item in value]
    return redact_text(str(value))


def mask_ip(value: str) -> str:
    """Keep the last IPv4 octet, mask the rest. IPv6 is fully masked."""
    if not value:
        return value
    ipv4 = _IPV4.fullmatch(value.strip())
    if ipv4:
        return f"***.***.***.{ipv4.group(4)}"
    if ":" in value:
        return "***"
    return value


def mask_network_details(value: str) -> str:
    """Mask IPv4 addresses, MAC addresses and host:port pairs inside text."""
    out = _IPV4.sub(lambda m: f"***.***.***.{m.group(4)}", value)
    out = _MAC.sub("**:**:**:**:**:**", out)
    return out
