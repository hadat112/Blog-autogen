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


def test_post_rejection_preserves_status_and_sanitized_wordpress_details():
    import requests
    import responses
    gateway = WordPressDestinationGateway({'url': 'https://wp.test', 'username': 'alice', 'password': 'secret-password'})
    with responses.RequestsMock() as mocked:
        mocked.add(responses.POST, 'https://wp.test/wp-json/wp/v2/posts', status=403,
                   json={'code': 'rest_cannot_create', 'message': 'Not allowed Bearer fake-token secret-password'})
        with pytest.raises(requests.HTTPError) as error:
            gateway.create_post('Title', 'Body')
    assert error.value.response.status_code == 403
    assert 'rest_cannot_create' in str(error.value)
    assert 'Not allowed' in str(error.value)
    assert 'fake-token' not in str(error.value)
    assert 'secret-password' not in str(error.value)


def test_post_rejection_redacts_basic_authorization_credentials():
    import base64
    import requests
    import responses
    encoded = base64.b64encode(b'alice:secret-password').decode()
    gateway = WordPressDestinationGateway({'url': 'https://wp.test', 'username': 'alice', 'password': 'secret-password'})
    with responses.RequestsMock() as mocked:
        mocked.add(responses.POST, 'https://wp.test/wp-json/wp/v2/posts', status=403,
                   json={'code': 'forbidden', 'message': f'Authorization: Basic {encoded}; credential={encoded}'})
        with pytest.raises(requests.HTTPError) as error:
            gateway.create_post('Title', 'Body')
    assert encoded not in str(error.value)
    assert 'forbidden' in str(error.value)
