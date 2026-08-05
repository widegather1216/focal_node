#!/usr/bin/env python3
"""
A/B/C Prompt Variant Benchmark for UniPercept.
Compares Structured Template (A), Natural Flow (B), and Minimal Direct (C)
across multiple diverse photos to evaluate:
1. Score Extraction Completeness (4/4 scores or overall score)
2. Quality and Depth of Critique (Richness of vocabulary, insight)
3. Natural readability and flow
"""

import os
import sys
import json
import time
from typing import Dict, Any, List

# Allow PyTorch to use full unified memory without hitting default MPS limit
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"

try:
    import gc
    import torch
    gc.collect()
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        torch.mps.empty_cache()
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend", "app"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

PROMPT_VARIANTS = {
    "Variant_A_Structured": {
        "name": "후보 A: 구조화 템플릿 강제형",
        "prompt": (
            "Rate this photo from 0 to 100.\n\n"
            "Template:\n"
            "Overall Score: [0-100]/100\n"
            "Aesthetic Score: [0-100]/100\n"
            "Quality Score: [0-100]/100\n"
            "Structure Score: [0-100]/100\n\n"
            "Analysis:\n"
            "- Aesthetics:\n"
            "- Quality:\n"
            "- Structure:"
        )
    },
    "Variant_B_Natural_Flow": {
        "name": "후보 B: 점수 선출력 + 자연 서술형 (Natural Flow)",
        "prompt": (
            "Rate this photo from 0 to 100 and write a detailed photographic critique.\n\n"
            "Overall Score: [0-100]/100\n"
            "Aesthetic Score: [0-100]/100\n"
            "Quality Score: [0-100]/100\n"
            "Structure Score: [0-100]/100\n\n"
            "Critique:"
        )
    },
    "Variant_C_Minimal_Direct": {
        "name": "후보 C: 초간결 직접 명령형",
        "prompt": (
            "Evaluate this photo technically and aesthetically. "
            "Output the score first as 'Overall Score: XX/100', followed by your technical critique."
        )
    }
}

def run_ab_test():
    from app.services.unipercept_adapter import get_unipercept_adapter, UniPerceptAdapter
    
    # 4 distinct test images
    candidate_images = [
        "/Users/kimbeomjun/Desktop/photo/jpeg/_DSC0561_edit.jpg", # Street & graffiti masterpiece
        os.path.join(PROJECT_ROOT, "scratch/test_images/test_scenic.jpg"), # Scenic nature
        "/Users/kimbeomjun/Desktop/photo/jpeg/morning_glory.jpg", # Close-up flower detail
        "/Users/kimbeomjun/Desktop/photo/jpeg/DSC_0290_edit.jpg" # Urban architecture / people
    ]

    valid_images = [p for p in candidate_images if os.path.exists(p)]
    if not valid_images:
        print("No valid test images found!")
        return

    print(f"🔬 Starting A/B/C Prompt Variant Benchmark on {len(valid_images)} test images...")
    adapter = get_unipercept_adapter()

    results = []

    for img_path in valid_images:
        f_name = os.path.basename(img_path)
        print(f"\n" + "="*70)
        print(f"📸 Testing Image: {f_name}")
        print("="*70)

        img_result = {
            "file_name": f_name,
            "file_path": img_path,
            "variants": {}
        }

        for var_key, var_info in PROMPT_VARIANTS.items():
            print(f"\n  ▶ Testing [{var_info['name']}]...")
            t0 = time.time()
            
            # Execute with single attempt without retrying to measure raw obedience
            res = adapter.generate_unipercept_critique(
                img_path,
                custom_prompt=var_info["prompt"],
                retry_if_score_missing=False
            )
            elapsed = round(time.time() - t0, 2)
            
            raw_text = res.get("critique", "")
            
            # Extract scores using our smart parser
            scores_dict = adapter._extract_all_scores_dict(raw_text)
            single_score = adapter._extract_score_from_text(raw_text, ["Overall Score", "Score", "Aesthetic Score", "Quality Score", "Structure Score"])
            
            # Count valid scores
            valid_scores_count = sum(1 for v in scores_dict.values() if v is not None)
            
            img_result["variants"][var_key] = {
                "name": var_info["name"],
                "elapsed_sec": elapsed,
                "raw_text": raw_text,
                "scores_dict": scores_dict,
                "single_score": single_score,
                "valid_scores_count": valid_scores_count,
                "char_length": len(raw_text)
            }

            print(f"     Elapsed: {elapsed}s | Scores Found: {valid_scores_count}/4 | Single Score: {single_score}")
            print(f"     Snippet:\n{raw_text[:200]}...")

        results.append(img_result)

    # Save results to JSON
    out_json = os.path.join(PROJECT_ROOT, "benchmark_results_ab_prompt_variants.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "="*70)
    print(f"✅ A/B/C Benchmark Complete! Saved to: {out_json}")
    print("="*70)

if __name__ == "__main__":
    run_ab_test()
