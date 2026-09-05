from abc import ABC, abstractmethod

class BaseAI(ABC):
    @abstractmethod
    def generate_story(self, prompt: str) -> dict:
        """
        Generates a story based on the prompt.
        Returns a dictionary with: title, content, caption, image_prompt.
        """
        pass

    @abstractmethod
    def generate_image(self, image_prompt: str) -> str:
        """
        Generates an image based on the prompt.
        Returns the image URL.
        """
        pass
