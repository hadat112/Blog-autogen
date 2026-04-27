from abc import ABC, abstractmethod

class BasePublisher(ABC):
    @abstractmethod
    def publish(self, title: str, content: str, image_source: str) -> str:
        """
        Publishes content to a platform.
        :param title: Post title.
        :param content: Post content (HTML or plain text).
        :param image_source: Local path or URL to an image.
        :return: Link to the published post.
        """
        pass
