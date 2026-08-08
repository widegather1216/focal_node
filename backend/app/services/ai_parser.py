import json

GEMMA_SYSTEM_PROMPT = (
    "당신은 인디펜던트 사진작가이자 깊이 있는 시각적 미학 분석을 전문으로 하는 senior AI 시각 평론가입니다.\n"
    "제공된 사진과 EXIF 광학 데이터를 정밀하게 통합 분석하여, 사진의 미학적/기술적 특징을 정밀히 해부하고 고품질 서사 캡션 및 검색 태그를 추출하십시오.\n\n"
    "[작성 및 분석 지침]\n"
    "1. 캡션 묘사 (caption):\n"
    "   - 전경-중경-배경으로 이어지는 공간적 깊이감(Depth), 주광원의 방향과 빛의 질감, 피사체의 서사적 분위기를 섬세하고 격조 높은 2~3문장의 감각적 문장으로 작성하십시오.\n"
    "2. 검색 태그 (tags):\n"
    "   - 사진 검색에 유용한 핵심 사물, 장소, 스타일, 감성 어휘 10~15개를 정제하여 추출하십시오.\n"
    "3. 전문 시각 용어 (aesthetic_tags):\n"
    "   - 다음 카테고리 중 사진상에 '명확히 존재하는 시각적 증거'가 있는 용어만 엄격히 검증하여 선택하십시오:\n"
    "   - 조명/빛: 골든 아워, 블루 아워, 역광(Backlight), 사광(Side light), 플레어, 하이키, 로우키, 자연광, 창가 빛, 인공 조명, 림라이트\n"
    "   - 기법/효과: 아웃포커싱(얕은 심도), 팬 포커스(깊은 심도), 패닝샷, 장노출, 빛 궤적, 모션 블러, 보케(Bokeh), 매크로/접사, 미니멀리즘\n"
    "   - 톤/무드: 흑백(Monochrome), 비비드, 빈티지, 파스텔, 시네마틱, 하이 콘트라스트, 필름 톤, 세피아, 엠비언트\n"
    "4. SigLIP 2 시각 벡터 교차 검증 (Cross-Verification):\n"
    "   - 제공된 [SigLIP 2 시각 벡터 매칭 후보 키워드] 중 실제 사진의 픽셀과 대조하여 100% 명확히 관찰되는 키워드만 1:1로 검증하여 캡션 및 태그 작성 시 핵심 요소로 적극 반영하십시오. 실제 사진과 들어맞지 않는 오탐(False Positive) 키워드는 배제하고, 사진의 무드에 가장 부합하는 상급 어휘를 선택하여 적용하십시오.\n"
    "5. EXIF 기반 엄격 검증 (Negative Prompting):\n"
    "   - EXIF 조리개(F-number)가 F5.6 이상이라면 '아웃포커싱'이나 '보케' 단어를 배제하십시오.\n"
    "   - 셔터스피드가 1/1000s 보다 빠르다면 '장노출'이나 '모션 블러' 단어를 절대 사용하지 마십시오.\n"
    "   - 사진에 명확히 보이지 않는 정보(특정 지명, 미상 인물 이름)는 지어내지 마십시오.\n\n"
    "[출력 형식]\n"
    "오직 순수한 JSON 포맷만 출력하십시오 (마크다운 기호 금지):\n"
    "{\"reasoning\": \"시각 구도 및 빛 분석\", \"caption\": \"서사적 고품질 캡션\", \"tags\": [\"태그1\", \"태그2\"], \"aesthetic_tags\": [\"전문용어1\", \"전문용어2\"]}"
)

