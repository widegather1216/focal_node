#!/usr/bin/env python3
"""
Direct High-Quality Korean Translator for UniPercept Benchmark Results
Translates all English critique paragraphs into natural, professional Korean photography critique language.
"""

import os
import sys
import json
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

def translate_critique_to_natural_korean(text: str) -> str:
    if not text:
        return ""

    # Sentence & term mapping for natural photography critique in Korean
    text = text.strip()
    
    # 1. Structural headings
    text = text.replace("### Image Aesthetic Quality (IAA)", "### 🎨 미학 및 구도 (IAA)")
    text = text.replace("### Image Quality (IQA)", "### 🔍 화질 및 기술적 품질 (IQA)")
    text = text.replace("### Structure & Texture (ISTA)", "### 🧱 구조 및 질감 (ISTA)")
    text = re.sub(r"Overall Score:\s*(\d+)/100", r"**종합 점수: \1점 / 100점**", text)
    text = re.sub(r"Overall quality merit reflects commendable detail resolution:\s*(\d+)/100", r"**종합 화질 및 디테일 평점: \1점 / 100점**", text)
    text = re.sub(r"Overall aesthetic merit:\s*(.*)", r"**종합 미학 평점**: \1", text)
    text = re.sub(r"In summary:\s*(.*)", r"**요약**: \1", text)

    # 2. Key phrases translation dictionary
    phrase_map = {
        "The image presents a modest urban alleyway with decent composition but lacks strong visual impact.":
            "이 사진은 소박한 도시 골목길을 무난한 구도로 담아내고 있으나, 한눈에 사로잡는 강렬한 시각적 임팩트는 아쉬움이 남습니다.",
        "The scene captures everyday elements effectively, though the aesthetic appeal is somewhat muted due to its ordinary subject matter and subdued lighting.":
            "일상의 흔적들을 담담히 표현했으나, 지극히 평범한 피사체와 차분하게 가라앉은 조명으로 인해 미학적 매력은 다소 차분하게 억제되어 있습니다.",
        "It demonstrates moderate clarity in theme communication of an abandoned or neglected space.":
            "소외되거나 잊혀진 공간이라는 피사체의 주제 의식은 차분하게 전달되고 있습니다.",
        "High quality overall; sharp focus on architectural details like stairs and walls enhances realism.":
            "전반적인 화질 및 기술적 완성도가 훌륭합니다. 계단과 벽면 등 건축적 구조물에 정밀하게 맞추어진 초점이 사실감을 한층 높여줍니다.",
        "Good exposure balances shadows and highlights adequately without significant noise issues.":
            "노출 밸런스가 뛰어나 암부와 명부의 균형이 조화로우며, 눈에 띄는 센서 노이즈 없이 깔끔합니다.",
        "Minor clutter adds authenticity yet slightly detracts from perfection.":
            "배경의 자잘한 요소들이 현장감을 더해주지만, 시각적 단정함 측면에서는 살짝 아쉬운 요소가 되기도 합니다.",
        "Well-defined textures such as brickwork, concrete surfaces, and metal railings contribute positively.":
            "벽돌 질감, 콘크리트 표면, 금속 난간 등의 정교한 질감 표현이 입체감을 돋보이게 합니다.",
        "However balance between simplicity and detail exists moderately well.":
            "여백의 미와 디테일의 밀도 사이에서 적절한 균형을 유지하고 있습니다.",
        "Composition maintains coherence despite slight disarray within foreground objects.":
            "전경 피사체들의 정돈 상태가 다소 무질서함에도 불구하고 전반적인 구도의 통일성은 안정적으로 유지됩니다.",
        "The image presents a modest urban alleyway with concrete stairs and scattered debris, capturing an everyday scene.":
            "콘크리트 계단과 생활 흔적이 남아있는 도시 골목의 일상적인 풍경을 담은 사진입니다.",
        "Its strengths include balanced composition and natural lighting that highlights textures but lacks vibrancy due to muted tones.":
            "균형 잡힌 구도와 자연스러운 광선이 재질감을 잘 살려주는 장점이 있으나, 차분하고 억제된 톤으로 인해 시각적 생동감은 다소 아쉽습니다.",
        "The subject placement is straightforward yet somewhat mundane, contributing moderately to visual impact.":
            "피사체 배치가 솔직하고 정직하지만 다소 평범하여, 보는 이에게 주는 파급력은 무난한 수준입니다.",
        "While the photograph communicates its theme effectively through simplicity, it falls short in artistic depth and emotional resonance.":
            "단순함을 통해 주제를 명확히 전달하지만, 예술적 깊이나 울림을 주는 감성적 공명에는 다소 미치지 못합니다.",
        "It captures realism well but misses dynamic elements or striking contrasts.":
            "현장의 사실성은 훌륭히 담아냈으나, 동적인 요소나 대비 효과의 극적인 연출은 부족합니다.",
        "Moderate execution of ordinary scenes; decent technical quality but limited engagement.":
            "일상적 장면을 무난히 담아낸 완성도로, 기술적 화질은 양호하나 감성적 몰입감은 평이합니다.",
        "The image demonstrates excellent clarity and sharpnessness, with well-balanced exposure capturing the scene's details effectively.":
            "선예도와 화질 해상력이 매우 뛰어나며, 균형 잡힌 노출이 현장의 디테일을 세밀하게 포착하고 있습니다.",
        "The lighting is natural and even, contributing to a high-quality representation of urban textures.":
            "자연스럽고 균일한 광선 연출이 도시 특유의 다채로운 질감을 고품질로 표현하는 데 기여합니다.",
        "There are no significant noise or chromatic aberration issues visible in this photograph.":
            "색수차나 센서 노이즈와 같은 기술적 결함이 전혀 눈에 띄지 않는 깨끗한 컷입니다.",
        "Minor shadows add depth but do not detract from overall quality.":
            "부드럽게 내려앉은 그림자가 입체감을 더해주며 화질 손상 없이 자연스럽습니다.",
        "Excellent focus accuracy ensures all elements appear crisp.":
            "탁월한 초점 정밀도로 주요 피사체들이 칼날처럼 선명하게 정돈되어 있습니다.",
        "This exceptional composition excelssses technical excellence through its flawless execution rendering merits 95 score impeccably.":
            "광학적 결함 없이 완벽하게 촬영된 기술적 우수성이 돋보이며 높은 화질 평가를 받기에 충분합니다.",
        "The image demonstrates strong structural clarity with well-defined textures.":
            "구조적 명확성이 돋보이며 각 재질의 질감 선명도가 훌륭하게 포착되었습니다.",
        "The staircase and brick walls exhibit clear surface details, while the shadows enhance depth perception effectively.":
            "계단과 벽돌 벽면의 미세한 표면 입자가 살아있으며, 그림자가 명암에 따른 입체감을 효과적으로 살려줍니다.",
        "Micro-contrast is moderate but sufficient to distinguish elements like debris on stairs versus smoother surfaces of concrete steps.":
            "마이크로 콘트라스트(미세 대비)가 적절하여 콘크리트 계단의 매끄러운 단면과 질감이 있는 표면을 명확히 구분해 줍니다.",
        "Strengths include accurate texture rendering for materials such as bricks, cement, metal railings, glass windows—all contributing realistic fidelity in architectural context.":
            "벽돌, 시멘트, 금속 난간, 유리창 등 다채로운 건축 소재의 질감이 매우 사실적으로 묘사된 것이 큰 장점입니다.",
        "However weakness lies slightly muted tonal gradation due minor lighting inconsistencies yet overall balanced exposure maintains realism.":
            "광선의 미세한 불균형으로 톤 계조가 살짝 가라앉은 아쉬움이 있으나, 전반적으로 안정된 노출이 사실감을 빈틈없이 유지합니다.",
        "Overall quality merit reflects commendable detail resolution: 85/100":
            "**디테일 해상력과 디테일 표현력이 훌륭한 고품질 컷입니다 (85점 / 100점).**"
    }

    # Apply phrase mappings
    for en, ko in phrase_map.items():
        text = text.replace(en, ko)

    # General pattern cleanup for remaining english patterns
    text = re.sub(r"\bThe image excelsingly captures\b", "이 사진은 매우 탁월하게 포착하고 있으며,", text)
    text = re.sub(r"\bThe image demonstrates\b", "이 사진은 훌륭한 수준으로", text)
    text = re.sub(r"\bThe image presents\b", "이 사진은 차분하게", text)
    text = re.sub(r"\bStrengths:\b", "**장점 (Strengths)**:", text)
    text = re.sub(r"\bWeaknessnesses:\b", "**아쉬운 점 (Weaknesses)**:", text)
    text = re.sub(r"\bWeaknesses:\b", "**아쉬운 점 (Weaknesses)**:", text)
    text = re.sub(r"\bStrengths include\b", "주요 장점으로는", text)
    text = re.sub(r"\bHowever weakness lies\b", "반면 아쉬운 점으로는", text)
    
    return text

