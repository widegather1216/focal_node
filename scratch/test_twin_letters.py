import os
import sys

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

from transformers import AutoTokenizer

def main():
    model_path = "widegather/unipercept-mirror"
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    
    # Let's generate aa..az, ba..bz, ca..cz, da..dz
    tokens = []
    for c1 in "abcdefghijklmnopqrstuvwxyz":
        for c2 in "abcdefghijklmnopqrstuvwxyz":
            t = c1 + c2
            tokens.append(t)
            if len(tokens) == 101:
                break
        if len(tokens) == 101:
            break

    print(f"Generated 101 candidate twin-letter tokens: {tokens[:5]} ... {tokens[-5:]}")
    
    # Check if each token is a single token ID in the vocabulary
    single_token_ids = []
    for i, t in enumerate(tokens):
        ids = tokenizer.encode(t, add_special_tokens=False)
        single_token_ids.append((i, t, ids))
    
    multi_count = sum(1 for _, _, ids in single_token_ids if len(ids) > 1)
    print(f"Number of multi-token twin letters: {multi_count}/101")
    if multi_count == 0:
        print("ALL 101 twin-letter tokens are single tokens in tokenizer vocabulary!")
        print(f"Token IDs range sample: aa={single_token_ids[0][2]}, ab={single_token_ids[1][2]}, cz={single_token_ids[-1][2]}")

if __name__ == "__main__":
    main()
