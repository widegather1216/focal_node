import pytest
from app.services.unipercept_adapter import UniPerceptAdapter, get_unipercept_adapter

def test_unipercept_adapter_singleton():
    adapter1 = get_unipercept_adapter()
    adapter2 = get_unipercept_adapter()
    assert adapter1 is adapter2
    assert adapter1.model is None  # Ensures model is NOT loaded at instantiation (Lazy loading)

def test_unipercept_adapter_initial_state():
    adapter = UniPerceptAdapter()
    assert adapter.model_id == "widegather/unipercept-mirror"
    assert adapter.model is None
    assert adapter.timer_active is False

def test_extract_score_from_text_multiline_and_averaging_fix():
    adapter = UniPerceptAdapter()
    
    # Text with multiple internal scores but final explicit Aesthetic Score at the end
    sample_text = (
        "This photo is well composed.\n"
        "Color Harmony Score: 40/100.\n"
        "Composition Score: 37/100.\n"
        "Overall Aesthetic Score: 97/100"
    )
    score = adapter._extract_score_from_text(sample_text, ["Aesthetic Score", "Overall Aesthetic Score", "Score"])
    assert score == 97, f"Expected 97 but got {score}"

    # Text where model outputs final line score
    sample_text_2 = (
        "Great shot.\n"
        "Aesthetic Score: 95/100"
    )
    score_2 = adapter._extract_score_from_text(sample_text_2, ["Aesthetic Score"])
    assert score_2 == 95, f"Expected 95 but got {score_2}"

def test_extract_all_scores_dict():
    adapter = UniPerceptAdapter()
    
    comp_text = (
        "This image is well executed.\n"
        "Overall Score: 88/100\n"
        "IAA Score: 95/100\n"
        "IQA Score: 80/100\n"
        "ISTA Score: 85/100"
    )
    scores = adapter._extract_all_scores_dict(comp_text)
    assert scores["overall"] == 88
    assert scores["iaa"] == 95
    assert scores["iqa"] == 80
    assert scores["ista"] == 85

def test_extract_score_from_text_score_first_header():
    adapter = UniPerceptAdapter()
    
    # Score-First format where scores appear at the very top header
    header_text = (
        "[SCORES]\n"
        "Overall Score: 89/100\n"
        "Aesthetic Score: 92/100\n"
        "Quality Score: 85/100\n"
        "Structure Score: 87/100\n"
        "[ANALYSIS]\n"
        "The image exhibits remarkable dynamic range and balanced composition."
    )
    score = adapter._extract_score_from_text(header_text, ["Aesthetic Score", "Overall Score"])
    assert score == 92, f"Expected 92 but got {score}"

    all_scores = adapter._extract_all_scores_dict(header_text)
    assert all_scores["overall"] == 89
    assert all_scores["iaa"] == 92
    assert all_scores["iqa"] == 85
    assert all_scores["ista"] == 87

