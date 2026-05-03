from unittest.mock import patch, MagicMock
import pytest

from publishers.facebook_page import FacebookPagePublisher


def test_publish_photo_caption_success():
    pub = FacebookPagePublisher("123", "token", "v23.0")

    with patch("publishers.facebook_page.requests.post") as mock_post:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"post_id": "123_456", "id": "456"}
        mock_post.return_value = resp

        post_id = pub.publish_photo_caption("Caption", "https://img.test/a.png")

        assert post_id == "123_456"


def test_publish_text_success():
    pub = FacebookPagePublisher("123", "token", "v23.0")

    with patch("publishers.facebook_page.requests.post") as mock_post:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"id": "123_789"}
        mock_post.return_value = resp

        post_id = pub.publish_text("Only caption")
        assert post_id == "123_789"


def test_comment_on_post_success():
    pub = FacebookPagePublisher("123", "token")

    with patch("publishers.facebook_page.requests.post") as mock_post:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"id": "987654"}
        mock_post.return_value = resp

        comment_id = pub.comment_on_post("123_456", "https://wp.url/post")
        assert comment_id == "987654"


def test_publish_photo_caption_http_error_raises():
    pub = FacebookPagePublisher("123", "token")

    with patch("publishers.facebook_page.requests.post") as mock_post:
        resp = MagicMock()
        resp.status_code = 400
        resp.text = "bad request"
        resp.json.return_value = {"error": {"message": "bad request"}}
        mock_post.return_value = resp

        with pytest.raises(Exception) as exc:
            pub.publish_photo_caption("Caption", "https://img.test/a.png")

        assert "Facebook API error" in str(exc.value)
