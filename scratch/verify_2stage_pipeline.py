import os
import sys
import time

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

from services.unipercept_adapter import get_unipercept_adapter

def main():
    img_path = os.path.abspath("scratch/test_images/test_scenic.jpg")
    print(f"=== Testing 2-Stage VR/VQA Pipeline on {img_path} ===")
    
    adapter = get_unipercept_adapter()
    
    start_time = time.time()
    res = adapter.generate_full_ensemble_critique(img_path)
    elapsed = time.time() - start_time
    
    print("\n--- VR Extraction Raw Text ---")
    print(res.get("raw_vr_text"))
    
    print("\n--- Final Scoreboard ---")
    scores = res.get("scores", {})
    print(f"Overall Score:    {scores.get('overall')}/100 (Formula: round(0.4*IAA + 0.3*IQA + 0.3*ISTA))")
    print(f"Aesthetic (IAA):  {scores.get('iaa')}/100")
    print(f"Quality (IQA):    {scores.get('iqa')}/100")
    print(f"Structure (ISTA): {scores.get('ista')}/100")
    
    print("\n--- VQA Critique (Pure Depth) ---")
    print(res.get("critique"))
    
    print(f"\nTotal Pipeline Latency: {elapsed:.2f}s")
    
    adapter.unload_model()

if __name__ == "__main__":
    main()
