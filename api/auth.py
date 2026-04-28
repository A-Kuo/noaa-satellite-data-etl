"""API key authentication via X-API-Key header."""

from __future__ import annotations

import os

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_VALID_KEYS: set[str] = set(
    filter(None, os.getenv("API_KEYS", "").split(","))
)


def require_api_key(key: str | None = Security(_API_KEY_HEADER)) -> str:
    """Dependency: validate the X-API-Key header.

    Set API_KEYS env var to a comma-separated list of valid keys.
    If API_KEYS is empty, auth is disabled (dev/test mode).
    """
    if not _VALID_KEYS:
        return "dev"
    if not key or key not in _VALID_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return key
