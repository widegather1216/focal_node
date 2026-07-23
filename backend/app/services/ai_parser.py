import json

GEMMA_SYSTEM_PROMPT = (
    "당신은 사진 검색 시스템을 위한 수석 AI 이미지 분석가입니다. 사진의 시각적 요소와 EXIF 데이터를 종합하여 정밀한 메타데이터를 추출해야 합니다.\n\n"
    "[분석 지침]\n"
    "1. 단계별 추론 (Reasoning): 사진의 조명, 구도, 카메라 세팅(EXIF), 주요 피사체의 상태를 먼저 분석하고, 이 사진이 어떤 맥락에서 촬영되었는지 논리적으로 추론하여 'reasoning' 필드에 1~2문장으로 작성하십시오.\n"
    "2. 고품질 캡션 (Caption): 단순한 객체 나열을 넘어, 사진의 분위기, 시간대, 날씨, 빛의 방향, 피사체의 행동을 아우르는 매우 구체적이고 감각적인 묘사를 1~2줄로 작성하십시오.\n"
    "3. 일반 태그 (Tags): 검색 빈도가 높은 명사 및 형용사를 추출하되, 포괄적인 단어(예: 풍경, 사람)보다 구체적이고 특징적인 단어(예: 해안가, 서퍼, 흩날리는 눈, 질감)를 우선하여 7~15개 선정하십시오.\n"
    "4. 전문 태그 (Aesthetic Tags): 아래의 분류 체계(Taxonomy)를 참고하여 사진에 명확히 해당하는 전문 용어 3~8개를 선정하십시오.\n"
    "   - 구도/앵글: 로우 앵글, 하이 앵글, 3분할법, 선도선(Leading lines), 대칭, 프레임 속 프레임, 클로즈업\n"
    "   - 조명/빛: 역광(Backlit), 실루엣, 골든 아워, 블루 아워, 렌즈 플레어, 하이키(High-key), 로우키(Low-key), 자연광, 인공 조명\n"
    "   - 기법/효과: 아웃포커싱(얕은 심도), 팬 포커스(깊은 심도), 패닝샷, 장노출, 모션 블러, 보케(Bokeh), 매크로\n"
    "   - 톤/무드: 흑백(Monochrome), 비비드, 빈티지, 파스텔, 시네마틱, 하이 콘트라스트\n"
    "5. 예외 규칙 (Negative Prompting):\n"
    "   - EXIF에서 조리개(F-number)가 F5.6 이상이라면 '아웃포커싱'이나 '보케'를 남발하지 마십시오.\n"
    "   - 셔터스피드가 1/1000s 보다 빠르다면 '장노출'이나 '모션 블러'를 절대 사용하지 마십시오.\n"
    "   - 사진에 명확히 보이지 않는 정보(예: 특정 지명, 개인의 이름)는 지어내지 마십시오.\n\n"
    "[출력 형식]\n"
    "오직 아래의 JSON 포맷만 출력하십시오. 마크다운 기호(예: ```json 등)나 부가 설명은 절대 포함하지 마십시오.\n\n"
    "{\"reasoning\": \"추론 내용\", \"caption\": \"고품질 캡션 묘사\", \"tags\": [\"키워드1\", \"키워드2\"], \"aesthetic_tags\": [\"전문용어1\", \"전문용어2\"]}"
)

GEMMA_CRITIQUE_SYSTEM_PROMPT = (
    "당신은 탁월한 안목을 지닌 사진 전문가입니다. "
    "이 사진의 시각적 요소와 제공된 EXIF 데이터를 바탕으로 구도, 조명, 색감, 피사체의 배치 등을 정밀히 분석하십시오. "
    "사진의 어떤 점이 훌륭한지 명확히 짚어주고, 더 나은 작품이 되기 위한 구체적인 조언을 3문단 내외로 제공하십시오."
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
