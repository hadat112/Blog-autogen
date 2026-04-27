from publishers.base_pub import BasePublisher

class WordPressPublisher(BasePublisher):
    def __init__(self, url: str, username: str, app_password: str):
        self.url = url.rstrip('/')
        self.username = username
        self.app_password = app_password

    def publish(self, title: str, content: str, image_source: str) -> str:
        # To be implemented
        pass
