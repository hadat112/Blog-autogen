import pytest

from app.integrations.wordpress.destination import WordPressDestinationGateway, detect_image_mime, validate_image_signature


@pytest.mark.parametrize(("header", "expected"), [
    (b"\xff\xd8\xffabc", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\nabc", "image/png"),
    (b"GIF89aabc", "image/gif"),
    (b"RIFF1234WEBPabc", "image/webp"),
])
def test_detect_image_signatures(header, expected):
    assert detect_image_mime(header) == expected


def test_rejects_spoofed_image_mime():
    with pytest.raises(ValueError, match="does not match"):
        validate_image_signature(b"not an image", "image/png")
    with pytest.raises(ValueError, match="does not match"):
        validate_image_signature(b"\xff\xd8\xffabc", "image/png")


def test_remote_image_rejects_embedded_credentials_before_request():
    gateway = WordPressDestinationGateway({"url": "https://wp.test"})
    with pytest.raises(ValueError, match="credentials"):
        gateway.upload_remote("https://user:pass@images.test/a.png")
