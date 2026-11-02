from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings

class FileTooLargeError(Exception):
    pass

class UnsupportedFileTypeError(Exception):
    pass

FILE_SIGNATURES = {
    b"%PDF": ".pdf",
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
}

def detect_extension(content:bytes) -> str |None:
    for signature,extension in FILE_SIGNATURES.items():
        if content.startswith(signature):
            return extension
    return None

def save_upload(file:UploadFile,user_id:int) -> str:
    max_bytes=settings.max_upload_size_mb*1024*1024
    content=file.file.read(max_bytes+1)

    if len(content)> max_bytes:
        raise FileTooLargeError
    extension=detect_extension(content)
    if extension is None:
        raise UnsupportedFileTypeError

    user_dir=Path(settings.upload_dir)/ str(user_id)
    user_dir.mkdir(parents=True,exist_ok=True)

    file_path=user_dir / f"{uuid4().hex}{extension}"
    file_path.write_bytes(content)

    return file_path.as_posix()

def delete_file(path:str) -> None:
    Path(path).unlink(missing_ok=True)