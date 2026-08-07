import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

from services.unipercept_adapter import get_unipercept_adapter
from services.ai_factory import get_gemma_adapter

test_images = [
    ("test_scenic.jpg", os.path.abspath("scratch/test_images/test_scenic.jpg"), {
        "camera_model": "NIKON Z50_2",
        "lens_model": "NIKKOR Z DX 16-50mm f/3.5-6.3 VR",
        "f_number": 6.3,
        "shutter_speed": "1/250",
        "iso": 100
    }),
    ("test_noisy.jpg", os.path.abspath("scratch/test_images/test_noisy.jpg"), {
        "camera_model": "NIKON Z50_2",
        "lens_model": "NIKKOR Z DX 16-50mm f/3.5-6.3 VR",
        "f_number": 4.5,
        "shutter_speed": "1/30",
        "iso": 6400
    })
]

results = []
adapter = get_unipercept_adapter()

for file_name, file_path, meta in test_images:
    print(f"\n================ Running on {file_name} ================")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        continue
    
    # 1. Raw 6-Way UniPercept
    t0 = time.time()
    uni_res = adapter.generate_full_ensemble_critique(file_path, metadata=meta)
    uni_time = time.time() - t0
    
    raw_en = uni_res["critique"]
    scores = uni_res["scores"]
    print(f"UniPercept completed in {uni_time:.2f}s with scores: {scores}")
    
    # 2. Gemma Translation
    t1 = time.time()
    gemma = get_gemma_adapter()
    ko_critique = gemma.translate_and_format_critique(raw_en, scores, scores.get("overall"))
    gemma_time = time.time() - t1
    print(f"Gemma translation completed in {gemma_time:.2f}s")
    
    results.append({
        "file_name": file_name,
        "metadata": meta,
        "scores": scores,
        "raw_en_critique": raw_en,
        "ko_translated_critique": ko_critique,
        "timings": {"unipercept": uni_time, "gemma": gemma_time}
    })

adapter.unload_model()

with open("scratch/raw_vs_translated_pair.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\nSaved raw vs translated pairs to scratch/raw_vs_translated_pair.json")
