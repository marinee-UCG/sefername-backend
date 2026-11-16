from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.crypto import DecryptError, decrypt_bytes, encrypt_bytes

class FileTooLargeError(Exception):
    pass

class UnsupportedFileTypeError(Exception):
    pass
class StorageQuotaError(Exception):
    pass

# Same error, older name kept for the routers
FileDecryptError = DecryptError



FILE_SIGNATURES = {
    b"%PDF": ".pdf",
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
}


def read_upload(path: str, user_id: int) -> bytes:
    """The original file content, decrypted. FileNotFoundError if it is not on disk.
    `user_id` is the owner: a file opens only as its owner's (see core/crypto.py)."""
    return decrypt_bytes(Path(path).read_bytes(), user_id)


def detect_extension(content:bytes) -> str |None:
    for signature,extension in FILE_SIGNATURES.items():
        if content.startswith(signature):
            return extension
    return None

def used_bytes(user_dir:Path) -> int:
    if not user_dir.exists():
        return 0
    total=0
    for f in user_dir.iterdir():
        if not f.is_file():
            continue
        total += f.stat().st_size
    return total


def save_upload(file:UploadFile,user_id:int) -> str:
    max_bytes=settings.max_upload_size_mb*1024*1024
    content=file.file.read(max_bytes+1)

    if len(content)> max_bytes:
        raise FileTooLargeError
    extension=detect_extension(content)
    if extension is None:
        raise UnsupportedFileTypeError

    user_dir=Path(settings.upload_dir)/ str(user_id)
    limit=settings.user_storage_limit_mb*1024*1024
    if used_bytes(user_dir)+len(content)> limit:
        raise StorageQuotaError

    user_dir.mkdir(parents=True,exist_ok=True)

    # The extension stays in the name (it tells the download its type); the bytes are encrypted
    file_path=user_dir / f"{uuid4().hex}{extension}"
    file_path.write_bytes(encrypt_bytes(content, user_id))

    return file_path.as_posix()

def delete_file(path:str) -> None:
    Path(path).unlink(missing_ok=True)
