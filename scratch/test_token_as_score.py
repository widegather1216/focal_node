import os
import sys
import time

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

import torch
from services.unipercept_adapter import get_unipercept_adapter, build_transform, GPU_LOCK
from PIL import Image, ImageOps

def main():
    img_path = os.path.abspath("scratch/test_images/test_scenic.jpg")
    adapter = get_unipercept_adapter()
    adapter._load_model_locked()
    
    with Image.open(img_path) as raw_img:
        t_img = ImageOps.exif_transpose(raw_img)
        pil_img = t_img.convert("RGB") if t_img.mode != "RGB" else t_img.copy()

    target_dtype = adapter.torch_dtype
    if adapter.model is not None and hasattr(adapter.model, "parameters"):
        try:
            target_dtype = next(adapter.model.parameters()).dtype
        except Exception:
            pass

    transform = build_transform(input_size=448)
    pixel_values = transform(pil_img).unsqueeze(0).to(dtype=target_dtype).to(adapter.device)

    # Official standard prompts without complex formatting instructions
    prompts = {
        "IAA (Aesthetics)": "Please evaluate the aesthetic quality of this image.",
        "IQA (Quality)": "Please evaluate the technical quality of this image.",
        "ISTA (Structure/Texture)": "Please evaluate the structural and textural quality of this image."
    }

    vr_config = dict(max_new_tokens=15, do_sample=False, num_beams=1)

    print("=== Testing Official Native Prompts (3 Separate VR Calls) ===")
    for domain, prompt in prompts.items():
        t0 = time.time()
        with GPU_LOCK:
            out_text = adapter.model.chat(adapter.tokenizer, pixel_values, prompt, generation_config=vr_config)
        elapsed = time.time() - t0
        print(f"[{domain}] Time: {elapsed:.2f}s | Output: {repr(out_text.strip())}")

    adapter.unload_model()

if __name__ == "__main__":
    main()