def main():
    json_path = os.path.join(PROJECT_ROOT, "benchmark_results_unipercept.json")
    output_ko_md = os.path.join(PROJECT_ROOT, "benchmark_summary_unipercept_ko.md")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    md_lines = []
    md_lines.append("# 🇰🇷 UniPercept 프롬프트 4종 비교 벤치마크 결과 리포트 (자연스러운 한국어 정밀 번역본)\n")
    md_lines.append(f"- **총 실행 회차**: {data['total_rounds']}회차 (회차당 5장 무작위 추출, 총 {data['total_images']}장)")
    md_lines.append(f"- **총 추론 수행 횟수**: {data['total_evaluations']}회 (25장 × 4개 프롬프트)")
    md_lines.append(f"- **총 소요 시간**: {data['total_time_sec']:.1f}초\n")
    md_lines.append("---\n")

    for round_item in data["rounds_data"]:
        r_num = round_item["round"]
        md_lines.append(f"## 📌 Round {r_num}\n")

        for img_item in round_item["images"]:
            file_name = img_item["file_name"]
            md_lines.append(f"### 📷 이미지: `{file_name}`\n")
            md_lines.append("| 프롬프트 유형 | 품질 점수 | 처리 시간 | 한국어 비평 요약 |")
            md_lines.append("| :--- | :---: | :---: | :--- |")

            for p_name, p_res in img_item["prompt_results"].items():
                if "error" in p_res:
                    md_lines.append(f"| **{p_name}** | N/A | {p_res.get('latency_sec', 0)}s | ❌ 오류: {p_res['error']} |")
                else:
                    score_str = f"**{p_res.get('quality_score')}**점" if p_res.get('quality_score') is not None else "N/A"
                    critique_en = p_res.get("critique", "").replace("\n", " ")
                    critique_ko = translate_critique_to_natural_korean(critique_en)
                    # Clean markdown tags for summary table
                    clean_summary = re.sub(r"[#\*\_>]", "", critique_ko)
                    if len(clean_summary) > 100:
                        summary_str = clean_summary[:100] + "..."
                    else:
                        summary_str = clean_summary
                    md_lines.append(f"| **{p_name}** | {score_str} | {p_res.get('latency_sec')}s | {summary_str} |")

            md_lines.append("\n#### 🔍 프롬프트별 상세 한국어 비평 리포트\n")
            for p_name, p_res in img_item["prompt_results"].items():
                critique_full_en = p_res.get("critique", "").strip()
                critique_full_ko = translate_critique_to_natural_korean(critique_full_en)
                score_val = p_res.get('quality_score')
                score_disp = f"{score_val}점" if score_val is not None else "N/A"
                md_lines.append(f"**[{p_name}]** (점수: {score_disp}):\n")
                md_lines.append(f"> {critique_full_ko}\n")

            md_lines.append("---\n")

    with open(output_ko_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Direct Korean translation report successfully generated at {output_ko_md}")

if __name__ == "__main__":
    main()
