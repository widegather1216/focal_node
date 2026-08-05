#!/usr/bin/env python3
"""
Deep Failure Case Analyzer: Why and When UniPercept Misses Scores.
Analyzes 100 raw benchmark outputs and classifies root causes of missing scores.
"""

import os
import sys
import json
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

def analyze_missing_score_cases():
    bm_path = os.path.join(PROJECT_ROOT, "benchmark_results_unipercept.json")
    if not os.path.exists(bm_path):
        print(f"Benchmark file not found: {bm_path}")
        return

    with open(bm_path, "r", encoding="utf-8") as f:
        bm = json.load(f)

    records = []
    for r_item in bm.get("rounds_data", []):
        for img_item in r_item.get("images", []):
            f_name = img_item.get("file_name")
            for p_name, p_res in img_item.get("prompt_results", {}).items():
                critique = p_res.get("critique", "")
                records.append({
                    "file_name": f_name,
                    "prompt_name": p_name,
                    "critique": critique,
                    "quality_score": p_res.get("quality_score")
                })

    total = len(records)
    print(f"Total samples: {total}")

    # Categorization buckets
    by_prompt = {}
    truncated_count = 0
    variant_format_count = 0
    completely_missing_count = 0
    corrupted_format_count = 0 # e.g. XX/1100 or XX /XX
    has_score_count = 0

    samples_truncated = []
    samples_variant = []
    samples_corrupted = []
    samples_completely_omitted = []
    samples_success = []

    for item in records:
        p_name = item["prompt_name"]
        text = item["critique"].strip()
        by_prompt.setdefault(p_name, {"total": 0, "missing": 0, "success": 0})
        by_prompt[p_name]["total"] += 1

        # Check ending punctuation / truncation
        is_truncated = not (text.endswith(".") or text.endswith('"') or text.endswith("'") or text.endswith(")") or text.endswith("0") or text.endswith("]"))
        # Check if text ends mid-sentence or token limit hit
        last_line = text.split("\n")[-1].strip() if text else ""

        # Search for any score-like patterns
        # 1. Standard pattern: Score: XX/100
        has_std_score = bool(re.search(r"(?:Score|IAA|IQA|ISTA)\s*[:=]\s*\d{1,3}\s*(?:/|out of)\s*100", text, re.IGNORECASE))
        # 2. Corrupted pattern: e.g. Score: XX/1100, Score XX /XX, Score: 30/1100
        has_corrupted_score = bool(re.search(r"Score\s*[:=]?\s*(?:XX|\d{1,3})\s*/\s*(?:1100|XX|\d{4})", text, re.IGNORECASE))
        # 3. Variant pattern: e.g. Score: 85 (without /100), or 'rated 85'
        has_variant_score = bool(re.search(r"(?:Score|Rating|Aesthetic|Quality|Structure)\s*[:=]\s*(\d{1,3})\b(?!\s*/\s*100)", text, re.IGNORECASE))
        # 4. Embedded numbers in text (e.g. 'giving it a score of 7')
        has_embedded_score = bool(re.search(r"(?:score of|rating of)\s*(\d{1,3})", text, re.IGNORECASE))

        if has_std_score and not has_corrupted_score:
            has_score_count += 1
            by_prompt[p_name]["success"] += 1
            if len(samples_success) < 3:
                samples_success.append((p_name, text[-150:]))
        else:
            by_prompt[p_name]["missing"] += 1
            if has_corrupted_score:
                corrupted_format_count += 1
                if len(samples_corrupted) < 3:
                    samples_corrupted.append((p_name, last_line, text[-180:]))
            elif has_variant_score or has_embedded_score:
                variant_format_count += 1
                if len(samples_variant) < 3:
                    samples_variant.append((p_name, last_line, text[-180:]))
            elif is_truncated:
                truncated_count += 1
                if len(samples_truncated) < 3:
                    samples_truncated.append((p_name, last_line, text[-180:]))
            else:
                completely_missing_count += 1
                if len(samples_completely_omitted) < 5:
                    samples_completely_omitted.append((p_name, last_line, text[-250:]))

    print("\n" + "="*70)
    print(" 🔬 DETAILED ROOT CAUSE ANALYSIS: WHY SCORES ARE MISSED")
    print("="*70)
    print(f"Total Evaluations Analyzed: {total}")
    print(f"✅ Explicit Standard Score Present: {has_score_count}/{total} ({has_score_count/total*100:.1f}%)")
    print(f"❌ Missing / Malformed Score Cases: {total - has_score_count}/{total} ({(total-has_score_count)/total*100:.1f}%)")

    print("\n--- 1. Breakdown by Prompt Type ---")
    for p_name, stats in by_prompt.items():
        missing_rate = (stats["missing"] / stats["total"]) * 100 if stats["total"] else 0
        print(f"  • {p_name:25s}: Total={stats['total']}, Missing={stats['missing']} ({missing_rate:.1f}%), Success={stats['success']}")

    print("\n--- 2. Root Cause Classification of Failures ---")
    print(f"  [Cause A] Completely Omitted (Model finished narrative but forgot score block): {completely_missing_count} cases ({completely_missing_count/(total-has_score_count)*100:.1f}%)")
    print(f"  [Cause B] Corrupted / Placeholder Tokens (e.g. 'XX/XX', '30/1100' artifact): {corrupted_format_count} cases ({corrupted_format_count/(total-has_score_count)*100:.1f}%)")
    print(f"  [Cause C] Variant / Embedded Formats (e.g. 'Score: 85' without /100, or in-text): {variant_format_count} cases ({variant_format_count/(total-has_score_count)*100:.1f}%)")
    print(f"  [Cause D] Max Token Truncation (Cut off mid-sentence before score): {truncated_count} cases ({truncated_count/(total-has_score_count)*100:.1f}%)")

    print("\n--- 3. Real Output Snippets by Failure Mode ---")
    print("\n[Cause A Examples: Completely Omitted Narrative Endings]")
    for p, ll, snippet in samples_completely_omitted[:3]:
        print(f"  • [{p}] Ending: ...{snippet.replace(chr(10), ' ')}")

    print("\n[Cause B Examples: Corrupted / Placeholder Hallucination]")
    for p, ll, snippet in samples_corrupted[:3]:
        print(f"  • [{p}] Ending: ...{snippet.replace(chr(10), ' ')}")

    print("\n[Cause C Examples: Variant Formats]")
    for p, ll, snippet in samples_variant[:3]:
        print(f"  • [{p}] Ending: ...{snippet.replace(chr(10), ' ')}")

    print("\n" + "="*70)

if __name__ == "__main__":
    analyze_missing_score_cases()
