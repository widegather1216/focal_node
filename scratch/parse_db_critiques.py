import os
import sys
import json
import sqlite3
import re
from collections import Counter

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

db_path = os.path.expanduser("~/.config/focal_node_dev/focal_node.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    SELECT 
        i.id, 
        i.file_name, 
        i.file_path, 
        a.critique, 
        a.critique_updated_at,
        a.caption,
        a.tags,
        a.aesthetic_tags,
        m.camera_model,
        m.lens_model,
        m.f_number,
        m.shutter_speed,
        m.iso,
        m.focal_length
    FROM images i
    JOIN ai_analysis a ON i.id = a.image_id
    LEFT JOIN image_metadata m ON i.id = m.image_id
    WHERE a.critique IS NOT NULL AND a.critique != ''
    ORDER BY a.critique_updated_at DESC
""")
db_rows = cur.fetchall()

print(f"=== DEV DB Critique Records: {len(db_rows)} ===")

# Also load previous dump if exists
prev_dump_path = "scratch/all_dev_db_critiques.json"
prev_records = []
if os.path.exists(prev_dump_path):
    with open(prev_dump_path, "r", encoding="utf-8") as f:
        prev_records = json.load(f)
    print(f"=== Previous Dump Records: {len(prev_records)} ===")

def parse_critique_structure(text):
    data = {
        "raw_text": text,
        "char_len": len(text),
        "word_len": len(text.split()),
        "has_sb_header": "[📊" in text or "6-Way 앙상블" in text or "4대 앙상블" in text,
        "sb_overall": None,
        "sb_iaa": None,
        "sb_iqa": None,
        "sb_ista": None,
        "body_scores": {},
        "sections": [],
        "duplicated_sb": text.count("앙상블 비평 스코어보드") > 1,
        "cliche_phrases": [],
        "exif_mentions": [],
        "technical_terms": []
    }
    
    # Extract SB scores
    m_ov = re.search(r"최종 종합 평점:\s*(\d+(?:\.\d+)?)\s*점", text)
    if m_ov: data["sb_overall"] = float(m_ov.group(1))
    
    m_iaa = re.search(r"미학 & 구도 \(IAA\):\s*(\d+(?:\.\d+)?)\s*점", text)
    if m_iaa: data["sb_iaa"] = float(m_iaa.group(1))
    
    m_iqa = re.search(r"화질 & 기술 \(IQA\):\s*(\d+(?:\.\d+)?)\s*점", text)
    if m_iqa: data["sb_iqa"] = float(m_iqa.group(1))
    
    m_ista = re.search(r"구조 & 질감 \(ISTA\):\s*(\d+(?:\.\d+)?)\s*점", text)
    if m_ista: data["sb_ista"] = float(m_ista.group(1))

    # Detect sections
    if "종합 품질 & 미학 점수" in text or "종합 평가" in text:
        data["sections"].append("1. 종합 평가")
    if "미학 및 구도 요약" in text:
        data["sections"].append("2. 미학 및 구도")
    if "화질 및 기술적 품질 요약" in text:
        data["sections"].append("3. 화질 및 기술")
    if "구조 및 질감 요약" in text:
        data["sections"].append("4. 구조 및 질감")
    if "[비평 작성 파트]" in text or "광학 진단" in text:
        data["sections"].append("Gemma 원본 3단계 포맷")

    # Cliché phrases check
    cliches = [
        "걸작", "흠잡을 데 없는", "완벽함 그 자체", "완벽함을 넘어선", "경지를 초월",
        "비평적 경계를 초월", "시대를 초월한", "말로 표현할 수 없을", "신의 한 수",
        "모범적인 실행", "탁월한 명료도", "예술적 심오함"
    ]
    for c in cliches:
        if c in text:
            data["cliche_phrases"].append(c)

    # EXIF mentions in critique body
    for kw in ["조리개", "셔터", "ISO", "렌즈", "초점거리", "화각", "F/", "f/", "NIKON", "Z50"]:
        if kw in text:
            data["exif_mentions"].append(kw)

    # Technical terms
    terms = [
        "선명도", "샤프니스", "다이내믹 레인지", "색수차", "노이즈", "미세 대비",
        "유도선", "키아로스쿠로", "하이라이트", "그림자", "피사계 심도", "보케",
        "톤 계조", "원근법", "시각적 균형", "구도", "텍스처", "표면 질감"
    ]
    for t in terms:
        if t in text:
            data["technical_terms"].append(t)

    return data

parsed_db = []
for r in db_rows:
    item = {
        "id": r[0],
        "file_name": r[1],
        "file_path": r[2],
        "updated_at": str(r[4]),
        "exif": {
            "camera": r[8], "lens": r[9], "f_number": r[10],
            "shutter_speed": r[11], "iso": r[12], "focal_length": r[13]
        },
        "analysis": parse_critique_structure(r[3])
    }
    parsed_db.append(item)

print(f"\nParsed {len(parsed_db)} DB records.")
for i, p in enumerate(parsed_db):
    a = p["analysis"]
    print(f"\n[{i+1}] {p['file_name']} (Updated: {p['updated_at']})")
    print(f"    Length: {a['char_len']} chars, {a['word_len']} words")
    print(f"    Scores -> Overall: {a['sb_overall']}, IAA: {a['sb_iaa']}, IQA: {a['sb_iqa']}, ISTA: {a['sb_ista']}")
    print(f"    Sections: {', '.join(a['sections'])}")
    print(f"    Duplicated SB Header: {a['duplicated_sb']}")
    print(f"    Cliché phrases ({len(a['cliche_phrases'])}): {', '.join(a['cliche_phrases'])}")
    print(f"    EXIF Mentions ({len(a['exif_mentions'])}): {', '.join(a['exif_mentions'])}")
    print(f"    Tech Terms ({len(a['technical_terms'])}): {', '.join(a['technical_terms'])}")

# Save parsed DB summary
with open("scratch/db_critiques_parsed_summary.json", "w", encoding="utf-8") as f:
    json.dump(parsed_db, f, ensure_ascii=False, indent=2)

print("\nSummary saved to scratch/db_critiques_parsed_summary.json")
