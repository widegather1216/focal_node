import threading
from core.ports import ImageEmbeddingPort, TextEmbeddingPort, ImageCaptioningPort

_siglip_adapter = None
_gemma_adapter = None
_factory_lock = threading.Lock()

def get_siglip_adapter() -> ImageEmbeddingPort:
    """
    Returns the singleton SigLIP 2 adapter instance implementing ImageEmbeddingPort & TextEmbeddingPort.
    """
    global _siglip_adapter
    if _siglip_adapter is None:
        with _factory_lock:
            if _siglip_adapter is None:
                from services.mlx_adapters import SigLIP2Adapter
                _siglip_adapter = SigLIP2Adapter()
    return _siglip_adapter

def get_gemma_adapter() -> ImageCaptioningPort:
    """
    Returns the singleton Gemma VLM adapter instance implementing ImageCaptioningPort.
    """
    global _gemma_adapter
    if _gemma_adapter is None:
        with _factory_lock:
            if _gemma_adapter is None:
                from services.mlx_adapters import GemmaAdapter
                _gemma_adapter = GemmaAdapter()
    return _gemma_adapter
