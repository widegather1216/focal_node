import os
import sys
import time

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

import torch
from services.unipercept_adapter import get_unipercept_adapter, build_transform, GPU_LOCK
from utils.image import is_raw_image, decode_raw_to_pil
from PIL import Image, ImageOps

def run_6way_test(image_path: str):
    print(f"=== 6-Way Dedicated Ensemble Verification on {image_path} ===")
    
    adapter = get_unipercept_adapter()
    adapter._load_model_locked()
    
    if is_raw_image(image_path):
        pil_img = decode_raw_to_pil(image_path)
    else:
        with Image.open(image_path) as raw_img:
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

    # 1. 3 Dedicated VR Prompts (Official Benchmark Style)
    vr_prompts = {
        "iaa": "Evaluate the aesthetic quality of this image on a scale from 1 to 100. Output ONLY the score: Aesthetic Score: [1-100]",
        "iqa": "Evaluate the technical image quality of this image on a scale from 1 to 100. Output ONLY the score: Quality Score: [1-100]",
        "ista": "Evaluate the structural and textural quality of this image on a scale from 1 to 100. Output ONLY the score: Structure Score: [1-100]"
    }

    # 2. 3 Dedicated VQA Prompts (Deep Perceptual Analysis)
    vqa_prompts = {
        "iaa": "Analyze the aesthetic qualities of this image in detail, focusing on composition, visual balance, lighting mood, color grading harmony, and artistic impact.",
        "iqa": "Analyze the technical image quality in detail, focusing on sharpness, optical clarity, depth of field, exposure balance, sensor noise, and lens characteristics.",
        "ista": "Analyze the structural and textural details in detail, focusing on surface textures, material definitions, edge clarity, geometry, and micro-contrast."
    }

    results = {
        "vr": {},
        "vqa": {},
        "timings": {}
    }

    total_start = time.time()

    # --- Phase 1: VR Mode (3 Calls) ---
    print("\n[Phase 1] Executing 3 Dedicated VR Inferences...")
    vr_config = dict(max_new_tokens=30, do_sample=False, num_beams=1, repetition_penalty=1.1)
    
    for key, prompt in vr_prompts.items():
        t0 = time.time()
        with GPU_LOCK:
            out_text = adapter.model.chat(adapter.tokenizer, pixel_values, prompt, generation_config=vr_config)
        elapsed = time.time() - t0
        score_val = adapter._extract_score_from_text(out_text, ["Aesthetic Score", "Quality Score", "Structure Score", "Score"])
        results["vr"][key] = {"raw": out_text.strip(), "score": score_val, "time": elapsed}
        print(f"  - VR {key.upper()}: score={score_val} ({elapsed:.2f}s) | Raw: {out_text.strip()}")

    # Compute Overall Score
    iaa_s = results["vr"]["iaa"]["score"] or 70
    iqa_s = results["vr"]["iqa"]["score"] or 70
    ista_s = results["vr"]["ista"]["score"] or 70
    overall_s = round((0.4 * iaa_s) + (0.3 * iqa_s) + (0.3 * ista_s))
    overall_s = min(100, max(0, overall_s))
    results["overall_score"] = overall_s

    # --- Phase 2: VQA Mode (3 Calls) ---
    print("\n[Phase 2] Executing 3 Dedicated VQA Inferences...")
    vqa_config = dict(max_new_tokens=512, do_sample=False, num_beams=1, repetition_penalty=1.2)
    
    for key, prompt in vqa_prompts.items():
        t0 = time.time()
        with GPU_LOCK:
            out_text = adapter.model.chat(adapter.tokenizer, pixel_values, prompt, generation_config=vqa_config)
        elapsed = time.time() - t0
        results["vqa"][key] = {"critique": out_text.strip(), "time": elapsed}
        print(f"  - VQA {key.upper()} ({elapsed:.2f}s): {out_text.strip()[:100]}...")

    total_elapsed = time.time() - total_start
    results["total_time"] = total_elapsed

    print("\n" + "="*50)
    print(f"=== 6-WAY ENSEMBLE SUMMARY (Total Time: {total_elapsed:.2f}s) ===")
    print(f"Overall Score:    {overall_s}/100")
    print(f"Aesthetic (IAA):  {iaa_s}/100 (VR Time: {results['vr']['iaa']['time']:.2f}s)")
    print(f"Quality (IQA):    {iqa_s}/100 (VR Time: {results['vr']['iqa']['time']:.2f}s)")
    print(f"Structure (ISTA): {ista_s}/100 (VR Time: {results['vr']['ista']['time']:.2f}s)")
    print("\n[VQA Text Previews]")
    print(f"1. IAA Critique:\n{results['vqa']['iaa']['critique']}\n")
    print(f"2. IQA Critique:\n{results['vqa']['iqa']['critique']}\n")
    print(f"3. ISTA Critique:\n{results['vqa']['ista']['critique']}\n")

    adapter.unload_model()
    return results

if __name__ == "__main__":
    img_path = os.path.abspath("scratch/test_images/test_scenic.jpg")
    run_6way_test(img_path)
