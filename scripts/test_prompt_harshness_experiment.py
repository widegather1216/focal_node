#!/usr/bin/env python3
"""
Prompt Harshness Experiment Script:
Compares score outputs between Comprehensive prompt vs Dedicated Prompts (IAA, IQA, ISTA).
Tests whether Dedicated Prompts give systematically lower (harsher) scores.
"""

import os
import sys
import numpy as np
from PIL import Image, ImageDraw

# Ensure backend/app is in Python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
BACKEND_APP_DIR = os.path.join(PROJECT_ROOT, "backend", "app")
if BACKEND_APP_DIR not in sys.path:
    sys.path.insert(0, BACKEND_APP_DIR)

def create_synthetic_test_images(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    img_paths = []

    # 1. Scenic Landscape (High aesthetic, clear detail)
    img1 = Image.new("RGB", (800, 600), color=(135, 206, 235))
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle([0, 400, 800, 600], fill=(34, 139, 34)) # Green ground
    draw1.ellipse([600, 50, 720, 170], fill=(255, 215, 0)) # Sun
    p1 = os.path.join(output_dir, "test_scenic.jpg")
    img1.save(p1)
    img_paths.append(p1)

    # 2. Noisy / Blur Photo (Medium aesthetic, poor quality)
    arr = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
    img2 = Image.fromarray(arr)
    p2 = os.path.join(output_dir, "test_noisy.jpg")
    img2.save(p2)
    img_paths.append(p2)

    return img_paths

def run_harshness_experiment():
    print("=" * 60)
    print(" 🧪 UniPercept Prompt Harshness & Rigor Experiment")
    print("=" * 60)

    # Prepare sample images
    test_dir = os.path.join(PROJECT_ROOT, "scratch", "test_images")
    img_paths = create_synthetic_test_images(test_dir)

    from services.unipercept_adapter import get_unipercept_adapter
    adapter = get_unipercept_adapter()

    print(f"\n[Experiment] Loaded UniPercept adapter on device: {adapter.device}")
    print(f"[Experiment] Testing {len(img_paths)} synthetic test images...\n")

    results = []

    for idx, img_path in enumerate(img_paths, 1):
        file_name = os.path.basename(img_path)
        print(f"📸 Image {idx}/{len(img_paths)}: {file_name}")

        try:
            ensemble_res = adapter.generate_full_ensemble_critique(img_path)
            scores = ensemble_res.get("scores", {})

            print(f"  - Comprehensive Direct Score: {scores.get('comp_direct')}")
            print(f"  - Dedicated IAA (Aesthetics): {scores.get('iaa')}")
            print(f"  - Dedicated IQA (Quality):    {scores.get('iqa')}")
            print(f"  - Dedicated ISTA (Structure): {scores.get('ista')}")
            print(f"  - Weighted Analysis Score:   {scores.get('weighted_analysis')}")
            print(f"  - Final Dual-Fusion Score:    {scores.get('overall')}\n")

            results.append({
                "file": file_name,
                "comp_direct": scores.get('comp_direct'),
                "iaa": scores.get('iaa'),
                "iqa": scores.get('iqa'),
                "ista": scores.get('ista'),
                "weighted_analysis": scores.get('weighted_analysis'),
                "overall": scores.get('overall'),
            })
        except Exception as e:
            print(f"  ❌ Error evaluating {file_name}: {e}")

    # Calculate differences
    comp_scores = [r["comp_direct"] for r in results if r["comp_direct"] is not None]
    analysis_scores = [r["weighted_analysis"] for r in results if r["weighted_analysis"] is not None]

    if comp_scores and analysis_scores:
        avg_comp = sum(comp_scores) / len(comp_scores)
        avg_analysis = sum(analysis_scores) / len(analysis_scores)
        diff = avg_comp - avg_analysis

        print("=" * 60)
        print("📊 Experiment Summary & Analysis")
        print("=" * 60)
        print(f"- Average Comprehensive Direct Score: {avg_comp:.1f} pts")
        print(f"- Average Dedicated Analysis Score:  {avg_analysis:.1f} pts")
        print(f"- Score Difference (Harshness Gap):   {diff:+.1f} pts")

        if diff > 0:
            print("\n✅ HYPOTHESIS CONFIRMED: Dedicated prompts give systematically HARSHER (lower) scores.")
        else:
            print("\nℹ️ HYPOTHESIS REJECTED: Dedicated prompts did not give lower scores in this sample.")
        print("=" * 60)

    adapter.unload_model()

if __name__ == "__main__":
    run_harshness_experiment()
