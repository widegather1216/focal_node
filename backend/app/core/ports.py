from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ImageEmbeddingPort(ABC):
    @abstractmethod
    def get_image_embedding(self, image_path: str) -> List[float]:
        """
        Extracts a high-dimensional vector embedding from the given image path.
        """
        pass

class TextEmbeddingPort(ABC):
    @abstractmethod
    def get_text_embedding(self, text: str) -> List[float]:
        """
        Extracts a high-dimensional vector embedding from the given text.
        """
        pass

class ImageCaptioningPort(ABC):
    @abstractmethod
    def generate_caption_and_tags(self, image_path: str) -> Dict[str, Any]:
        """
        Generates an natural language caption and a list of key tags for the image.
        Returns a dict of {"caption": str, "tags": list[str]}.
        """
        pass
