"""Context-preserving secret redaction for every dotf output surface."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"
_SENSITIVE_NAME = re.compile(
    r"(?:credential|authorization|proxy_authorization|cookie|set_cookie|password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)",
    re.IGNORECASE,
)
_HEADER = re.compile(
    r"(?im)\b(authorization|proxy-authorization|cookie|set-cookie)\s*:\s*[^\r\n]+"
)
_AUTH_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:authorization|proxy[_-]?authorization)\b\s*[=:]\s*)(?:\"[^\"]*\"|'[^']*'|Bearer\s+[^\s,;\]}]+|[^\s,;\]}]+)"
)
_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:credential|authorization|cookie|password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)\b\s*[=:]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;\]}]+)"
)
_OPTION = re.compile(
    r"(?i)(--(?:credential|authorization|cookie|password|passwd|secret|token|api-key|access-key|private-key|client-secret)(?:=|\s+))(?:\"[^\"]*\"|'[^']*'|\S+)"
)
_URI_USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)([^/@\s]+)@")


def _sensitive_environment(environ: Mapping[str, str] | None) -> list[str]:
    env = os.environ if environ is None else environ
    values = {
        value
        for name, value in env.items()
        if value and _SENSITIVE_NAME.search(name) and value != REDACTED
    }
    return sorted(values, key=len, reverse=True)


def sanitize_text(
    value: str,
    *,
    environ: Mapping[str, str] | None = None,
    secret_values: Sequence[str] = (),
) -> str:
    """Redact syntax-recognized secrets and actual sensitive env values."""
    if not isinstance(value, str):
        raise TypeError("sanitize_text expects str")
    result = _HEADER.sub(lambda m: f"{m.group(1)}: {REDACTED}", value)
    result = _URI_USERINFO.sub(lambda m: f"{m.group(1)}{REDACTED}@", result)
    result = _AUTH_ASSIGNMENT.sub(lambda m: f"{m.group(1)}{REDACTED}", result)
    result = _ASSIGNMENT.sub(lambda m: f"{m.group(1)}{REDACTED}", result)
    result = _OPTION.sub(lambda m: f"{m.group(1)}{REDACTED}", result)
    known = set(_sensitive_environment(environ))
    known.update(v for v in secret_values if isinstance(v, str) and v)
    for secret in sorted(known, key=len, reverse=True):
        result = result.replace(secret, REDACTED)
    return result


def sanitize(
    value: Any,
    *,
    environ: Mapping[str, str] | None = None,
    secret_values: Sequence[str] = (),
    _key_sensitive: bool = False,
) -> Any:
    """Recursively sanitize JSON-compatible data without mutating the input."""
    if _key_sensitive:
        return REDACTED
    if isinstance(value, str):
        return sanitize_text(value, environ=environ, secret_values=secret_values)
    if isinstance(value, Mapping):
        return {
            str(key): sanitize(
                item,
                environ=environ,
                secret_values=secret_values,
                _key_sensitive=bool(_SENSITIVE_NAME.search(str(key))),
            )
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(sanitize(v, environ=environ, secret_values=secret_values) for v in value)
    if isinstance(value, list):
        return [sanitize(v, environ=environ, secret_values=secret_values) for v in value]
    return value


def sanitize_for_terminal(value: Any, **kwargs: Any) -> str:
    if isinstance(value, str):
        return sanitize_text(value, **kwargs)
    return json.dumps(sanitize(value, **kwargs), ensure_ascii=False, sort_keys=True)


def sanitize_for_json(value: Any, **kwargs: Any) -> Any:
    return sanitize(value, **kwargs)


def sanitize_for_persistence(value: Any, **kwargs: Any) -> Any:
    return sanitize(value, **kwargs)


def sanitize_json(value: Any, **kwargs: Any) -> str:
    return json.dumps(sanitize(value, **kwargs), ensure_ascii=False, sort_keys=True)
