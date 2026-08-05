#!/usr/bin/env python3
"""
Raw EN vs KO Translation Comparison Script:
Runs UniPercept to get raw English critique, then runs Gemma 4 translation,
and prints both side-by-side for exact alignment check.
"""

import os
import sys
import asyncio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
BACKEND_APP_DIR = os.path.join(PROJECT_ROOT, "backend", "app")
if BACKEND_APP_DIR not in sys.path:
    sys.path.insert(0, BACKEND_APP_DIR)

async def run_comparison():
    test_img = os.path.join(PROJECT_ROOT, "scratch", "test_images", "test_scenic.jpg")
    if not os.path.exists(test_img):
        print(f"Test image not found at {test_img}")
        return

    print("=" * 70)
    print(" 🔬 RAW UniPercept EN Critique vs Gemma 4 KO Translation Comparison")
    print("=" * 70)

    from services.unipercept_adapter import get_unipercept_adapter
    from services.ai_factory import get_gemma_adapter

    print("\n[Step 1] Generating UniPercept 4-Ensemble Raw EN Critique...")
    uni_adapter = get_unipercept_adapter()
    res_dict = await asyncio.to_thread(
        uni_adapter.generate_full_ensemble_critique,
        test_img,
        None
    )
    raw_en = res_dict.get("critique", "")
    scores_dict = res_dict.get("scores", {})
    quality_score = res_dict.get("quality_score")

    print("\n--------------------------------------------------")
    print(" 🇬🇧 [RAW UniPercept English Output (원문)]")
    print("--------------------------------------------------")
    print(raw_en)

    print("\n[Step 2] Translating via Gemma 4 (1:1 Faithful Mode)...")
    gemma_adapter = get_gemma_adapter()
    ko_translation = await asyncio.to_thread(
        gemma_adapter.translate_and_format_critique,
        raw_en,
        scores_dict,
        quality_score
    )

    print("\n--------------------------------------------------")
    print(" 🇰🇷 [Gemma 4 Korean Translation Output (번역본)]")
    print("--------------------------------------------------")
    print(ko_translation)
    print("=" * 70)

    uni_adapter.unload_model()

if __name__ == "__main__":
    asyncio.run(run_comparison())
