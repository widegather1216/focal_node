import os
import sys
import time
import torch
from PIL import Image

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

from services.unipercept_adapter import get_unipercept_adapter, build_transform

print("1. Loading adapter...", flush=True)
adapter = get_unipercept_adapter()
adapter._load_model_locked()

img_path = "/Users/kimbeomjun/Desktop/photo/jpeg/_DSC0561_edit.jpg"
with Image.open(img_path) as raw:
    pil_img = raw.convert("RGB")

print("2. Preparing transform...", flush=True)
transform = build_transform(input_size=448)
target_dtype = adapter.torch_dtype
pixel_values = transform(pil_img).unsqueeze(0).to(dtype=target_dtype).to(adapter.device)

print(f"3. Running model.chat on {adapter.device} with dtype={target_dtype}...", flush=True)
prompt = "Write a brief 2-sentence aesthetic analysis of this photo."
t0 = time.time()
gen_config = dict(max_new_tokens=60, do_sample=False, num_beams=1)

res = adapter.model.chat(
    adapter.tokenizer,
    pixel_values,
    prompt,
    generation_config=gen_config
)
t1 = time.time()
print(f"✅ Success in {t1 - t0:.2f}s:\n{res}", flush=True)
