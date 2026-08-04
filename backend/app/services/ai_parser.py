import json

GEMMA_SYSTEM_PROMPT = (
    "당신은 인디펜던트 사진작가이자 정밀한 시각적 묘사를 전문으로 하는 AI 분석가입니다.\n"
    "제공된 사진과 EXIF 정보를 대조 분석하여 사진의 미학적/기술적 특징을 정밀하게 해부하고, 무드에 맞는 감각적 캡션 묘사 및 관련 검색 태그를 추출하십시오.\n\n"
    "[지침]\n"
    "1. 캡션 묘사: 사진 속 피사체의 구도, 조명, 색조, 텍스처, 공간감을 감각적이고 서정적인 문장으로 작성하십시오.\n"
    "2. 검색 태그 (tags): 사진을 검색할 때 유용한 핵심 사물, 장소, 스타일, 분위기 키워드 (10~15개).\n"
    "3. 사진 전문 용어 (aesthetic_tags): 다음 전문 용어 카테고리를 참고하여, 화면상에 명확히 존재하는 시각 요소만을 엄격히 정밀 검증하여 선택하십시오:\n"
    "   - 조명/빛: 골든 아워, 블루 아워, 역광(Backlight), 사광(Side light), 플레어, 하이키(High-key), 로우키(Low-key), 자연광, 창가 빛, 인공 조명, 플래시, 림라이트(Rim light)\n"
    "   - 기법/효과: 아웃포커싱(얕은 심도), 팬 포커스(깊은 심도), 패닝샷, 장노출, 빛 궤적, 모션 블러, 보케(Bokeh), 매크로/접사, 미니멀리즘\n"
    "   - 톤/무드: 흑백(Monochrome), 비비드, 빈티지, 파스텔, 시네마틱, 하이 콘트라스트, 필름 톤, 세피아, 엠비언트\n"
    "4. SigLIP 2 시각 교차 검증 (Cross-Verification): 제공된 [SigLIP 2 시각 벡터 매칭 후보 키워드]를 참고하십시오. 실제 사진에 해당 시각적 요소가 존재하는지 직접 검증하고, 타당한 키워드는 캡션 및 일반 태그 작성 시 핵심 요소로 적극 반영하되, 실제 사진과 맞지 않는 오탐(False Positive) 키워드는 배제하십시오.\n"
    "5. 예외 규칙 (Negative Prompting):\n"
    "   - EXIF에서 조리개(F-number)가 F5.6 이상이라면 '아웃포커싱'이나 '보케'를 남발하지 마십시오.\n"
    "   - 셔터스피드가 1/1000s 보다 빠르다면 '장노출'이나 '모션 블러'를 절대 사용하지 마십시오.\n"
    "   - 사진에 명확히 보이지 않는 정보(예: 특정 지명, 개인의 이름)는 지어내지 마십시오.\n\n"
    "[출력 형식]\n"
    "오직 아래의 JSON 포맷만 출력하십시오. 마크다운 기호(예: ```json 등)나 부가 설명은 절대 포함하지 마십시오.\n\n"
    "{\"reasoning\": \"추론 내용\", \"caption\": \"고품질 캡션 묘사\", \"tags\": [\"키워드1\", \"키워드2\"], \"aesthetic_tags\": [\"전문용어1\", \"전문용어2\"]}"
)

GEMMA_CRITIQUE_SYSTEM_PROMPT = (
    "당신은 냉철한 안목과 깊은 인디펜던트 사진학 지식을 지닌 세계적인 사진 평론가입니다.\n"
    "제공된 사진의 **실제 시각적 요소(피사체의 포즈·표정, 빛의 하이라이트와 그림자, 색상 조화, 구도 밸런스, 질감)**와 **EXIF 카메라 데이터(조리개, 셔터스피드, ISO, 렌즈 초점거리)**를 유기적으로 대조 분석하십시오. 영혼 없는 형식적 칭찬은 배제하고 실제 시각적 증거에 기반한 3단계 정밀 비평을 작성하십시오.\n\n"
    "[비평 작성 파트]\n"
    "1. 🎨 [시각적 미학 및 EXIF 광학 진단]: 실제 화면 속 피사체의 동작/표정과 빛의 대비(Contrast), 색감의 조화(Color Harmony)가 주는 시각적 전달력을 평가하고, 이것이 카메라 EXIF 세팅(심도, 노이즈, 광학 왜곡, 셔터 감도)과 어떻게 상호작용했는지 심층 진단하십시오.\n"
    "2. 🔍 [구도·빛·피사체 결함 및 한 끗의 아쉬움]: 뻔한 칭찬을 배제하고, 사진의 완성도를 저해하는 시각적 아쉬움(예: 배경과 피사체의 분리감 부족, 시선 분산 요인, 수평/수직 불균형, 그림자 계라 손실, 피사체의 시선/포즈 어색함)을 실제 이미지상에서 정확히 짚어내십시오.\n"
    "3. 💡 [현장 재촬영 & 보정 실전 기술 조언]: 추상적 조언은 피하고, **카메라 조작(F-stop, 셔터스피드, 렌즈 수치)뿐만 아니라 피사체 동선/앵글, 빛을 담는 각도, 라이트룸/보정 시 톤 커브 및 HSL 색상 조정 팁**을 포함한 구체적이고 실전적인 솔루션을 명시하여 제언하십시오.\n\n"
    "전문가다운 냉철하고 명확한 문단으로 작성해주십시오."
)

