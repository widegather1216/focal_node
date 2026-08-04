#!/usr/bin/env python3
"""
Generate Korean Benchmark Summary Report from benchmark_results_unipercept.json
Uses Gemma Adapter if available or clean translation parser to translate UniPercept raw English critiques into Korean.
"""

import os
import sys
import json
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
BACKEND_APP_DIR = os.path.join(PROJECT_ROOT, "backend", "app")
if BACKEND_APP_DIR not in sys.path:
    sys.path.insert(0, BACKEND_APP_DIR)

def translate_phrase_ko(text: str) -> str:
    """Translates common UniPercept visual evaluation terms into natural Korean."""
    if not text:
        return ""
    
    # Simple regex rules & term replacements for clear Korean reading
    replacements = [
        (r"### Image Aesthetic Quality \(IAA\)", "### 🎨 미학 및 구도 품질 (IAA)"),
        (r"### Image Quality \(IQA\)", "### 🔍 화질 및 기술적 품질 (IQA)"),
        (r"### Structure & Texture \(ISTA\)", "### 🧱 구조 및 질감 (ISTA)"),
        (r"Overall Score:\s*(\d+)/100", r"종합 점수: \1점 / 100점"),
        (r"Overall aesthetic merit:", "종합 미학 평점:"),
        (r"Overall quality merit reflects", "종합 화질 및 디테일 평점:"),
        (r"In summary:", "요약:"),
        (r"The image presents", "이 사진은"),
        (r"The image demonstrates", "이 사진은"),
        (r"The image excelsingly captures", "이 사진은 매우 훌륭하게"),
        (r"moderate visual impact", "적절한 시각적 인상"),
        (r"strong visual impact", "강렬한 시각적 임팩트"),
        (r"everyday elements", "일상적인 요소들"),
        (r"subdued lighting", "은은하고 차분한 조명"),
        (r"urban alleyway", "도시 골목길"),
        (r"concrete stairs", "콘크리트 계단"),
        (r"scattered debris", "흩어진 파편 및 흔적들"),
        (r"sharp focus", "선명한 초점"),
        (r"architectural details", "건축적 디테일"),
        (r"exposure balances shadows and highlights", "명암과 하이라이트의 균형 잡힌 노출"),
        (r"micro-contrast", "마이크로 콘트라스트(미세 대비)"),
        (r"chromatic aberration", "색수차"),
        (r"sensor noise", "센서 노이즈"),
        (r"tonal gradation", "톤 계조 표현"),
        (r"textural fidelity", "질감 묘사의 충실도"),
        (r"composition", "구도"),
        (r"lighting", "광선 및 조명"),
        (r"color harmony", "색채 조화"),
        (r"subject placement", "피사체 배치"),
    ]
    
    res = text
    for pattern, repl in replacements:
        res = re.sub(pattern, repl, res, flags=re.IGNORECASE)
    
    return res

def main():
    json_path = os.path.join(PROJECT_ROOT, "benchmark_results_unipercept.json")
    output_ko_md = os.path.join(PROJECT_ROOT, "benchmark_summary_unipercept_ko.md")

    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    md_lines = []
    md_lines.append("# 🇰🇷 UniPercept 프롬프트 4종 비교 벤치마크 결과 리포트 (한국어 번역본)\n")
    md_lines.append(f"- **총 실행 회차**: {data['total_rounds']}회차 (회차당 5장 무작위, 총 {data['total_images']}장)")
    md_lines.append(f"- **총 추론 수행 횟수**: {data['total_evaluations']}회 (25장 x 4개 프롬프트)")
    md_lines.append(f"- **총 소요 시간**: {data['total_time_sec']:.1f}초\n")
    md_lines.append("---\n")

    for round_item in data["rounds_data"]:
        r_num = round_item["round"]
        md_lines.append(f"## 📌 Round {r_num}\n")

        for img_item in round_item["images"]:
            file_name = img_item["file_name"]
            md_lines.append(f"### 📷 이미지: `{file_name}`\n")
            md_lines.append("| 프롬프트 유형 | 품질 점수 | 처리 시간 | 비평 출력 요약 (한국어) |")
            md_lines.append("| :--- | :---: | :---: | :--- |")

            for p_name, p_res in img_item["prompt_results"].items():
                if "error" in p_res:
                    md_lines.append(f"| **{p_name}** | N/A | {p_res.get('latency_sec', 0)}s | ❌ 오류 발생: {p_res['error']} |")
                else:
                    score_str = f"**{p_res.get('quality_score')}**점" if p_res.get('quality_score') is not None else "N/A"
                    critique_en = p_res.get("critique", "").replace("\n", " ")
                    critique_ko = translate_phrase_ko(critique_en)
                    critique_summary = critique_ko[:120] + "..." if len(critique_ko) > 120 else critique_ko
                    md_lines.append(f"| **{p_name}** | {score_str} | {p_res.get('latency_sec')}s | {critique_summary} |")

            md_lines.append("\n#### 🔍 프롬프트별 상세 한국어 비평 비교\n")
            for p_name, p_res in img_item["prompt_results"].items():
                critique_full_en = p_res.get("critique", "").strip()
                critique_full_ko = translate_phrase_ko(critique_full_en)
                score_val = p_res.get('quality_score')
                score_disp = f"{score_val}점" if score_val is not None else "N/A"
                md_lines.append(f"**[{p_name}]** (점수: {score_disp}):\n")
                md_lines.append(f"> {critique_full_ko}\n")

            md_lines.append("---\n")

    with open(output_ko_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Successfully generated Korean summary report at {output_ko_md}")

if __name__ == "__main__":
    main()
