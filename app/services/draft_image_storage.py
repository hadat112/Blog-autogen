"""Validation and storage shared by both Publisher input modes."""
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.integrations.wordpress.destination import ALLOWED_IMAGE_MIME, MAX_IMAGE_BYTES, validate_image_signature


async def store_draft_image(image: UploadFile) -> str:
    if image.content_type not in ALLOWED_IMAGE_MIME:
        raise ValueError('Image must be JPEG, PNG, WebP, or GIF')
    suffix = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif'}[image.content_type]
    directory = Path('var/uploads')
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f'{uuid4()}{suffix}'
    size, header = 0, b''
    try:
        with target.open('wb') as handle:
            while chunk := await image.read(64 * 1024):
                size += len(chunk)
                header = (header + chunk)[:16]
                if size > MAX_IMAGE_BYTES:
                    raise ValueError('Image exceeds the 10 MiB limit')
                handle.write(chunk)
        validate_image_signature(header, image.content_type)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return str(target)
