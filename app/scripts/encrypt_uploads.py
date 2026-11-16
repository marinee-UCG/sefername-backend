"""Encrypt the uploaded files that are still stored in plain form, and re-encrypt files
that only an old key can open (after DATA_ENCRYPTION_KEY was changed).

Run from the backend folder:
    python -m app.scripts.encrypt_uploads           # only reports what it would do
    python -m app.scripts.encrypt_uploads --apply   # does it

Safe to run again: files already encrypted with the current key are left alone.
Before --apply, make sure DATA_ENCRYPTION_KEY is saved somewhere safe: without it the files are gone.
Fields in the database have their own script: app/scripts/seal_fields.py
"""
import os
import sys
from pathlib import Path

from app.core.config import settings
from app.core.crypto import FILE_MAGIC, DecryptError, decrypt_bytes, encrypt_bytes, is_encrypted_file, opens_with_current_key
from app.core.storage import FILE_SIGNATURES


def write_atomically(path: Path, data: bytes) -> None:
    # Written next to the file, then swapped in: a crash halfway never leaves a half-written scan
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(data)
    os.replace(temp, path)


def main(apply: bool) -> None:
    root = Path(settings.upload_dir)
    counts = {"encrypted": 0, "re-encrypted": 0, "already done": 0, "skipped": 0, "unreadable": 0}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix == ".tmp":
            continue
        # uploads/<user_id>/<uuid>.<ext>: the folder says whose file it is
        if not path.parent.name.isdigit():
            print(f"skipped (not in a user folder): {path}")
            counts["skipped"] += 1
            continue
        user_id = int(path.parent.name)
        blob = path.read_bytes()
        if is_encrypted_file(blob):
            if opens_with_current_key(blob[len(FILE_MAGIC):], user_id):
                counts["already done"] += 1
                continue
            try:
                plain = decrypt_bytes(blob, user_id)   # an old key opens it
            except DecryptError:
                print(f"UNREADABLE with every key: {path}")
                counts["unreadable"] += 1
                continue
            action = "re-encrypted"
        elif any(blob.startswith(signature) for signature in FILE_SIGNATURES):
            plain = blob
            action = "encrypted"
        else:
            print(f"skipped (not PDF/JPG/PNG): {path}")
            counts["skipped"] += 1
            continue
        if apply:
            write_atomically(path, encrypt_bytes(plain, user_id))
        counts[action] += 1
    print(("Done: " if apply else "Dry run (nothing changed, add --apply): ") + ", ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
