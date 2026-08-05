import os
import time
import torch
from app.services.unipercept_adapter import get_unipercept_adapter

def test_full_6way():
    img_path = os.path.abspath("scratch/test_images/test_scenic.jpg")
    adapter = get_unipercept_adapter()
    
    print(f"=== Starting 100% Official 6-Way Ensemble Pipeline on: {img_path} ===")
    t0 = time.time()
    result = adapter.generate_full_ensemble_critique(img_path)
    elapsed = time.time() - t0
    
    print(f"\n[Result in {elapsed:.2f}s]")
    print(f"Scores: {result['scores']}")
    print(f"Quality Score: {result['quality_score']}")
    print(f"\nCritique Output:\n{result['critique']}")
    
    adapter.unload_model()
    print("\n[Done] Model unloaded successfully.")

if __name__ == "__main__":
    test_full_6way()
