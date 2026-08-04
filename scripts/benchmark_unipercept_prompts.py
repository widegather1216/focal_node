#!/usr/bin/env python3
"""
UniPercept Benchmark Script: Compare Comprehensive vs Domain-Focused Critique Prompts
Runs 5 rounds of 5 randomly selected images (total 25 images) against 4 prompt variations.
"""

import os
import sys
import json
import random
import time
import argparse
from typing import List, Dict, Any

# Ensure backend/app is in Python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
BACKEND_APP_DIR = os.path.join(PROJECT_ROOT, "backend", "app")
if BACKEND_APP_DIR not in sys.path:
    sys.path.insert(0, BACKEND_APP_DIR)

PROMPTS = {
    "Comprehensive (종합 평가)": (
        "Evaluate this image comprehensively across three core domains: "
        "1. Image Aesthetics (IAA), 2. Image Quality (IQA), and 3. Structure & Texture (ISTA). "
        "Provide concise technical reasons for each domain and a final score out of 100."
    ),
    "Aesthetics Focus (IAA 미학/구도)": (
        "Focus deeply on Image Aesthetics (IAA). "
        "Analyze composition, lighting, color harmony, subject placement, and visual impact. "
        "Detail how aesthetic choices elevate or weaken the photo, and rate the aesthetic score out of 100."
    ),
    "Quality Focus (IQA 화질/기술)": (
        "Focus strictly on Image Quality (IQA). "
        "Evaluate technical sharpness, sensor noise, exposure balance, focus accuracy, chromatic aberration, and dynamic range. "
        "Detail technical artifacts and rate technical quality out of 100."
    ),
    "Structure Focus (ISTA 구조/질감)": (
        "Focus intently on Structure & Texture (ISTA). "
        "Inspect fine detail resolution, micro-contrast, edge definitions, surface texture rendering, and tonal gradations. "
        "Detail textural fidelity and rate structural quality out of 100."
    ),
}

def get_image_files(directory: str) -> List[str]:
    valid_exts = {".jpg", ".jpeg", ".png", ".arw", ".cr3", ".nef"}
    files = []
    for f in os.listdir(directory):
        ext = os.path.splitext(f)[1].lower()
        if ext in valid_exts and not f.startswith("."):
            files.append(os.path.join(directory, f))
    return sorted(files)

def run_benchmark(
    photo_dir: str,
    rounds: int = 5,
    images_per_round: int = 5,
    output_json: str = "benchmark_results_unipercept.json",
    output_md: str = "benchmark_summary_unipercept.md",
    seed: int = 42
):
    print(f"[Benchmark] Scanning image directory: {photo_dir}")
    all_files = get_image_files(photo_dir)
    print(f"[Benchmark] Found {len(all_files)} images.")

    if len(all_files) < images_per_round:
        raise ValueError(f"Not enough images in {photo_dir}. Found {len(all_files)}, need at least {images_per_round}.")

    random.seed(seed)
    
    total_needed = rounds * images_per_round
    if len(all_files) >= total_needed:
        selected_pool = random.sample(all_files, total_needed)
        round_batches = [selected_pool[i * images_per_round:(i + 1) * images_per_round] for i in range(rounds)]
    else:
        round_batches = [random.sample(all_files, images_per_round) for _ in range(rounds)]

    print(f"[Benchmark] Loading UniPercept adapter...")
    from services.unipercept_adapter import get_unipercept_adapter
    adapter = get_unipercept_adapter()

    results_data = []
    total_tests = 0
    start_total_time = time.time()

    for r_idx, batch in enumerate(round_batches, 1):
        print(f"\n==================================================")
        print(f" 🚀 Round {r_idx}/{rounds} ({len(batch)} Images)")
        print(f"==================================================")

        round_entry = {
            "round": r_idx,
            "images": []
        }

        for img_idx, img_path in enumerate(batch, 1):
            file_name = os.path.basename(img_path)
            print(f"\n  📸 [Round {r_idx} - Photo {img_idx}/{len(batch)}] {file_name}")

            img_entry = {
                "file_name": file_name,
                "file_path": img_path,
                "prompt_results": {}
            }

            for p_name, p_text in PROMPTS.items():
                print(f"    - Running prompt: '{p_name}'... ", end="", flush=True)
                t0 = time.time()
                try:
                    res = adapter.generate_unipercept_critique(
                        image_path=img_path,
                        metadata=None,
                        custom_prompt=p_text
                    )
                    elapsed = round(time.time() - t0, 2)
                    critique_text = res.get("critique", "")
                    quality_score = res.get("quality_score")

                    print(f"Done in {elapsed}s (Score: {quality_score})")

                    img_entry["prompt_results"][p_name] = {
                        "prompt_text": p_text,
                        "critique": critique_text,
                        "quality_score": quality_score,
                        "latency_sec": elapsed
                    }
                except Exception as e:
                    print(f"Error: {e}")
                    img_entry["prompt_results"][p_name] = {
                        "error": str(e),
                        "latency_sec": round(time.time() - t0, 2)
                    }

                total_tests += 1

            round_entry["images"].append(img_entry)

        results_data.append(round_entry)

    total_elapsed = round(time.time() - start_total_time, 2)
    print(f"\n[Benchmark] Completed {total_tests} inference evaluations across {rounds} rounds in {total_elapsed}s.")

    # Save JSON
    output_json_path = os.path.join(PROJECT_ROOT, output_json)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_rounds": rounds,
            "images_per_round": images_per_round,
            "total_images": rounds * images_per_round,
            "total_evaluations": total_tests,
            "total_time_sec": total_elapsed,
            "rounds_data": results_data
        }, f, ensure_ascii=False, indent=2)
    print(f"[Benchmark] Saved full raw results to {output_json_path}")

    # Generate Markdown Summary
    output_md_path = os.path.join(PROJECT_ROOT, output_md)
    generate_markdown_report(results_data, output_md_path, total_elapsed)
    print(f"[Benchmark] Saved summary report to {output_md_path}")

    # Explicitly unload model to free memory
    adapter.unload_model()

