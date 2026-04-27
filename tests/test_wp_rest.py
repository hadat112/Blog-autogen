import pytest
from publishers.wp_rest import WordPressPublisher

def test_wp_publisher_init():
    wp = WordPressPublisher("https://example.com", "user", "pass")
    assert wp.url == "https://example.com"
    assert wp.username == "user"
    assert wp.app_password == "pass"