GEMMA_CRITIQUE_SUMMARY_SYSTEM_PROMPT = (
    "당신은 저명한 사진 평론가이자 포트폴리오 멘토입니다. "
    "제공된 여러 사진의 정밀 비평 및 EXIF 데이터 집합을 심층 분석하여 작가의 총체적인 'AI 사진 비평 종합 요약 리포트'를 작성하십시오.\n\n"
    "[분석 파트]\n"
    "1. 🌟 작가만의 독창적 장점 및 시각적 개성: 공통적으로 나타나는 구도, 색감, 빛의 활용 등 대표적인 미학적 특기를 진단하십시오.\n"
    "2. ⚠️ 고질적인 반복적 실책 및 기술적 보완점: 조리개 선택 습관, ISO 관리, 구도 불균형 등 여러 비평에서 반복 지적된 취약점을 분석하십시오.\n"
    "3. 📷 EXIF 촬영 습관 및 카메라 장비 활용 패턴: 렌즈 사용 경향, 셔터스피드 및 조리개 세팅 패턴 통계를 심층 파악하십시오.\n"
    "4. 🚀 한 단계 도약을 위한 차세대 실전 가이드라인: 작가의 포트폴리오 수준을 프로 레벨로 격상시키기 위한 구체적 훈련 과제와 실전 노하우를 제언하십시오.\n\n"
    "명확하고 정돈된 전문적인 한국어 문단으로 작성해주십시오."
)

GEMMA_TRANSLATE_CRITIQUE_SYSTEM_PROMPT = (
    "당신은 세계적인 사진 비평가 및 예술 감독입니다. 영문 시각 모델(UniPercept)의 기술적 비평 데이터를 바탕으로 품격 있고 체계적인 한국어 사진 비평 리포트를 생성하십시오."
)

UNIPERCEPT_CRITIQUE_PROMPT = (
    "Evaluate this image comprehensively across three domains: 1. Image Aesthetics (IAA), "
    "2. Image Quality (IQA), and 3. Structure & Texture (ISTA). "
    "Provide concise technical reasons for each domain. "
    "At the very end, strictly output scores in format: "
    "'Overall Score: XX/100', 'IAA Score: XX/100', 'IQA Score: XX/100', 'ISTA Score: XX/100'."
)

UNIPERCEPT_IAA_PROMPT = (
    "Focus deeply on Image Aesthetics (IAA). "
    "Analyze composition, lighting, color harmony, subject placement, and visual impact. "
    "Detail how aesthetic choices elevate or weaken the photo. "
    "At the very end, strictly output 'Aesthetic Score: XX/100'."
)

UNIPERCEPT_IQA_PROMPT = (
    "Focus strictly on Image Quality (IQA). "
    "Evaluate technical sharpness, sensor noise, exposure balance, focus accuracy, chromatic aberration, and dynamic range. "
    "Detail technical artifacts. "
    "At the very end, strictly output 'Quality Score: XX/100'."
)

UNIPERCEPT_ISTA_PROMPT = (
    "Focus intently on Structure & Texture (ISTA). "
    "Inspect fine detail resolution, micro-contrast, edge definitions, surface texture rendering, and tonal gradations. "
    "Detail textural fidelity. "
    "At the very end, strictly output 'Structure Score: XX/100'."
)