def generate_markdown_report(results_data: List[Dict[str, Any]], output_md_path: str, total_elapsed: float):
    md_lines = []
    md_lines.append("# UniPercept 프롬프트 4종 비교 벤치마크 결과 리포트\n")
    md_lines.append(f"- **총 실행 회차**: {len(results_data)}회차 (회차당 5장 무작위, 총 {len(results_data)*5}장)")
    md_lines.append(f"- **총 추론 수행 횟수**: {len(results_data)*5*4}회 (25장 x 4개 프롬프트)")
    md_lines.append(f"- **총 소요 시간**: {total_elapsed:.1f}초\n")
    md_lines.append("---\n")

    for round_item in results_data:
        r_num = round_item["round"]
        md_lines.append(f"## 📌 Round {r_num}\n")

        for img_item in round_item["images"]:
            file_name = img_item["file_name"]
            md_lines.append(f"### 📷 이미지: `{file_name}`\n")
            md_lines.append("| 프롬프트 유형 | 품질 점수 | 처리 시간 | 비평 출력 (요약) |")
            md_lines.append("| :--- | :---: | :---: | :--- |")

            for p_name, p_res in img_item["prompt_results"].items():
                if "error" in p_res:
                    md_lines.append(f"| **{p_name}** | N/A | {p_res.get('latency_sec', 0)}s | ❌ Error: {p_res['error']} |")
                else:
                    score_str = f"**{p_res.get('quality_score')}**점" if p_res.get('quality_score') is not None else "N/A"
                    critique = p_res.get("critique", "").replace("\n", " ")
                    if len(critique) > 120:
                        critique_summary = critique[:120] + "..."
                    else:
                        critique_summary = critique
                    md_lines.append(f"| **{p_name}** | {score_str} | {p_res.get('latency_sec')}s | {critique_summary} |")

            md_lines.append("\n#### 🔍 프롬프트별 상세비평 비교 (Detail)\n")
            for p_name, p_res in img_item["prompt_results"].items():
                critique_full = p_res.get("critique", "").strip()
                md_lines.append(f"**[{p_name}]** (Score: {p_res.get('quality_score')}):\n")
                md_lines.append(f"> {critique_full}\n")

            md_lines.append("---\n")

    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UniPercept Prompt Benchmark Runner")
    parser.add_argument("--dir", default="/Users/kimbeomjun/Desktop/photo/jpeg", help="Path to photo directory")
    parser.add_argument("--rounds", type=int, default=5, help="Number of rounds (default: 5)")
    parser.add_argument("--per-round", type=int, default=5, help="Images per round (default: 5)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--dry-run", action="store_true", help="Run quick 1 round x 1 image test")
    
    args = parser.parse_args()

    if args.dry_run:
        print("[Benchmark] Executing Dry Run (1 round x 1 image)...")
        run_benchmark(
            photo_dir=args.dir,
            rounds=1,
            images_per_round=1,
            output_json="dry_run_results.json",
            output_md="dry_run_summary.md",
            seed=args.seed
        )
    else:
        run_benchmark(
            photo_dir=args.dir,
            rounds=args.rounds,
            images_per_round=args.per_round,
            output_json="benchmark_results_unipercept.json",
            output_md="benchmark_summary_unipercept.md",
            seed=args.seed
        )
