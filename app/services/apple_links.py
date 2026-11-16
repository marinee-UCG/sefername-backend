"""Keeping and revoking the Apple refresh token of a "Sign in with Apple" link.

Both are best effort: if Apple cannot be reached, the user still signs in / still gets their account
deleted, and the failure goes to the security log (core/audit.py) so it can be retried by hand.
Blocking a deletion because Apple is down would break a stronger rule: the user's right to erase.
"""
from app.core.audit import security_event
from app.core.config import settings
from app.core.crypto import DecryptError, open_sealed, seal
from app.models.user_identity import UserIdentity
from app.services import apple


def store_refresh_token(link: UserIdentity, authorization_code: str | None) -> None:
    """Swaps Apple's one-time code for the link's refresh token and keeps it sealed. The caller commits."""
    if link.provider != "apple" or not authorization_code or not apple.is_configured():
        return
    client_id = link.client_id or settings.apple_client_ids[0]
    try:
        token = apple.exchange_code(authorization_code, client_id)
    except apple.AppleError as exc:
        security_event("apple_code_exchange_failed", user_id=link.user_id, reason=str(exc)[:200])
        return
    link.provider_refresh_token = seal(token, link.user_id)


def revoke(link: UserIdentity) -> None:
    """Tells Apple this link is gone (account deleted or Apple disconnected)."""
    if link.provider != "apple" or link.provider_refresh_token is None:
        return
    if not apple.is_configured():
        security_event("apple_revoke_skipped", user_id=link.user_id, reason="Apple keys not configured")
        return
    try:
        token = open_sealed(link.provider_refresh_token, link.user_id)
        apple.revoke(token, link.client_id or settings.apple_client_ids[0])
    except (apple.AppleError, DecryptError) as exc:
        security_event("apple_revoke_failed", user_id=link.user_id, reason=str(exc)[:200])
        return
    security_event("apple_link_revoked", user_id=link.user_id)
