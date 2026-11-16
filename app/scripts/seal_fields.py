"""Seal (encrypt) the sensitive fields still stored in plain form, and re-seal values that only an
old key can open (after DATA_ENCRYPTION_KEY was changed).

Fields: identity documents (document_number, issuing_country, extracted_data),
        certificates (cert_number, issuing_inst).

Run from the backend folder:
    python -m app.scripts.seal_fields           # only reports what it would do
    python -m app.scripts.seal_fields --apply   # does it, in one transaction

Safe to run again: values already sealed with the current key are left alone.
Take a database backup first, and keep DATA_ENCRYPTION_KEY somewhere safe.
"""
import base64
import sys

from sqlalchemy import select

import app.main  # noqa: F401  (loads every model, so relationships resolve)
from app.core.crypto import FIELD_PREFIX, DecryptError, is_sealed, open_sealed, opens_with_current_key, seal
from app.database import SessionLocal
from app.models.certificate import Certificate
from app.models.identity_document import IdentityDocument

TABLES = [
    (IdentityDocument, ("document_number", "issuing_country", "extracted_data")),
    (Certificate, ("cert_number", "issuing_inst")),
]


def main(apply: bool) -> None:
    counts = {"sealed": 0, "re-sealed": 0, "already done": 0, "unreadable": 0}
    db = SessionLocal()
    try:
        for model, fields in TABLES:
            for row in db.scalars(select(model)).all():
                for field in fields:
                    value = getattr(row, field)
                    if value is None:
                        continue
                    if is_sealed(value):
                        raw = base64.b64decode(value[len(FIELD_PREFIX):])
                        if opens_with_current_key(raw, row.user_id):
                            counts["already done"] += 1
                            continue
                        try:
                            plain = open_sealed(value, row.user_id)   # an old key opens it
                        except DecryptError:
                            print(f"UNREADABLE with every key: {model.__tablename__} id={row.id} {field}")
                            counts["unreadable"] += 1
                            continue
                        action = "re-sealed"
                    else:
                        # Plain text from before encryption; extracted_data is already JSON text, sealed as it is
                        plain = value
                        action = "sealed"
                    if apply:
                        setattr(row, field, seal(plain, row.user_id))
                    counts[action] += 1
        if apply:
            db.commit()   # all or nothing: a failure halfway leaves every value as it was
    finally:
        db.close()
    print(("Done: " if apply else "Dry run (nothing changed, add --apply): ") + ", ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