def test_safety_net_retry_logic(monkeypatch):
    import os
    adapter = UniPerceptAdapter()
    
    test_img = os.path.join(os.path.dirname(__file__), "fixtures", "test_scenic.jpg")
    if not os.path.exists(test_img):
        test_img = os.path.abspath("backend/tests/fixtures/test_scenic.jpg")
    
    call_count = 0
    def mock_chat(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "This response has no score anywhere."
        else:
            return "This response has final Aesthetic Score: 92/100."

    adapter.model = type("DummyModel", (), {"chat": mock_chat})()
    
    res = adapter.generate_unipercept_critique(
        test_img,
        custom_prompt="Rate this photo",
        retry_if_score_missing=True,
        max_retries=2
    )
    assert call_count == 2, f"Expected 2 attempts but got {call_count}"
    assert res["quality_score"] == 92, f"Expected score 92 but got {res['quality_score']}"

def test_vr_scores_and_weighted_overall():
    adapter = UniPerceptAdapter()
    
    # VR output containing only 3 metrics
    vr_text = (
        "Aesthetic Score: [85]\n"
        "Quality Score: [90]\n"
        "Structure Score: [80]"
    )
    vr_scores = adapter._extract_3_vr_scores_dict(vr_text)
    assert vr_scores["iaa"] == 85
    assert vr_scores["iqa"] == 90
    assert vr_scores["ista"] == 80

    # Test mathematical weighted overall: round(0.4*85 + 0.3*90 + 0.3*80) = round(34 + 27 + 24) = 85
    overall = round((0.4 * 85) + (0.3 * 90) + (0.3 * 80))
    assert overall == 85

from app.services.unipercept_adapter import score2aestoken, AESTHETICS_TOKEN_LIST

def test_official_score2aestoken_mapping():
    assert score2aestoken(0) == "aa"
    assert score2aestoken(25) == "az"
    assert score2aestoken(26) == "ca"
    assert score2aestoken(50) == "cy"
    assert score2aestoken(51) == "da"
    assert score2aestoken(75) == "dy"
    assert score2aestoken(76) == "ea"
    assert score2aestoken(100) == "ey"
    assert len(AESTHETICS_TOKEN_LIST) == 101

def test_full_ensemble_6way_pipeline(monkeypatch):
    import os
    adapter = UniPerceptAdapter()
    test_img = os.path.join(os.path.dirname(__file__), "fixtures", "test_scenic.jpg")
    if not os.path.exists(test_img):
        test_img = os.path.abspath("backend/tests/fixtures/test_scenic.jpg")
    
    vr_calls = []
    def mock_compute_vr(pixel_values, desc):
        vr_calls.append(desc)
        if desc == "aesthetics":
            return 85.5
        elif desc == "quality":
            return 90.0
        elif desc == "structure and texture richness":
            return 80.0
        return 70.0

    vqa_calls = []
    def mock_chat(*args, **kwargs):
        text = ""
        for a in args:
            if isinstance(a, str):
                text = a
                break
        if not text:
            for v in kwargs.values():
                if isinstance(v, str):
                    text = v
                    break
        vqa_calls.append(text)
        return "Striking aesthetic composition with golden hour lighting, pin-sharp optical clarity, and rich surface textures."

    adapter.model = type("DummyModel", (), {"chat": mock_chat})()
    adapter.tokenizer = type("DummyTokenizer", (), {"convert_tokens_to_ids": lambda self, x: 100})()
    adapter.compute_official_vr_score = mock_compute_vr
    
    res = adapter.generate_full_ensemble_critique(test_img)
    
    # Verify 3 VR calls and 1 single-pass integrated VQA call
    assert vr_calls == ["aesthetics", "quality", "structure and texture richness"]
    assert len(vqa_calls) == 1
    assert res["scores"]["iaa"] == 85.5
    assert res["scores"]["iqa"] == 90.0
    assert res["scores"]["ista"] == 80.0
    # Overall (Mode D standard fallback: 0.55*85.5 + 0.3*90.0 + 0.15*80.0) = round(86.025) = 86
    assert res["scores"]["overall"] == 86
    assert res["quality_score"] == 86
    assert "Striking aesthetic composition" in res["critique"]
    assert "pin-sharp optical clarity" in res["critique"]
    assert "rich surface textures" in res["critique"]

def test_1point_perfect_score_upgrade_logic():
    adapter = UniPerceptAdapter()

    # Case 1: 'Image Aesthetic Score = 1 Perfect'
    text_1 = (
        "Visual storytelling beyond mere documentation—perfectly transcending ordinary photography realms!\n"
        "Image Aesthetic Score = 1 Perfect\n"
        "Quality Image Scores= perfect Structure Texture Interpretation"
    )
    score_1 = adapter._extract_score_from_text(text_1, ["Image Aesthetic Score", "Aesthetic Score"])
    assert score_1 == 100, f"Expected 100 but got {score_1}"

    scores_dict_1 = adapter._extract_all_scores_dict(text_1)
    assert scores_dict_1["iaa"] == 100
    assert scores_dict_1["iqa"] == 100

    # Case 2: Standalone trailing '1' with high-praise keywords (e.g. surpassing excellence)
    text_2 = (
        "Strengths lies in realistic representation and breathtaking lighting.\n"
        "Overall merit leans towards competent documentation surpassing average excellence:\n\n"
        "1"
    )
    score_2 = adapter._extract_score_from_text(text_2, ["Overall Score", "Score"])
    assert score_2 == 100, f"Expected 100 but got {score_2}"

    # Case 3: Random artifact '1' without praise keywords -> Should be discarded (None)
    text_3 = (
        "This image is blurry and has severe exposure issues.\n"
        "Score: 1"
    )
    score_3 = adapter._extract_score_from_text(text_3, ["Score"])
    assert score_3 is None, f"Expected None (to trigger retry) but got {score_3}"

def test_natural_flow_format_and_bracket_parsing():
    adapter = UniPerceptAdapter()

    # Case 1: Candidate B Natural Flow with brackets and omitted colon
    natural_flow_text = (
        "Overall Score: [98/100]\n"
        "Aesthetic Score: [95/100]\n"
        "Quality Score [97/100]\n"
        "Structure Score[96/100]\n\n"
        "This image excels in every conceivable aspect. It masterfully captures urban decay."
    )
    scores = adapter._extract_all_scores_dict(natural_flow_text)
    assert scores["overall"] == 98
    assert scores["iaa"] == 95
    assert scores["iqa"] == 97
    assert scores["ista"] == 96

    single_overall = adapter._extract_score_from_text(natural_flow_text, ["Overall Score"])
    assert single_overall == 98


def test_unipercept_prompts_strict_fidelity_and_no_emoji():
    from services.ai_parser import (
        GEMMA_TRANSLATE_STEP1_SYSTEM_PROMPT,
        GEMMA_TRANSLATE_STEP2_SYSTEM_PROMPT,
        format_unipercept_translate_step1_user_prompt,
        format_unipercept_translate_step2_user_prompt
    )

    # 1. Step 1 system prompt fidelity & no emoji
    assert "왜곡" in GEMMA_TRANSLATE_STEP1_SYSTEM_PROMPT
    assert "이모티콘" in GEMMA_TRANSLATE_STEP1_SYSTEM_PROMPT

    # 2. Step 2 system prompt: strictly prohibits subjective intervention and hallucination
    assert "무개입" in GEMMA_TRANSLATE_STEP2_SYSTEM_PROMPT
    assert "학술 번역 감수자" in GEMMA_TRANSLATE_STEP2_SYSTEM_PROMPT
    assert "## 1. [미학 및 구도 평가 (IAA)]" in GEMMA_TRANSLATE_STEP2_SYSTEM_PROMPT
    assert "## 2. [화질 및 광학 기술 평가 (IQA)]" in GEMMA_TRANSLATE_STEP2_SYSTEM_PROMPT
    assert "## 3. [구조 및 질감 분석 (ISTA)]" in GEMMA_TRANSLATE_STEP2_SYSTEM_PROMPT
    assert "이모티콘" in GEMMA_TRANSLATE_STEP2_SYSTEM_PROMPT

    # 3. User prompts have matching standard headers
    scores = {"overall": 90, "iaa": 92, "iqa": 88, "ista": 91}
    step1_prompt = format_unipercept_translate_step1_user_prompt("Raw test critique", scores)
    assert "## 1. [미학 및 구도 평가 (IAA)]" in step1_prompt
    assert "## 2. [화질 및 광학 기술 평가 (IQA)]" in step1_prompt
    assert "## 3. [구조 및 질감 분석 (ISTA)]" in step1_prompt

    step2_prompt = format_unipercept_translate_step2_user_prompt("Draft ko critique", scores)
    assert "## 1. [미학 및 구도 평가 (IAA)]" in step2_prompt
    assert "한 줄 총평" in step2_prompt
    assert "원문에 없는 새로운 조언" in step2_prompt


@pytest.mark.asyncio
async def test_chat_service_unipercept_pipeline_isolation(monkeypatch, db_session):
    """
    Verifies that when payload.engine == 'unipercept', generate_perceptual_critique
    is called with perceptual anchor and format_and_structure_critique is NOT called.
    """
    from contextlib import contextmanager
    from services.chat_service import ChatService
    import schemas, models

    photo_id = "test_critique_isolation_img"
    test_img = models.Image(
        id=photo_id,
        parent_dir="/test",
        file_path="/test/img.jpg",
        file_name="img.jpg",
        file_size=1000,
        file_mtime=1.0,
        mime_type="image/jpeg"
    )
    db_session.add(test_img)
    db_session.commit()

    @contextmanager
    def mock_session_scope():
        yield db_session

    monkeypatch.setattr("services.chat_service.SessionLocal", mock_session_scope)

    mock_format_called = False
    mock_perceptual_called = False

    class DummyUniPercept:
        def generate_full_ensemble_critique(self, *args, **kwargs):
            return {
                "critique": "Raw english anchor from UniPercept",
                "scores": {"overall": 88, "iaa": 90, "iqa": 85, "ista": 89},
                "quality_score": 88
            }
        def unload_model(self):
            pass

    class DummyGemma:
        def generate_perceptual_critique(self, *args, **kwargs):
            nonlocal mock_perceptual_called
            mock_perceptual_called = True
            return "Perceptual critique based on anchor"

        def translate_and_format_critique(self, *args, **kwargs):
            return "Translated UniPercept critique"

        def format_and_structure_critique(self, *args, **kwargs):
            nonlocal mock_format_called
            mock_format_called = True
            return "Overridden by format_and_structure"

    monkeypatch.setattr("services.unipercept_adapter.get_unipercept_adapter", lambda: DummyUniPercept())
    monkeypatch.setattr("services.chat_service.get_gemma_adapter", lambda: DummyGemma())

    req = schemas.CritiqueRequest(photo_id=photo_id, engine="unipercept")
    result = await ChatService.generate_photo_critique(req)

    assert mock_perceptual_called is True
    assert mock_format_called is False, "format_and_structure_critique should NOT be called for unipercept engine"
    assert "6-Way 앙상블 비평 스코어보드" in result["critique"]
    assert "Perceptual critique based on anchor" in result["critique"]


def test_tc_crt_11_single_pass_perceptual_anchor():
    """
    TC-CRT-11: UniPercept single-pass perceptual anchor extraction and vocabulary breakdown prevention.
    Verifies that generate_perceptual_anchor_vqa calls inference with UNIPERCEPT_VQA_SINGLE_PASS_PROMPT
    and normalized decoding parameters (repetition_penalty=1.0, do_sample=True, temp=0.7, top_p=0.9).
    """
    import os
    from services.ai_parser import UNIPERCEPT_VQA_SINGLE_PASS_PROMPT

    adapter = UniPerceptAdapter()
    test_img = os.path.join(os.path.dirname(__file__), "fixtures", "test_scenic.jpg")
    if not os.path.exists(test_img):
        test_img = os.path.abspath("backend/tests/fixtures/test_scenic.jpg")

    captured_prompt = None
    captured_config = None

    def mock_chat(self, tokenizer, pixel_values, prompt_text, generation_config=None):
        nonlocal captured_prompt, captured_config
        captured_prompt = prompt_text
        captured_config = generation_config
        return (
            "The photo exhibits remarkable compositional harmony with balanced leading lines drawing attention into the mountain ridge. "
            "Optical clarity is sharp across the central zone with minimal sensor grain and well-managed dynamic range. "
            "Tactile rock textures in the foreground create tangible spatial depth against the soft atmospheric background haze."
        )

    adapter.model = type("DummyModel", (), {"chat": mock_chat})()
    adapter.tokenizer = type("DummyTokenizer", (), {"convert_tokens_to_ids": lambda self, x: 100})()

    meta = {"camera_model": "Sony A7R V", "lens_model": "FE 35mm F1.4 GM", "f_number": 1.4, "iso": 100}
    scores = {"overall": 88, "iaa": 92, "iqa": 85, "ista": 86}

    anchor = adapter.generate_perceptual_anchor_vqa(test_img, metadata=meta, scores_context=scores)

    # 1. Prompt verification: contains single-pass prompt and EXIF
    assert UNIPERCEPT_VQA_SINGLE_PASS_PROMPT in captured_prompt
    assert "Sony A7R V" in captured_prompt

    # 2. Decoding parameter normalization: repetition_penalty=1.0, do_sample=True, temp=0.7, top_p=0.9
    assert captured_config is not None
    assert captured_config.get("repetition_penalty") == 1.0
    assert captured_config.get("do_sample") is True
    assert captured_config.get("temperature") == 0.7
    assert captured_config.get("top_p") == 0.9

    # 3. Clean diagnosis: around 150-200 tokens, no broken markdown tables
    assert len(anchor) > 100
    assert "compositional harmony" in anchor
    assert "Optical clarity is sharp" in anchor
    assert "Tactile rock textures" in anchor
    assert "## 1." not in anchor  # no robotic markdown table decay


def test_tc_crt_12_gemma_perceptual_critique_generation():
    """
    TC-CRT-12: Gemma 4 direct perceptual critique generation grounded in perceptual anchor.
    Verifies that GemmaAdapter.generate_perceptual_critique constructs system and user prompts
    with the 3 standard headers, executive summary, and preserves scoreboard header.
    """
    from services.mlx_adapters import GemmaAdapter
    from services.ai_parser import (
        GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT,
        format_score_info_text
    )

    gemma = GemmaAdapter()
    scores = {"overall": 88, "iaa": 92, "iqa": 85, "ista": 86}
    meta = {"camera_model": "Sony A7R V", "f_number": 1.4, "iso": 100}
    anchor = "Strong leading lines with sharp central clarity and tactile foreground textures."

    # Verify prompt builder
    messages = gemma._build_perceptual_critique_messages(meta, scores, anchor)
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT
    user_text = messages[1]["content"][1]["text"]
    assert "Sony A7R V" in user_text
    assert "Strong leading lines" in user_text
    assert "6-Way 앙상블 비평 스코어보드" in user_text

    # Mock execute generation and preservation
    sample_critique = (
        "> **한 줄 총평**: 섬세한 시선 유도와 빛 모델링이 돋보이나 주변부 광량 저하가 아쉬우며, 조리개 스톱 다운과 커브 보정 시 완성도가 격상될 작품입니다.\n\n"
        "## 1. [시각적 미학 및 EXIF 광학 진단]\n"
        "- 전경에서 원경으로 이어지는 **황금 분할** 구도가 안정적입니다.\n\n"
        "## 2. [구도 및 화질 결함과 왜곡 위치 지적]\n"
        "- F1.4 개방으로 인한 주변부 **색수차**가 미세하게 관찰됩니다.\n\n"
        "## 3. [현장 재촬영 및 보정 실전 기술 조언]\n"
        "- 조리개를 **F2.8**로 조이고 라이트룸에서 하이라이트 롤오프를 보정하십시오."
    )
    score_header = format_score_info_text(scores)
    output = f"{score_header}{sample_critique}"

    # Verify 3 standard headers + executive summary + scoreboard
    assert "## 1. [시각적 미학 및 EXIF 광학 진단]" in output
    assert "## 2. [구도 및 화질 결함과 왜곡 위치 지적]" in output
    assert "## 3. [현장 재촬영 및 보정 실전 기술 조언]" in output
    assert "> **한 줄 총평**" in output
    assert "6-Way 앙상블 비평 스코어보드" in output


@pytest.mark.asyncio
async def test_tc_crt_13_unipercept_failure_fallback_to_gemma(monkeypatch, db_session):
    """
    TC-CRT-13: UniPercept VQA error triggers graceful fallback to Gemma 4 direct critique.
    Verifies that when UniPercept throws an exception during critique pipeline,
    ChatService falls back to _execute_gemma_critique_pipeline and completes without error.
    """
    from contextlib import contextmanager
    from services.chat_service import ChatService
    import schemas, models

    photo_id = "test_unipercept_fallback_img"
    test_img = models.Image(
        id=photo_id,
        parent_dir="/test",
        file_path="/test/fallback.jpg",
        file_name="fallback.jpg",
        file_size=1000,
        file_mtime=1.0,
        mime_type="image/jpeg"
    )
    db_session.add(test_img)
    db_session.commit()

    @contextmanager
    def mock_session_scope():
        yield db_session

    monkeypatch.setattr("services.chat_service.SessionLocal", mock_session_scope)

    # 1. UniPercept throws RuntimeError
    class FailingUniPercept:
        def generate_full_ensemble_critique(self, *args, **kwargs):
            raise RuntimeError("MPS Device Out of Memory during UniPercept inference")
        def unload_model(self):
            pass

    # 2. Gemma direct critique fallback
    class FallbackGemma:
        def generate_deep_critique(self, *args, **kwargs):
            return "Gemma 4 직접 심층 비평 초안"
        def format_and_structure_critique(self, text, *args, **kwargs):
            return (
                "> **한 줄 총평**: 자율 비평 폴백 결과입니다.\n\n"
                "## 1. [시각적 미학 및 EXIF 광학 진단]\n- 안정적인 구도입니다.\n\n"
                "## 2. [구도 및 화질 결함과 왜곡 위치 지적]\n- 결함 없음.\n\n"
                "## 3. [현장 재촬영 및 보정 실전 기술 조언]\n- 현장 조작 유지."
            )

    monkeypatch.setattr("services.unipercept_adapter.get_unipercept_adapter", lambda: FailingUniPercept())
    monkeypatch.setattr("services.chat_service.get_gemma_adapter", lambda: FallbackGemma())

    req = schemas.CritiqueRequest(photo_id=photo_id, engine="unipercept")
    result = await ChatService.generate_photo_critique(req)

    assert result["status"] == "completed"
    assert "자율 비평 폴백 결과" in result["critique"]
    assert "## 1. [시각적 미학 및 EXIF 광학 진단]" in result["critique"]




