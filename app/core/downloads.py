"""Sends an uploaded file back to its owner: decrypted, as a download, never cached."""
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException, Response, status

from app.core.storage import FileDecryptError, read_upload

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".png": "image/png",
}


def file_download(path: str, filename: str, user_id: int) -> Response:
    """`filename` is what the user's device saves it as; the stored name stays a random UUID."""
    try:
        content = read_upload(path, user_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    except FileDecryptError:
        # Wrong DATA_ENCRYPTION_KEY on the server or a damaged file: a server problem, not the user's
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The file could not be opened. Please try again later.",
        )
    suffix = Path(path).suffix
    return Response(
        content=content,
        media_type=MEDIA_TYPES.get(suffix, "application/octet-stream"),
        headers={
            # filename* carries any character safely; the plain one is the fallback for old clients
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}",
            # Passport scans must not stay in a browser or proxy cache, or in the phone's URL cache
            "Cache-Control": "no-store",
        },
    )
