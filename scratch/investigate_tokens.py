import os
import sys

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

from transformers import AutoTokenizer

def main():
    model_path = "widegather/unipercept-mirror"
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    
    print(f"Tokenizer vocab size: {len(tokenizer)}")
    
    # Check token IDs for numbers 0 to 100
    token_map = {}
    for i in range(101):
        s = str(i)
        ids = tokenizer.encode(s, add_special_tokens=False)
        # also check with leading space or format
        token_map[i] = ids
    
    print("Sample number token encodings (0..10, 50, 100):")
    for i in [0, 1, 2, 5, 10, 50, 99, 100]:
        print(f"  Number {i}: token_ids = {token_map[i]}, decoded = {[tokenizer.decode([tid]) for tid in token_map[i]]}")

if __name__ == "__main__":
    main()
