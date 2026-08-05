import os
import sys
import time
import torch
from PIL import Image

sys.path.insert(0, os.path.abspath("backend/app"))
from services.unipercept_adapter import get_unipercept_adapter

def run_test():
    adapter = get_unipercept_adapter()
    adapter._load_model_locked()

    test_img = os.path.abspath("scratch/test_images/test_scenic.jpg")
    print(f"Testing on image: {test_img}")

    # 1. VR Mode: Dedicated Score-Only Prompt (Ultra Fast, max_tokens=40)
    print("\n" + "="*60)
    print("🚀 [Step 1] VR Mode (Visual Rating - Score Only, max_tokens=40)")
    print("="*60)
    
    vr_prompt = (
        "Rate this photo from 0 to 100 across 4 dimensions. Output ONLY the scores in this exact format:\n"
        "Overall Score: [0-100]\n"
        "Aesthetic Score: [0-100]\n"
        "Quality Score: [0-100]\n"
        "Structure Score: [0-100]"
    )

    t0 = time.time()
    res_vr = adapter.generate_unipercept_critique(
        test_img,
        custom_prompt=vr_prompt,
        retry_if_score_missing=True,
        max_retries=3
    )
    t_vr = time.time() - t0

    print(f"⏱️ VR Elapsed Time: {t_vr:.2f}s")
    print(f"VR Raw Output:\n{res_vr['critique']}")
    
    scores = adapter._extract_all_scores_dict(res_vr['critique'])
    print(f"Parsed Scores: {scores}")

    # 2. VQA Mode: Pure Critique Prompt (No score pressure, max_tokens=1024)
    print("\n" + "="*60)
    print("📝 [Step 2] VQA Mode (Visual Question Answering - Pure Critique, max_tokens=1024)")
    print("="*60)
    
    vqa_prompt = (
        "Write a comprehensive and professional photographic critique for this image. "
        "Analyze the composition, lighting nuances, optical depth of field, color harmony, and surface textures in detail."
    )

    t0 = time.time()
    res_vqa = adapter.generate_unipercept_critique(
        test_img,
        custom_prompt=vqa_prompt,
        retry_if_score_missing=False
    )
    t_vqa = time.time() - t0

    print(f"⏱️ VQA Elapsed Time: {t_vqa:.2f}s")
    print(f"VQA Raw Critique:\n{res_vqa['critique'][:500]}...")

    # 3. Combined Result
    print("\n" + "="*60)
    print("🎯 [Step 3] Final Combined Result (Scoreboard + VQA Critique)")
    print("="*60)
    combined = {
        "scores": scores,
        "critique": res_vqa['critique']
    }
    print(f"Final Scores: {combined['scores']}")
    print(f"Critique Length: {len(combined['critique'])} chars")

if __name__ == "__main__":
    run_test()