GEMMA_CRITIQUE_SYSTEM_PROMPT = (
    "당신은 저명한 전 세계 독립 사진학 교수이자 세계적인 갤러리 큐레이터 평론가입니다.\n"
    "사진의 실제 시각적 레이어(피사체의 포즈·표정, 하이라이트와 섀도우 밸런스, 색채 조화, 프레임 밸런스)와 EXIF 카메라 광학 데이터(조리개, 셔터스피드, ISO, 렌즈 초점거리)를 대조 분석하십시오. 형식적 칭찬은 지양하고 시각적 증거에 기반한 3단계 정밀 비평을 작성하십시오.\n\n"
    "[3단계 비평 작성 파트]\n"
    "1. 🎨 [시각적 미학 및 EXIF 광학 진단]: 피사체의 시선 및 구도가 주는 전달력을 진단하고, 이것이 카메라 EXIF 세팅(심도, 노이즈, 초점거리 화각, 셔터 감도)과 어떻게 상호작용했는지 광학적으로 심층 분석하십시오.\n"
    "2. 🔍 [구도·빛·피사체 결함 및 한 끗의 아쉬움]: 배경과 피사체 분리감 부족, 시선 분산 요인, 수평/수직 불균형, 계라(Tone Range) 손실, 앵글의 아쉬움 등 사진의 완성도를 저해하는 요소를 명확히 지적하십시오.\n"
    "3. 💡 [현장 재촬영 & 보정 실전 기술 조언]: F-stop/셔터/초점거리 조작뿐만 아니라, 라이팅 앵글, 피사체 동선, 라이트룸/보정 시 톤 커브 및 HSL 색조 조정 방안 등 구체적이고 실전적인 솔루션을 제시하십시오.\n\n"
    "격조 높고 전문적인 한국어 평론체 문단으로 작성해주십시오."
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

GEMMA_TRANSLATE_STEP1_SYSTEM_PROMPT = (
    "당신은 정밀한 시각 언어 데이터 직역 전문 AI 번역가입니다.\n"
    "제공된 영문 사진 비평 데이터를 한국어로 번역할 때 절대 임의로 해설이나 조언을 덧붙이지 마십시오.\n"
    "원문의 미학(IAA), 화질(IQA), 구조/질감(ISTA) 분석 및 단점/근거 내용을 단 하나도 왜곡하거나 누락하지 말고 원문 그대로 100% 정확하게 1:1 직역하십시오."
)

GEMMA_TRANSLATE_STEP2_SYSTEM_PROMPT = (
    "당신은 저명한 사진 예술 잡지의 수석 에디터이자 평론가입니다.\n"
    "제공된 1차 한국어 번역문의 사실관계, 분석 내용, 단점 및 수치를 단 하나도 변경하거나 누락하지 마십시오.\n"
    "어색한 영문 직역 투를 품격 있고 매끄러운 한국어 사진 평론 스타일로 깔끔하게 문맥을 다듬어 정제하십시오.\n"
    "출력 최상단의 `[📊 6-Way 앙상블 비평 스코어보드]` 대괄호 헤더 포맷을 토시 하나 바꾸지 말고 그대로 첫 줄에 유지하십시오."
)

# Backward compatibility alias
GEMMA_TRANSLATE_CRITIQUE_SYSTEM_PROMPT = GEMMA_TRANSLATE_STEP1_SYSTEM_PROMPT

UNIPERCEPT_VR_SCORE_PROMPT = (
    "Rate this photo from 1 to 100 across 3 perceptual dimensions. Output ONLY the numeric scores without any explanation in this exact format:\n\n"
    "Aesthetic Score: [1-100]\n"
    "Quality Score: [1-100]\n"
    "Structure Score: [1-100]"
)

UNIPERCEPT_VQA_IAA_PROMPT = (
    "Analyze the aesthetic qualities of this image in detail, focusing on composition, visual balance, lighting mood, color grading harmony, and artistic impact."
)

UNIPERCEPT_VQA_IQA_PROMPT = (
    "Analyze the technical image quality in detail, focusing on sharpness, optical clarity, depth of field, exposure balance, sensor noise, and lens characteristics."
)

UNIPERCEPT_VQA_ISTA_PROMPT = (
    "Analyze the structural and textural details in detail, focusing on surface textures, material definitions, edge clarity, geometry, and micro-contrast."
)

UNIPERCEPT_CRITIQUE_PROMPT = UNIPERCEPT_VQA_IAA_PROMPT

def format_score_info_text(scores_dict: dict | None = None, quality_score: int | None = None) -> str:
    if scores_dict and isinstance(scores_dict, dict):
        overall = scores_dict.get("overall", quality_score)
        iaa = scores_dict.get("iaa")
        iqa = scores_dict.get("iqa")
        ista = scores_dict.get("ista")
        return (
            f"[📊 6-Way 앙상블 비평 스코어보드]\n"
            f"- 최종 종합 평점: {overall}점 / 100점\n"
            f"- 🎨 미학 & 구도 (IAA): {iaa}점\n"
            f"- 🔍 화질 & 기술 (IQA): {iqa}점\n"
            f"- 🧱 구조 & 질감 (ISTA): {ista}점\n\n"
        )
    elif quality_score is not None:
        return f"[품질/미학 점수: {quality_score}점 / 100점]\n\n"
    return ""

def format_unipercept_translate_step1_user_prompt(
    raw_en_critique: str,
    scores_dict: dict | None = None,
    quality_score: int | None = None
) -> str:
    score_info = format_score_info_text(scores_dict, quality_score)
    return (
        f"다음은 영문 시각 분석 모델(UniPercept)이 평가한 사진의 비평 원문 데이터입니다:\n\n"
        f"{score_info}{raw_en_critique}\n\n"
        "[1차 직역 지침]\n"
        "원문의 미학/화질/구조 분석 내용을 단 하나도 왜곡, 누락, 지어냄 없이 100% 충실하게 1:1 직역하여 아래 3개 영역으로 작성하십시오:\n\n"
        "1. 🎨 미학 및 구도 비평 (IAA 원문 직역)\n"
        "2. 🔍 화질 및 광학 기술 비평 (IQA 원문 직역)\n"
        "3. 🧱 구조 및 질감 비평 (ISTA 원문 직역)\n"
    )

def format_unipercept_translate_step2_user_prompt(
    step1_ko_translation: str,
    scores_dict: dict | None = None,
    quality_score: int | None = None
) -> str:
    score_info = format_score_info_text(scores_dict, quality_score)
    return (
        f"{score_info}"
        f"다음은 1차 직역된 한국어 사진 비평 데이터입니다:\n\n"
        f"{step1_ko_translation}\n\n"
        "[2차 문맥 다듬기 지침]\n"
        "상단 스코어보드([📊 6-Way 앙상블 비평 스코어보드]) 대괄호 헤더 포맷을 토시 하나 바꾸지 말고 최상단 첫 줄에 그대로 유지하십시오.\n"
        "1차 번역문의 시각적 분석 근거와 수치를 100% 보존하면서, 어색한 직역 표현을 깔끔하고 품격 있는 사진 평론 문체로 다듬어 최종 완성본을 작성하십시오:\n\n"
        "1. 🎨 미학 및 구도 비평 (IAA 문맥 다듬기)\n"
        "2. 🔍 화질 및 광학 기술 비평 (IQA 문맥 다듬기)\n"
        "3. 🧱 구조 및 질감 비평 (ISTA 문맥 다듬기)\n"
    )

def format_unipercept_translate_user_prompt(
    raw_en_critique: str,
    scores_dict: dict | None = None,
    quality_score: int | None = None
) -> str:
    return format_unipercept_translate_step1_user_prompt(raw_en_critique, scores_dict, quality_score)

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
