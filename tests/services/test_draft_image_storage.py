import asyncio
from io import BytesIO

import pytest
from starlette.datastructures import Headers, UploadFile


@pytest.mark.parametrize('body,mime,valid', [
    (b'\xff\xd8\xffimage', 'image/jpeg', True),
    (b'wrong', 'image/jpeg', False),
    (b'', 'image/png', False),
    (b'wrong', 'text/plain', False),
])
def test_image_validation_and_cleanup(tmp_path, monkeypatch, body, mime, valid):
    from app.services.draft_image_storage import store_draft_image
    monkeypatch.chdir(tmp_path)
    image = UploadFile(BytesIO(body), headers=Headers({'content-type': mime}))
    if valid:
        from pathlib import Path
        path = asyncio.run(store_draft_image(image))
        assert Path(path).read_bytes() == body
    else:
        with pytest.raises(ValueError):
            asyncio.run(store_draft_image(image))
        assert list(tmp_path.rglob('*.jpg')) == []
        assert list(tmp_path.rglob('*.png')) == []


def test_oversized_image_removes_partial_file(tmp_path, monkeypatch):
    import app.services.draft_image_storage as storage
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(storage, 'MAX_IMAGE_BYTES', 3)
    image = UploadFile(BytesIO(b'\xff\xd8\xfftoo-long'), headers=Headers({'content-type': 'image/jpeg'}))
    with pytest.raises(ValueError, match='limit'):
        asyncio.run(storage.store_draft_image(image))
    assert list(tmp_path.rglob('*.jpg')) == []
