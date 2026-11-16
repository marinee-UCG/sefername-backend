"""Talking to Apple's server for "Sign in with Apple" links (App Store rule 5.1.1(v)):
when an account is deleted, its link to Apple must be revoked at Apple too.

How it works:
  1. At sign-in Apple also gives a one-time `authorization_code`.
  2. exchange_code() swaps it at Apple for a refresh token, which we store sealed (core/crypto.py).
  3. revoke() hands that token back to Apple when the account is deleted or Apple is disconnected.
Every call proves who we are with a "client secret": a short JWT signed with our private key from
developer.apple.com (ES256), not a fixed password.

No HTTP framework here: errors are AppleError, callers decide what to do (revoking is best effort).
"""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import jwt

from app.core.config import settings

APPLE_BASE = "https://appleid.apple.com"
TOKEN_URL = f"{APPLE_BASE}/auth/token"
REVOKE_URL = f"{APPLE_BASE}/auth/revoke"
FETCH_TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 64 * 1024
CLIENT_SECRET_SECONDS = 5 * 60   # Apple allows up to 6 months; ours is made per call, so minutes are enough


class AppleError(Exception):
    """Apple could not be reached, or refused the request."""


def is_configured() -> bool:
    return bool(settings.apple_team_id and settings.apple_key_id and settings.apple_private_key)


def _private_key() -> str:
    # .env files keep one value per line, so the key's line breaks may arrive written as "\n"
    return settings.apple_private_key.replace("\\n", "\n")


def client_secret(client_id: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {"iss": settings.apple_team_id, "iat": now, "exp": now + CLIENT_SECRET_SECONDS, "aud": APPLE_BASE, "sub": client_id},
        _private_key(),
        algorithm="ES256",
        headers={"kid": settings.apple_key_id},
    )


def _post(url: str, fields: dict) -> bytes:
    request = Request(
        url,
        data=urlencode(fields).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Sefername/1.0"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            return response.read(MAX_RESPONSE_BYTES)
    except HTTPError as exc:
        # Apple's answer says why ("invalid_grant": code used or expired...); no secrets in it
        raise AppleError(f"Apple answered {exc.code}: {exc.read(512).decode(errors='replace')}") from exc
    except (URLError, TimeoutError) as exc:
        raise AppleError(f"Apple could not be reached: {exc}") from exc


def exchange_code(code: str, client_id: str) -> str:
    """The one-time sign-in code -> Apple's refresh token for this link."""
    body = _post(TOKEN_URL, {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret(client_id),
    })
    try:
        token = json.loads(body)["refresh_token"]
    except (ValueError, KeyError) as exc:
        raise AppleError("Apple's answer had no refresh token") from exc
    return token


def revoke(refresh_token: str, client_id: str) -> None:
    _post(REVOKE_URL, {
        "client_id": client_id,
        "client_secret": client_secret(client_id),
        "token": refresh_token,
        "token_type_hint": "refresh_token",
    })
