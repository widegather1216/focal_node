#!/usr/bin/env python3
"""
Comprehensive Prompt Deep-Dive:
Examines all 25 Comprehensive Prompt outputs to see exactly which score is missed (Overall, IAA, IQA, or ISTA)
and why the trailing/last scores (e.g. ISTA / Structure) are consistently dropped.
"""

import os
import sys
import json
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

def inspect_comprehensive_outputs():
    bm_path = os.path.join(PROJECT_ROOT, "benchmark_results_unipercept.json")
    if not os.path.exists(bm_path):
        print("benchmark file not found")
        return

    with open(bm_path, "r", encoding="utf-8") as f:
        bm = json.load(f)

    comp_items = []
    for r_item in bm.get("rounds_data", []):
        for img_item in r_item.get("images", []):
            f_name = img_item.get("file_name")
            p_res = img_item.get("prompt_results", {}).get("Comprehensive (종합 평가)", {})
            if p_res:
                comp_items.append({
                    "file_name": f_name,
                    "critique": p_res.get("critique", "")
                })

    print(f"Total Comprehensive Samples: {len(comp_items)}")

    # Score presence tracking
    score_presence = {"overall": 0, "iaa": 0, "iqa": 0, "ista": 0}
    position_breakdown = {
        "all_4_present": 0,
        "first_3_only (missed ISTA)": 0,
        "first_2_only (missed IQA+ISTA)": 0,
        "first_1_only (missed IAA+IQA+ISTA)": 0,
        "none_present": 0
    }

    detailed_cases = []

    for idx, item in enumerate(comp_items, 1):
        text = item["critique"].strip()
        has_ov = bool(re.search(r"Overall\s*Score", text, re.IGNORECASE))
        has_iaa = bool(re.search(r"(?:IAA\s*Score|Aesthetic[s]?\s*Score)", text, re.IGNORECASE))
        has_iqa = bool(re.search(r"(?:IQA\s*Score|Quality\s*Score)", text, re.IGNORECASE))
        has_ista = bool(re.search(r"(?:ISTA\s*Score|Structure\s*Score)", text, re.IGNORECASE))

        if has_ov: score_presence["overall"] += 1
        if has_iaa: score_presence["iaa"] += 1
        if has_iqa: score_presence["iqa"] += 1
        if has_ista: score_presence["ista"] += 1

        score_cnt = sum([has_ov, has_iaa, has_iqa, has_ista])
        if score_cnt == 4:
            position_breakdown["all_4_present"] += 1
        elif has_ov and has_iaa and has_iqa and not has_ista:
            position_breakdown["first_3_only (missed ISTA)"] += 1
        elif has_ov and has_iaa and not has_iqa and not has_ista:
            position_breakdown["first_2_only (missed IQA+ISTA)"] += 1
        elif score_cnt == 1:
            position_breakdown["first_1_only (missed IAA+IQA+ISTA)"] += 1
        elif score_cnt == 0:
            position_breakdown["none_present"] += 1

        detailed_cases.append({
            "id": idx,
            "file": item["file_name"],
            "length": len(text),
            "scores_found": [k for k, v in [("Overall", has_ov), ("IAA", has_iaa), ("IQA", has_iqa), ("ISTA", has_ista)] if v],
            "last_120_chars": text[-120:].replace("\n", " ↵ ")
        })

    print("\n" + "="*70)
    print(" 🔬 COMPREHENSIVE PROMPT: SCORE-BY-SCORE DROPOUT ANALYSIS")
    print("="*70)
    print(f"Total Samples Analyzed: {len(comp_items)}")
    print("\n[Score-by-Score Detection Rates]:")
    print(f"  1. Overall Score : {score_presence['overall']}/{len(comp_items)} ({score_presence['overall']/len(comp_items)*100:.1f}%)")
    print(f"  2. IAA Score     : {score_presence['iaa']}/{len(comp_items)} ({score_presence['iaa']/len(comp_items)*100:.1f}%)")
    print(f"  3. IQA Score     : {score_presence['iqa']}/{len(comp_items)} ({score_presence['iqa']/len(comp_items)*100:.1f}%)")
    print(f"  4. ISTA Score    : {score_presence['ista']}/{len(comp_items)} ({score_presence['ista']/len(comp_items)*100:.1f}%) 🚨")

    print("\n[Dropout Pattern Breakdown]:")
    for k, v in position_breakdown.items():
        print(f"  • {k:35s}: {v} cases ({v/len(comp_items)*100:.1f}%)")

    print("\n[Detailed Sample Endings (Showing Trailing Dropout)]: ")
    for c in detailed_cases[:8]:
        print(f"  [{c['id']:02d}] Scores: {c['scores_found']}")
        print(f"       Tail: ...{c['last_120_chars']}")

if __name__ == "__main__":
    inspect_comprehensive_outputs()
