"""Checks an ID token from "Sign in with Google / Apple" and says who the person is.

The provider signs the token (a JWT) with its private key and publishes the public keys at a
fixed address (JWKS). We check, in this order:
  1. the signature, with the provider's published key   -> really issued by Google / Apple
  2. iss (issuer)                                        -> by the provider we think
  3. aud (audience)                                      -> for OUR app, not someone else's
  4. exp / iat                                           -> not expired
  5. nonce                                               -> made for this very sign-in, not replayed
Only then is `sub` (the person's permanent id at that provider) trusted.

No HTTP here (see the architecture rules): errors are our own classes, the router turns them into codes.
"""
import hashlib
import hmac
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

import jwt
from jwt import PyJWKClient

from app.core.config import settings

FETCH_TIMEOUT_SECONDS = 10
KEYS_CACHE_SECONDS = 60 * 60   # providers rotate keys rarely; a new key id makes PyJWKClient fetch again
CLOCK_SKEW_SECONDS = 60        # a phone or server clock a little off must not fail every sign-in


@dataclass(frozen=True)
class Provider:
    jwks_url: str
    issuers: tuple[str, ...]
    client_ids: Callable[[], list[str]]   # read at call time, so settings changes in tests apply
    hashed_nonce: bool                    # Apple puts sha256(nonce) in the token, Google the nonce itself


PROVIDERS = {
    "google": Provider(
        jwks_url="https://www.googleapis.com/oauth2/v3/certs",
        issuers=("https://accounts.google.com", "accounts.google.com"),
        client_ids=lambda: settings.google_client_ids,
        hashed_nonce=False,
    ),
    "apple": Provider(
        jwks_url="https://appleid.apple.com/auth/keys",
        issuers=("https://appleid.apple.com",),
        client_ids=lambda: settings.apple_client_ids,
        hashed_nonce=True,
    ),
}


@dataclass(frozen=True)
class SocialIdentity:
    provider: str
    subject: str            # permanent id at the provider: the account is matched on this, never on email
    email: str | None       # Apple may give a private relay address, or none after the first sign-in
    email_verified: bool
    audience: str           # which of our app ids the token was for (Apple needs it again to revoke)


class SocialAuthError(Exception):
    """The token is not valid for us (bad signature, wrong app, expired, wrong nonce...)."""


class ProviderDisabledError(SocialAuthError):
    """This provider has no client id configured: the button is off."""


class ProviderUnavailableError(SocialAuthError):
    """The provider's keys could not be fetched (network, provider down). Not the user's fault."""


@lru_cache(maxsize=None)
def _keys(provider: str) -> PyJWKClient:
    return PyJWKClient(PROVIDERS[provider].jwks_url, cache_keys=True, lifespan=KEYS_CACHE_SECONDS, timeout=FETCH_TIMEOUT_SECONDS)


def _as_bool(value) -> bool:
    # Google sends true/false, Apple sometimes the strings "true"/"false"
    return value is True or value == "true"


def verify_id_token(provider: str, id_token: str, nonce: str) -> SocialIdentity:
    config = PROVIDERS.get(provider)
    if config is None:
        raise SocialAuthError("Unknown provider")
    client_ids = config.client_ids()
    if not client_ids:
        raise ProviderDisabledError(provider)

    try:
        signing_key = _keys(provider).get_signing_key_from_jwt(id_token)
    except jwt.PyJWKClientConnectionError as exc:
        raise ProviderUnavailableError(provider) from exc
    except (jwt.PyJWKClientError, jwt.DecodeError) as exc:
        # Not a JWT, or signed with a key the provider never published
        raise SocialAuthError("Unknown signing key") from exc

    try:
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],          # fixed: a token cannot choose a weaker algorithm (e.g. "none")
            audience=client_ids,
            issuer=list(config.issuers),
            leeway=CLOCK_SKEW_SECONDS,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        raise SocialAuthError(str(exc)) from exc

    expected_nonce = hashlib.sha256(nonce.encode()).hexdigest() if config.hashed_nonce else nonce
    # compare_digest: the same time whatever the input, so the comparison leaks nothing
    if not hmac.compare_digest(str(claims.get("nonce", "")), expected_nonce):
        raise SocialAuthError("Nonce does not match")

    email = claims.get("email")
    return SocialIdentity(
        provider=provider,
        subject=str(claims["sub"]),
        email=email.lower() if isinstance(email, str) else None,
        email_verified=_as_bool(claims.get("email_verified")),
        audience=claims["aud"] if isinstance(claims["aud"], str) else claims["aud"][0],
    )
