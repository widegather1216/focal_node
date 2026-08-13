"""
UniPercept Helper Utilities Module

Contains official UniPercept score token mapping, ImageNet transforms,
and PreTrainedModel monkey-patching.
"""

import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode
from transformers import PreTrainedModel

# Monkeypatch transformers PreTrainedModel all_tied_weights_keys property with setter
if not hasattr(PreTrainedModel, "all_tied_weights_keys"):
    def get_tied(self):
        return getattr(self, "_all_tied_weights_keys_dict", {})
    def set_tied(self, val):
        if isinstance(val, dict):
            self._all_tied_weights_keys_dict = val
        elif isinstance(val, (list, tuple, set)):
            self._all_tied_weights_keys_dict = {k: k for k in val}
        else:
            self._all_tied_weights_keys_dict = {}
    PreTrainedModel.all_tied_weights_keys = property(get_tied, set_tied)

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

def build_transform(input_size=448):
    """
    Builds standard ImageNet normalization transform for UniPercept vision model.
    """
    return T.Compose([
        T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
    ])

def score2aestoken(n: int) -> str:
    """Official UniPercept token mapping for continuous score prediction."""
    if not (0 <= n <= 100):
        raise ValueError("Score must be between 0 and 100 inclusive.")
    if 0 <= n <= 25:
        first = 'a'
        offset = n
    elif 26 <= n <= 50:
        first = 'c'
        offset = n - 26
    elif 51 <= n <= 75:
        first = 'd'
        offset = n - 51
    else:
        first = 'e'
        offset = n - 76
    second = chr(ord('a') + offset)
    return first + second

AESTHETICS_TOKEN_LIST = [score2aestoken(i) for i in range(101)]