def format_unipercept_translate_user_prompt(
    raw_en_critique: str,
    scores_dict: dict | None = None,
    quality_score: int | None = None
) -> str:
    score_info = ""
    if scores_dict and isinstance(scores_dict, dict):
        overall = scores_dict.get("overall", quality_score)
        iaa = scores_dict.get("iaa")
        iqa = scores_dict.get("iqa")
        ista = scores_dict.get("ista")
        score_info = (
            f"[📊 4대 앙상블 비평 스코어보드]\n"
            f"- 최종 종합 평점: {overall}점 / 100점\n"
            f"- 🎨 미학 & 구도 (IAA): {iaa}점\n"
            f"- 🔍 화질 & 기술 (IQA): {iqa}점\n"
            f"- 🧱 구조 & 질감 (ISTA): {ista}점\n\n"
        )
    elif quality_score is not None:
        score_info = f"[품질/미학 점수: {quality_score}점 / 100점]\n\n"

    return (
        f"다음은 시각 분석 모델(UniPercept)이 4개 프롬프트 연쇄 앙상블로 생성한 사진의 기술적 영문 비평 데이터입니다:\n\n"
        f"{score_info}{raw_en_critique}\n\n"
        "위 영문 분석 내용을 전문 사진작가의 품격 있고 다정한 어조로 한국어로 번역하고 다음 구체적인 5개 영역으로 정돈하여 불렛포인트로 리포트를 작성해주십시오:\n"
        "1. 📊 종합 품질 & 미학 점수 (상단 스코어보드 수치 반영)\n"
        "2. ✨ 미학 및 구도 (IAA)\n"
        "3. 🔍 화질 및 기술적 품질 (IQA)\n"
        "4. 🎨 구조 및 질감 (ISTA)\n"
        "5. 💡 전문가 총평 및 조언"
    )

def format_exif_text(metadata: dict | None) -> str:
    """Formats EXIF metadata dictionary into human-readable text for VLM context."""
    if not metadata:
        return ""
    return (
        f"\n[EXIF 데이터]\n"
        f"- 카메라: {metadata.get('camera_model', 'N/A')}\n"
        f"- 렌즈: {metadata.get('lens_model', 'N/A')}\n"
        f"- 조리개: F{metadata.get('f_number', 'N/A')}\n"
        f"- 셔터스피드: {metadata.get('shutter_speed', 'N/A')}s\n"
        f"- ISO: {metadata.get('iso', 'N/A')}\n\n"
    )

def format_siglip_hints_text(hints: list[str] | None) -> str:
    """Formats SigLIP 2 candidate visual terms into human-readable text for VLM context."""
    if not hints:
        return ""
    joined_hints = ", ".join(hints)
    return (
        f"[SigLIP 2 시각 벡터 매칭 후보 키워드]\n"
        f"- {joined_hints}\n\n"
    )

def parse_gemma_json_output(output: str) -> dict:
    """
    Safely parses JSON candidate from VLM output text with fallback handling.
    """
    default_result = {"caption": "", "tags": [], "aesthetic_tags": []}
    if not output:
        return default_result
        
    clean_output = output.strip()
    
    # 1. Clean markdown code blocks (e.g. ```json ... ```)
    if "```" in clean_output:
        parts = clean_output.split("```")
        if len(parts) >= 3:
            content = parts[1].strip()
            if content.lower().startswith("json"):
                content = content[4:].strip()
            clean_output = content
            
    # 2. Extract content starting with '{' and ending with '}'
    start_idx = clean_output.find("{")
    end_idx = clean_output.rfind("}")
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_candidate = clean_output[start_idx:end_idx+1]
        try:
            data = json.loads(json_candidate)
            if "caption" in data and "tags" in data:
                return {
                    "caption": str(data["caption"]),
                    "tags": [str(t) for t in (data.get("tags") or [])],
                    "aesthetic_tags": [str(t) for t in (data.get("aesthetic_tags") or [])]
                }
            elif "caption" in data:
                return {"caption": str(data["caption"]), "tags": [], "aesthetic_tags": [str(t) for t in (data.get("aesthetic_tags") or [])]}
            elif "tags" in data:
                return {"caption": "", "tags": [str(t) for t in (data.get("tags") or [])], "aesthetic_tags": [str(t) for t in (data.get("aesthetic_tags") or [])]}
        except Exception as parse_err:
            print(f"[AI Parser] JSON parsing failed: {parse_err}. Raw: {output}", flush=True)
            
    # Fallback parsing strategy for malformed output
    if clean_output and len(clean_output) > 5:
        return {"caption": clean_output, "tags": [], "aesthetic_tags": []}
        
    return default_result
