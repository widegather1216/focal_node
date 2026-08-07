import os
import sys
import json
import time
import math
import gc

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

from services.unipercept_adapter import get_unipercept_adapter

def free_memory():
    gc.collect()
    try:
        import torch
        if hasattr(torch, "mps") and torch.mps.is_available():
            torch.mps.empty_cache()
    except Exception:
        pass

def calc_stats(numbers):
    valid = [n for n in numbers if n is not None]
    if not valid:
        return {"mean": None, "std": None, "min": None, "max": None, "range": None}
    mean = sum(valid) / len(valid)
    variance = sum((x - mean) ** 2 for x in valid) / len(valid)
    std = math.sqrt(variance)
    mn = min(valid)
    mx = max(valid)
    rng = mx - mn
    return {
        "mean": round(mean, 2),
        "std": round(std, 2),
        "min": mn,
        "max": mx,
        "range": rng
    }

test_dir = os.path.abspath("scratch/test_images/recent_5")
files = ['_DSC2126_edit.jpg', '_DSC2250_edit.jpg', '_DSC1924_edit.jpg', '_DSC2081_edit.jpg', '_DSC2073_edit.jpg']
num_trials = 5
output_json = "scratch/vr_consistency_test_results.json"

uni = get_unipercept_adapter()

all_photo_results = []

for idx, fn in enumerate(files, 1):
    full_path = os.path.join(test_dir, fn)
    print(f"\n================ [{idx}/{len(files)}] VR Consistency Testing on {fn} ================", flush=True)
    if not os.path.exists(full_path):
        print(f"File not found: {full_path}")
        continue

    trials_data = []
    iaa_list = []
    iqa_list = []
    ista_list = []
    overall_list = []

    for trial in range(1, num_trials + 1):
        t0 = time.time()
        scores = uni.generate_vr_scores(full_path)
        elapsed = time.time() - t0

        ov = scores.get("overall")
        iaa = scores.get("iaa")
        iqa = scores.get("iqa")
        ista = scores.get("ista")

        iaa_list.append(iaa)
        iqa_list.append(iqa)
        ista_list.append(ista)
        overall_list.append(ov)

        print(f"  [Trial {trial}/{num_trials}] Scores -> Overall: {ov}, IAA: {iaa}, IQA: {iqa}, ISTA: {ista} (Latency: {elapsed:.2f}s)")
        trials_data.append({
            "trial": trial,
            "scores": scores,
            "latency_sec": round(elapsed, 2)
        })

        free_memory()

    stats = {
        "overall": calc_stats(overall_list),
        "iaa": calc_stats(iaa_list),
        "iqa": calc_stats(iqa_list),
        "ista": calc_stats(ista_list)
    }

    photo_summary = {
        "file_name": fn,
        "trials": trials_data,
        "stats": stats
    }
    all_photo_results.append(photo_summary)

    # Save incremental progress
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_photo_results, f, ensure_ascii=False, indent=2)

uni.unload_model()
free_memory()

print(f"\nCompleted VR consistency testing on {len(files)} photos ({num_trials} trials each). Results saved to {output_json}")
