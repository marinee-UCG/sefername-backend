"""Security events, one JSON line each on stdout (Docker keeps them: `docker compose logs api`).

What gets written: sign-ins (ok / failed / blocked), sign-ups, a stolen refresh token coming back,
password changes, account deletions, passport-read limits. Enough to answer "was someone trying
to get into this account, from where, when?".

What never gets written: passwords, tokens, document numbers, and email addresses in plain form.
An email is logged as a keyed hash: the same address always gives the same tag (so attempts on one
account can be followed), but the tag cannot be turned back into the address without SECRET_KEY.
"""
import hashlib
import hmac
import json
import logging
import sys
from datetime import datetime, timezone

from fastapi import Request

from app.core.config import settings

logger = logging.getLogger("sefername.security")
if not logger.handlers:
    # Own handler: uvicorn sets up only its own loggers, so ours would otherwise print nothing
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def email_tag(email: str) -> str:
    digest = hmac.new(settings.secret_key.encode(), email.lower().encode(), hashlib.sha256).hexdigest()
    return digest[:16]


def security_event(
    event: str,
    request: Request | None = None,
    user_id: int | None = None,
    email: str | None = None,
    **details,
) -> None:
    record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "type": "security", "event": event}
    if request is not None and request.client is not None:
        record["ip"] = request.client.host
    if user_id is not None:
        record["user_id"] = user_id
    if email is not None:
        record["email_tag"] = email_tag(email)
    record.update(details)
    logger.info(json.dumps(record, ensure_ascii=False))
