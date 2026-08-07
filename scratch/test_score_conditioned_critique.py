import os
import sys
import json
import time
import gc

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

def free_system_memory():
    gc.collect()
    try:
        import torch
        if hasattr(torch, "mps") and torch.mps.is_available():
            torch.mps.empty_cache()
    except Exception:
        pass
    try:
        import mlx.core as mx
        mx.clear_cache()
    except Exception:
        pass
    print("[MemoryCleanup] System garbage collected & Metal/MPS GPU caches cleared.", flush=True)

test_dir = os.path.abspath("scratch/test_images/recent_5")
files = ['_DSC2126_edit.jpg', '_DSC2250_edit.jpg', '_DSC1924_edit.jpg', '_DSC2081_edit.jpg', '_DSC2073_edit.jpg']
output_json = "scratch/score_conditioned_test_results.json"

results = []

# Load existing progress if any
if os.path.exists(output_json):
    try:
        with open(output_json, "r", encoding="utf-8") as f:
            results = json.load(f)
            processed = [r["file_name"] for r in results]
            print(f"Loaded existing results for: {processed}")
    except Exception:
        results = []

for idx, fn in enumerate(files, 1):
    # Check if already processed
    if any(r["file_name"] == fn for r in results):
        print(f"[{idx}/{len(files)}] Skipping already processed photo: {fn}")
        continue

    full_path = os.path.join(test_dir, fn)
    print(f"\n================ [{idx}/{len(files)}] Processing {fn} ================")
    if not os.path.exists(full_path):
        print(f"File not found: {full_path}")
        continue

    # --- PHASE 1: UniPercept Inferences (VR Scores & VQA Critiques) ---
    print(f"\n--- Phase 1: UniPercept (VR + VQA A + VQA B) ---", flush=True)
    from services.unipercept_adapter import get_unipercept_adapter
    uni = get_unipercept_adapter()

    # 1. VR Mode Scores
    scores = uni.generate_vr_scores(full_path)
    print(f"[{fn}] VR Scores: Overall={scores['overall']}, IAA={scores['iaa']}, IQA={scores['iqa']}, ISTA={scores['ista']}")

    # 2. Variant A (Current VQA)
    t0 = time.time()
    vqa_a_res = uni.generate_vqa_critiques_3way(full_path)
    raw_en_a = (
        f"[Aesthetics & Composition]\n{vqa_a_res.get('iaa', '')}\n\n"
        f"[Technical Quality & Clarity]\n{vqa_a_res.get('iqa', '')}\n\n"
        f"[Structure & Textural Details]\n{vqa_a_res.get('ista', '')}"
    )
    time_a = time.time() - t0
    print(f"[{fn}] UniPercept Variant A finished in {time_a:.2f}s")

    # 3. Variant B (Score-Conditioned VQA)
    t1 = time.time()
    ov = scores.get('overall')
    iaa = scores.get('iaa')
    iqa = scores.get('iqa')
    ista = scores.get('ista')

    score_ctx = (
        f"[Target Perceptual Metric Scores]\n"
        f"- Overall Photo Rating: {ov}/100\n"
        f"- Aesthetics & Composition (IAA): {iaa}/100\n"
        f"- Technical Quality & Clarity (IQA): {iqa}/100\n"
        f"- Structure & Textural Details (ISTA): {ista}/100\n"
        f"Instruction: Analyze this photo reflecting these exact scores. If any score is under 70, strictly focus on identifying the specific visual defects, noise, blur, lighting imbalance, or compositional flaws. Do NOT use inflated praise words like 'masterpiece', 'flawless', or 'impeccable' unless scores exceed 90.\n\n"
    )

    from services.ai_parser import (
        UNIPERCEPT_VQA_IAA_PROMPT,
        UNIPERCEPT_VQA_IQA_PROMPT,
        UNIPERCEPT_VQA_ISTA_PROMPT
    )
    from PIL import Image, ImageOps
    from services.unipercept_adapter import build_transform, GPU_LOCK
    import torch

    with Image.open(full_path) as raw_img:
        t_img = ImageOps.exif_transpose(raw_img)
        pil_img = t_img.convert("RGB") if t_img.mode != "RGB" else t_img.copy()

    target_dtype = uni.torch_dtype
    transform = build_transform(input_size=448)
    pixel_values = transform(pil_img).unsqueeze(0).to(dtype=target_dtype).to(uni.device)

    cond_prompts = {
        "iaa": f"{score_ctx}{UNIPERCEPT_VQA_IAA_PROMPT}",
        "iqa": f"{score_ctx}{UNIPERCEPT_VQA_IQA_PROMPT}",
        "ista": f"{score_ctx}{UNIPERCEPT_VQA_ISTA_PROMPT}"
    }

    gen_config = dict(max_new_tokens=512, do_sample=False, num_beams=1, repetition_penalty=1.2)
    vqa_b_res = {}
    for dom_key, ptext in cond_prompts.items():
        with GPU_LOCK:
            if hasattr(uni.model, "chat"):
                txt = uni.model.chat(uni.tokenizer, pixel_values, ptext, generation_config=gen_config)
            else:
                inputs = uni.processor(images=pil_img, text=ptext, return_tensors="pt").to(uni.device, dtype=uni.torch_dtype)
                with torch.no_grad():
                    outputs = uni.model.generate(**inputs, max_new_tokens=512)
                txt = uni.processor.decode(outputs[0], skip_special_tokens=True)
            vqa_b_res[dom_key] = txt.strip()

    raw_en_b = (
        f"[Aesthetics & Composition]\n{vqa_b_res.get('iaa', '')}\n\n"
        f"[Technical Quality & Clarity]\n{vqa_b_res.get('iqa', '')}\n\n"
        f"[Structure & Textural Details]\n{vqa_b_res.get('ista', '')}"
    )
    time_b = time.time() - t1
    print(f"[{fn}] UniPercept Variant B finished in {time_b:.2f}s")

    # UNLOAD UNIPERCEPT IMMEDIATELY
    print(f"[{fn}] Unloading UniPercept model before loading Gemma...", flush=True)
    uni.unload_model()
    free_system_memory()
    time.sleep(2)

    # --- PHASE 2: Gemma 4 Korean Translation Phase ---
    print(f"\n--- Phase 2: Gemma 4 Translation (A + B) ---", flush=True)
    from services.ai_factory import get_gemma_adapter
    gemma = get_gemma_adapter()

    t_tr_a = time.time()
    ko_a = gemma.translate_and_format_critique(raw_en_a, scores, scores.get("overall"))
    time_tr_a = time.time() - t_tr_a

    t_tr_b = time.time()
    ko_b = gemma.translate_and_format_critique(raw_en_b, scores, scores.get("overall"))
    time_tr_b = time.time() - t_tr_b

    # UNLOAD GEMMA IMMEDIATELY
    print(f"[{fn}] Unloading Gemma 4 model after translation...", flush=True)
    gemma.unload_model()
    free_system_memory()
    time.sleep(2)

    # Record item result
    item_record = {
        "file_name": fn,
        "scores": scores,
        "variant_a_current": {
            "raw_en": raw_en_a,
            "ko_translated": ko_a,
            "latency_sec": time_a + time_tr_a
        },
        "variant_b_score_conditioned": {
            "raw_en": raw_en_b,
            "ko_translated": ko_b,
            "latency_sec": time_b + time_tr_b
        }
    }
    results.append(item_record)

    # Save progress after every photo
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[{fn}] Saved progress ({len(results)}/{len(files)} completed).")

print(f"\nAll {len(files)} photos completed safely without memory leaks! Final results in {output_json}")
