import os
import sys
import json
import re
from collections import Counter

# Load current dev DB critiques
with open("scratch/current_dev_db_critiques_full.json", "r", encoding="utf-8") as f:
    current_db = json.load(f)

# Load previous dump critiques
with open("scratch/all_dev_db_critiques.json", "r", encoding="utf-8") as f:
    prev_dump = json.load(f)

print(f"Loaded {len(current_db)} current DB records and {len(prev_dump)} previous dump records.")

# Merge and index
all_critiques = []
for item in current_db:
    all_critiques.append({
        "source": "Current DB (6-Way Engine)",
        "file_name": item["file_name"],
        "camera": item.get("camera_model"),
        "lens": item.get("lens_model"),
        "f_number": item.get("f_number"),
        "shutter_speed": item.get("shutter_speed"),
        "iso": item.get("iso"),
        "focal_length": item.get("focal_length"),
        "critique": item["critique"],
        "updated_at": item["critique_updated_at"]
    })

for item in prev_dump:
    # Check if already present
    exists = any(c["file_name"] == item["file_name"] and c["source"] == "Current DB (6-Way Engine)" for c in all_critiques)
    all_critiques.append({
        "source": "Historical DB (4-Way Benchmark)",
        "file_name": item["file_name"],
        "camera": item.get("camera_model"),
        "lens": item.get("lens_model"),
        "f_number": item.get("f_number"),
        "shutter_speed": item.get("shutter_speed"),
        "iso": item.get("iso"),
        "focal_length": None,
        "critique": item["critique"],
        "updated_at": item.get("updated_at")
    })

def analyze_text(entry):
    text = entry["critique"]
    
    # 1. Scoreboard Extraction
    sb_scores = {}
    m_ov = re.search(r"최종 종합 평점:\s*(\d+(?:\.\d+)?)\s*점", text)
    if m_ov: sb_scores["overall"] = float(m_ov.group(1))
    m_iaa = re.search(r"미학 & 구도 \(IAA\):\s*(\d+(?:\.\d+)?)\s*점", text)
    if m_iaa: sb_scores["iaa"] = float(m_iaa.group(1))
    m_iqa = re.search(r"화질 & 기술 \(IQA\):\s*(\d+(?:\.\d+)?)\s*점", text)
    if m_iqa: sb_scores["iqa"] = float(m_iqa.group(1))
    m_ista = re.search(r"구조 & 질감 \(ISTA\):\s*(\d+(?:\.\d+)?)\s*점", text)
    if m_ista: sb_scores["ista"] = float(m_ista.group(1))
    
    # 2. Section Partitioning
    sections = {}
    sec_patterns = [
        ("scoreboard", r"(\[📊.*?\](?:.*?\n\n|.*?---\n\n))"),
        ("section_1_overview", r"(?:\*{0,3}1\.\s*📊\s*종합 품질 & 미학 점수\*{0,3}|### 1\..*?)(.*?)(?=\*{0,3}2\.|\n\n### 2|\Z)"),
        ("section_2_aesthetics", r"(?:\*{0,3}2\.\s*✨\s*미학 및 구도 요약\*{0,3}|### 2\..*?)(.*?)(?=\*{0,3}3\.|\n\n### 3|\Z)"),
        ("section_3_quality", r"(?:\*{0,3}3\.\s*🔍\s*화질 및 기술적 품질 요약\*{0,3}|### 3\..*?)(.*?)(?=\*{0,3}4\.|\n\n### 4|\Z)"),
        ("section_4_structure", r"(?:\*{0,3}4\.\s*🧱\s*구조 및 질감 요약\*{0,3}|### 4\..*?)(.*?)(?=\Z)"),
    ]
    
    for name, pat in sec_patterns:
        m = re.search(pat, text, re.DOTALL)
        if m:
            sections[name] = m.group(1).strip()
            
    # 3. Linguistic & Lexical Analysis
    words = re.findall(r'[가-힣a-zA-Z0-9]+', text)
    korean_nouns = re.findall(r'[가-힣]{2,}', text)
    
    # Check for formatting anomalies
    anomalies = []
    if text.count("앙상블 비평 스코어보드") > 1:
        anomalies.append("중복 스코어보드 헤더")
    if re.search(r"(?:XX/XX|XX/1|19/0|/ 1|\b1\s*/\b|Score:\s*1\b)", text):
        anomalies.append("원문 점수 파싱 왜곡 잔재 (XX/XX, 19/0, / 1 등)")
    if "(상단 스코어보드 수치 명시)" in text:
        anomalies.append("프롬프트 지침 메타 텍스트 노출 ((상단 스코어보드 수치 명시))")
    if "걸작" in text or "완벽함 그 자체" in text or "초월" in text:
        anomalies.append("극단적 찬사/미사여구 사용")
    if "에어컨 장치:" in text or "재질:" in text or "평면 윤곽:" in text:
        anomalies.append("UniPercept ISTA 구조적 템플릿(재질/윤곽/추론) 직역")

    return {
        "file_name": entry["file_name"],
        "source": entry["source"],
        "char_len": len(text),
        "word_count": len(words),
        "sb_scores": sb_scores,
        "sections_found": list(sections.keys()),
        "section_lengths": {k: len(v) for k, v in sections.items()},
        "anomalies": anomalies,
        "korean_word_count": len(korean_nouns)
    }

results = [analyze_text(e) for e in all_critiques]

print("\n=== AGGREGATED METRICS ===")
print(f"Total critiques evaluated: {len(results)}")
print(f"Current 6-Way critiques: {sum(1 for r in results if 'Current' in r['source'])}")
print(f"Historical 4-Way critiques: {sum(1 for r in results if 'Historical' in r['source'])}")

avg_len_curr = sum(r["char_len"] for r in results if "Current" in r["source"]) / max(1, sum(1 for r in results if "Current" in r["source"]))
avg_len_prev = sum(r["char_len"] for r in results if "Historical" in r["source"]) / max(1, sum(1 for r in results if "Historical" in r["source"]))

print(f"Avg Char Length (Current 6-Way): {avg_len_curr:.1f} chars")
print(f"Avg Char Length (Historical 4-Way): {avg_len_prev:.1f} chars")

all_anomalies = [a for r in results for a in r["anomalies"]]
anomaly_counts = Counter(all_anomalies)
print("\n=== ANOMALY FREQUENCY ===")
for a, c in anomaly_counts.items():
    print(f"- {a}: {c}건 ({c/len(results)*100:.1f}%)")

# Score distribution
scores_curr = [r["sb_scores"] for r in results if "Current" in r["source"] and r["sb_scores"]]
print("\n=== CURRENT 6-WAY SCORES SUMMARY ===")
for sc in scores_curr:
    print(f"Overall: {sc.get('overall')}, IAA: {sc.get('iaa')}, IQA: {sc.get('iqa')}, ISTA: {sc.get('ista')}")

with open("scratch/deep_critique_analysis_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\nSaved full deep analysis to scratch/deep_critique_analysis_result.json")
