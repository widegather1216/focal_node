import pytest
from services.unipercept_adapter import UniPerceptAdapter, get_unipercept_adapter

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

def test_adr05_scoreboard_parser_and_weighted_overall():
    from services.ai_parser import parse_scoreboard_scores
    from services.scoring import calculate_overall_vr_score

    scoreboard_text = (
        "[6-Way 앙상블 비평 스코어보드]\n"
        "- 최종 종합 평점: 86점 / 100점\n"
        "- 미학 및 구도 (IAA): 85점\n"
        "- 화질 및 선명도 (IQA): 90점\n"
        "- 구조 및 질감 (ISTA): 80점\n\n"
        "> **한 줄 총평**: 균형 잡힌 구도와 선예도가 돋보입니다."
    )
    parsed = parse_scoreboard_scores(scoreboard_text)
    assert parsed == {"overall": 86.0, "iaa": 85.0, "iqa": 90.0, "ista": 80.0}

    # Mode D (0.55 * 85 + 0.30 * 90 + 0.15 * 80) = 46.75 + 27.0 + 12.0 = 85.75 -> round = 86
    overall = calculate_overall_vr_score(85, 90, 80)
    assert overall == 86

from services.unipercept_adapter import score2aestoken, AESTHETICS_TOKEN_LIST

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

def test_adr05_prompts_strict_fidelity_and_no_emoji():
    from services.ai_parser import (
        GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT,
        UNIPERCEPT_VQA_SINGLE_PASS_PROMPT,
        format_perceptual_critique_user_prompt,
    )

    assert "이모티콘" in GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT
    assert "## 1. [시각적 미학 및 EXIF 광학 진단]" in GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT
    assert "## 2. [구도 및 화질 결함과 왜곡 위치 지적]" in GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT
    assert "## 3. [현장 재촬영 및 보정 실전 기술 조언]" in GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT
    assert "Aesthetics & Composition" in UNIPERCEPT_VQA_SINGLE_PASS_PROMPT
    assert "Technical Quality & Distortions" in UNIPERCEPT_VQA_SINGLE_PASS_PROMPT
    assert "Structure & Surface Textures" in UNIPERCEPT_VQA_SINGLE_PASS_PROMPT

    scores = {"overall": 90, "iaa": 92, "iqa": 88, "ista": 91}
    user_prompt = format_perceptual_critique_user_prompt("Balanced lighting.", scores_dict=scores)
    assert "[6-Way 앙상블 비평 스코어보드]" in user_prompt
    assert "Balanced lighting." in user_prompt
    assert "이모티콘" in user_prompt


@pytest.mark.asyncio
async def test_adr05_pipeline_monotonic_progress_and_labels(monkeypatch, db_session):
    """Verify REFACTOR-08: monotonic progress (5 -> 12 -> 22 -> 32 -> 50 -> 75 -> 100) with no [1/6] regressions."""
    import os
    from contextlib import contextmanager
    import models
    import schemas
    from services.chat_service import ChatService
    from services.critique_status import critique_status_manager

    photo_id = "test_monotonic_progress_img"
    img_path = os.path.abspath("backend/tests/fixtures/test_scenic.jpg")
    db_session.add(models.Image(
        id=photo_id, parent_dir="/test", file_path=img_path,
        file_name="test_scenic.jpg", file_size=1000, file_mtime=1.0, mime_type="image/jpeg",
    ))
    db_session.commit()

    @contextmanager
    def mock_session_scope():
        yield db_session

    monkeypatch.setattr("services.chat_service.SessionLocal", mock_session_scope)

    recorded_updates = []
    original_update = critique_status_manager.update

    def capture_update(pid, step, total_steps, message, progress, status="processing", **extra):
        if pid == photo_id:
            recorded_updates.append((step, message, progress, status))
        return original_update(pid, step, total_steps, message, progress, status=status, **extra)

    monkeypatch.setattr(critique_status_manager, "update", capture_update)

    adapter = UniPerceptAdapter()
    adapter.model = type("DummyUniModel", (), {"chat": lambda *a, **kw: "Clean composition."})()
    adapter.tokenizer = type("DummyTok", (), {"convert_tokens_to_ids": lambda self, x: 1})()
    adapter.compute_official_vr_score = lambda pixel_values, desc: 85.0
    adapter._prepare_pixel_values = lambda pil_img, photo_id=None: None
    adapter.unload_model = lambda: None

    class DummyGemma:
        active_requests = 0
        def generate_perceptual_critique(self, image_path, perceptual_anchor, scores_dict=None, metadata=None, photo_id=None):
            critique_status_manager.update(photo_id, 3, 4, "[Gemma] 지각 앵커 기반 심층 비평 작성 중...", 75)
            return "[6-Way 앙상블 비평 스코어보드]\n- 최종 종합 평점: 85점 / 100점\n- 미학 및 구도 (IAA): 85점\n- 화질 및 선명도 (IQA): 85점\n- 구조 및 질감 (ISTA): 85점\n\n좋은 사진입니다."
        def unload_model(self):
            pass

    monkeypatch.setattr("services.unipercept_adapter.get_unipercept_adapter", lambda: adapter)
    monkeypatch.setattr("services.chat_service.get_gemma_adapter", lambda: DummyGemma())

    result = await ChatService.generate_photo_critique(schemas.CritiqueRequest(photo_id=photo_id, engine="unipercept"))
    assert result["status"] == "completed"
    progress_values = [entry[2] for entry in recorded_updates]
    assert progress_values == sorted(progress_values), f"Non-monotonic progress detected: {recorded_updates}"
    assert progress_values[0] == 5 and progress_values[-1] == 100
    assert all("/6]" not in entry[1] for entry in recorded_updates)
    assert any("[1/3]" in entry[1] for entry in recorded_updates)


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


def test_tc_crt_12_gemma_perceptual_critique_generation(monkeypatch):
    """
    TC-CRT-12: Gemma 4 direct perceptual critique generation grounded in perceptual anchor.
    Verifies that GemmaAdapter.generate_perceptual_critique executes with mocked VLM components,
    properly formats messages with 3 standard headers, calls tokenizer and generator,
    and prepends the scoreboard header when missing.
    """
    import os
    from unittest.mock import MagicMock
    from services.mlx_adapters import GemmaAdapter
    from services.ai_parser import (
        GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT,
        format_score_info_text
    )

    gemma = GemmaAdapter()
    monkeypatch.setattr(gemma, "_load_model_locked", lambda: None)
    gemma.model = MagicMock()

    mock_tokenizer = MagicMock()
    mock_tokenizer.apply_chat_template.return_value = "<formatted_chat_prompt>"
    mock_processor = MagicMock()
    mock_processor.tokenizer = mock_tokenizer
    gemma.processor = mock_processor

    sample_critique_body = (
        "> **한 줄 총평**: 섬세한 시선 유도와 빛 모델링이 돋보이나 주변부 광량 저하가 아쉬우며, 조리개 스톱 다운과 커브 보정 시 완성도가 격상될 작품입니다.\n\n"
        "## 1. [시각적 미학 및 EXIF 광학 진단]\n"
        "- 전경에서 원경으로 이어지는 **황금 분할** 구도가 안정적입니다.\n\n"
        "## 2. [구도 및 화질 결함과 왜곡 위치 지적]\n"
        "- F1.4 개방으로 인한 주변부 **색수차**가 미세하게 관찰됩니다.\n\n"
        "## 3. [현장 재촬영 및 보정 실전 기술 조언]\n"
        "- 조리개를 **F2.8**로 조이고 라이트룸에서 하이라이트 롤오프를 보정하십시오."
    )
    mock_gen_result = MagicMock()
    mock_gen_result.text = sample_critique_body

    captured_generate_calls = []
    def mock_generate(model, processor, prompt=None, image=None, max_tokens=3072, verbose=False):
        captured_generate_calls.append({"prompt": prompt, "image": image})
        return mock_gen_result

    monkeypatch.setattr("mlx_vlm.generate", mock_generate)

    scores = {"overall": 88, "iaa": 92, "iqa": 85, "ista": 86}
    meta = {"camera_model": "Sony A7R V", "f_number": 1.4, "iso": 100}
    anchor = "Strong leading lines with sharp central clarity and tactile foreground textures."

    test_img = os.path.join(os.path.dirname(__file__), "fixtures", "test_scenic.jpg")
    if not os.path.exists(test_img):
        test_img = os.path.abspath("backend/tests/fixtures/test_scenic.jpg")

    # Execute actual adapter method
    output = gemma.generate_perceptual_critique(
        image_path=test_img,
        metadata=meta,
        scores_dict=scores,
        perceptual_anchor=anchor
    )

    # 1. Verify tokenizer chat template was called with valid messages structure
    assert mock_tokenizer.apply_chat_template.called
    template_call_args = mock_tokenizer.apply_chat_template.call_args
    passed_messages = template_call_args[0][0]
    assert passed_messages[0]["role"] == "system"
    assert passed_messages[0]["content"] == GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT
    user_text = passed_messages[1]["content"][1]["text"]
    assert "Sony A7R V" in user_text
    assert "Strong leading lines" in user_text
    assert "6-Way 앙상블 비평 스코어보드" in user_text

    # 2. Verify generator execution
    assert len(captured_generate_calls) == 1
    assert captured_generate_calls[0]["prompt"] == "<formatted_chat_prompt>"

    # 3. Verify output includes scoreboard header and standard critique structure
    expected_scoreboard = format_score_info_text(scores)
    assert expected_scoreboard in output
    assert "## 1. [시각적 미학 및 EXIF 광학 진단]" in output
    assert "## 2. [구도 및 화질 결함과 왜곡 위치 지적]" in output
    assert "## 3. [현장 재촬영 및 보정 실전 기술 조언]" in output
    assert "> **한 줄 총평**" in output

    # 4. Verify request counter was safely decremented
    assert gemma.active_requests == 0


@pytest.mark.asyncio
async def test_tc_crt_13_unipercept_failure_fallback_to_gemma(monkeypatch, db_session):
    """
    TC-CRT-13: UniPercept VQA error triggers graceful fallback to Gemma 4 direct critique.
    Verifies that when UniPercept VQA inference fails within generate_full_ensemble_critique,
    the exception is propagated (not silently swallowed) to _execute_unipercept_critique_pipeline,
    and ChatService seamlessly falls back to _execute_gemma_critique_pipeline.
    """
    from contextlib import contextmanager
    from services.chat_service import ChatService
    from services.unipercept_adapter import UniPerceptAdapter
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

    # Use actual UniPerceptAdapter instance
    real_adapter = UniPerceptAdapter()
    monkeypatch.setattr(real_adapter, "_safe_load_pil_image", lambda path: None)
    monkeypatch.setattr(
        real_adapter,
        "generate_vr_scores",
        lambda *args, **kwargs: {
            "overall": 85,
            "iaa": 88,
            "iqa": 82,
            "ista": 84,
            "raw_vr_text": "Aesthetic Score: [88]\nQuality Score: [82]\nStructure Score: [84]"
        }
    )

    # VQA anchor generation raises runtime exception (simulating VQA stage failure)
    def mock_failing_vqa(*args, **kwargs):
        raise RuntimeError("UniPercept VQA forward pass memory corruption")

    monkeypatch.setattr(real_adapter, "generate_perceptual_anchor_vqa", mock_failing_vqa)
    monkeypatch.setattr("services.unipercept_adapter.get_unipercept_adapter", lambda: real_adapter)

    # Gemma direct critique fallback
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

    monkeypatch.setattr("services.chat_service.get_gemma_adapter", lambda: FallbackGemma())

    req = schemas.CritiqueRequest(photo_id=photo_id, engine="unipercept")
    result = await ChatService.generate_photo_critique(req)

    assert result["status"] == "completed"
    assert "자율 비평 폴백 결과" in result["critique"]
    assert "## 1. [시각적 미학 및 EXIF 광학 진단]" in result["critique"]


def test_defect_03_vqa_bypasses_chat_return_dict_collision(monkeypatch):
    """
    DEFECT-03 reproduction (Case 1):
    When self.model is an InternVLChatModel (has language_model and extract_feature),
    _run_single_vqa_domain_inference must bypass self.model.chat() (which passes
    return_dict=None and triggers TypeError in transformers 5.12.1 _prefill) and directly
    invoke self.model.language_model.generate(inputs_embeds=..., attention_mask=..., ...)
    without return_dict, stripping <think>...</think> and stop tokens from the output.
    """
    import os
    import torch

    adapter = UniPerceptAdapter()
    test_img = os.path.join(os.path.dirname(__file__), "fixtures", "test_scenic.jpg")
    if not os.path.exists(test_img):
        test_img = os.path.abspath("backend/tests/fixtures/test_scenic.jpg")

    captured_gen_kwargs = {}

    class DummyLanguageModel:
        def get_input_embeddings(self):
            return lambda ids: torch.zeros((ids.shape[0], ids.shape[1], 16), dtype=torch.float32)

        def generate(self, **kwargs):
            if "return_dict" in kwargs:
                raise TypeError("Qwen2ForCausalLM.forward() got multiple values for keyword argument 'return_dict'")
            captured_gen_kwargs.update(kwargs)
            return torch.tensor([[1, 2, 3]])

    class DummyInternVLModel:
        num_image_token = 4

        def __init__(self):
            self.language_model = DummyLanguageModel()
            self.img_context_token_id = None

        def extract_feature(self, pixel_values):
            return torch.ones((1, 4, 16), dtype=torch.float32)

        def chat(self, *args, **kwargs):
            raise TypeError("Qwen2ForCausalLM.forward() got multiple values for keyword argument 'return_dict'")

    class DummyTokenizer:
        def convert_tokens_to_ids(self, token):
            return 99 if token == "<IMG_CONTEXT>" else 151645

        def __call__(self, query, return_tensors="pt"):
            # 2 prefix tokens + 4 IMG_CONTEXT (99) + 2 suffix tokens
            return {
                "input_ids": torch.tensor([[10, 11, 99, 99, 99, 99, 12, 13]]),
                "attention_mask": torch.ones((1, 8), dtype=torch.long),
            }

        def batch_decode(self, output_ids, skip_special_tokens=True):
            return ["<think>internal reasoning</think>\nBalanced composition with sharp central clarity and rich rock textures.<|im_end|> trailing"]

    adapter.device = "cpu"
    adapter.torch_dtype = torch.float32
    adapter.model = DummyInternVLModel()
    adapter.tokenizer = DummyTokenizer()
    monkeypatch.setattr(adapter, "_prepare_pixel_values", lambda pil_img, **kw: torch.zeros((1, 3, 448, 448)))

    anchor = adapter.generate_perceptual_anchor_vqa(
        test_img,
        metadata={"camera_model": "Sony A7R V", "f_number": 2.8, "iso": 100},
        scores_context={"overall": 88, "iaa": 90, "iqa": 85, "ista": 86},
    )

    assert "return_dict" not in captured_gen_kwargs
    assert "inputs_embeds" in captured_gen_kwargs
    assert "attention_mask" in captured_gen_kwargs
    assert captured_gen_kwargs.get("use_cache") is True
    assert captured_gen_kwargs.get("repetition_penalty") == 1.0
    assert captured_gen_kwargs.get("do_sample") is True
    assert "<think>" not in anchor
    assert "<|im_end|>" not in anchor
    assert anchor == "Balanced composition with sharp central clarity and rich rock textures."


@pytest.mark.asyncio
async def test_defect_03_vqa_exception_propagates_for_gemma_fallback(monkeypatch, db_session):
    """
    DEFECT-03 reproduction (Case 2):
    When VQA inference fails inside generate_perceptual_anchor_vqa, the exception must
    NOT be swallowed into 'Perceptual analysis error: ...'; it must propagate so that
    ChatService falls back to Gemma 4 direct critique and never saves an error string to critique_en.
    """
    import os
    from contextlib import contextmanager
    from services.chat_service import ChatService
    import schemas, models

    photo_id = "test_defect_03_vqa_fallback_img"
    test_img_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_scenic.jpg")
    if not os.path.exists(test_img_path):
        test_img_path = os.path.abspath("backend/tests/fixtures/test_scenic.jpg")

    test_img = models.Image(
        id=photo_id,
        parent_dir=os.path.dirname(test_img_path),
        file_path=test_img_path,
        file_name="test_scenic.jpg",
        file_size=1000,
        file_mtime=1.0,
        mime_type="image/jpeg",
    )
    db_session.add(test_img)
    db_session.commit()

    @contextmanager
    def mock_session_scope():
        yield db_session

    monkeypatch.setattr("services.chat_service.SessionLocal", mock_session_scope)

    adapter = UniPerceptAdapter()
    adapter.model = type(
        "FailingVqaModel",
        (),
        {"chat": lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("Simulated VQA TypeError"))},
    )()
    adapter.tokenizer = type("DummyTokenizer", (), {"convert_tokens_to_ids": lambda self, x: 100})()
    monkeypatch.setattr(adapter, "compute_official_vr_score", lambda pv, desc, **kw: 85.0)
    monkeypatch.setattr(adapter, "_prepare_pixel_values", lambda pil_img, **kw: None)

    # 1. Direct call to generate_perceptual_anchor_vqa must raise RuntimeError
    with pytest.raises(RuntimeError, match="Simulated VQA TypeError"):
        adapter.generate_perceptual_anchor_vqa(test_img_path)

    # Restore model after unload for full ChatService fallback verification
    adapter.model = type(
        "FailingVqaModel",
        (),
        {"chat": lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("Simulated VQA TypeError"))},
    )()

    class FallbackGemma:
        def generate_deep_critique(self, *args, **kwargs):
            return "Gemma 4 자율 폴백 비평"

        def format_and_structure_critique(self, text, *args, **kwargs):
            return (
                "> **한 줄 총평**: VQA 예외 전파에 따른 자율 비평 폴백입니다.\n\n"
                "## 1. [시각적 미학 및 EXIF 광학 진단]\n- 구도 양호.\n\n"
                "## 2. [구도 및 화질 결함과 왜곡 위치 지적]\n- 결함 없음.\n\n"
                "## 3. [현장 재촬영 및 보정 실전 기술 조언]\n- 현행 유지."
            )

    monkeypatch.setattr("services.unipercept_adapter.get_unipercept_adapter", lambda: adapter)
    monkeypatch.setattr("services.chat_service.get_gemma_adapter", lambda: FallbackGemma())

    req = schemas.CritiqueRequest(photo_id=photo_id, engine="unipercept")
    result = await ChatService.generate_photo_critique(req)

    assert result["status"] == "completed"
    assert "VQA 예외 전파에 따른 자율 비평 폴백입니다" in result["critique"]
    assert result["critique_en"] is None


def test_defect_03_load_model_locked_calls_eval(monkeypatch):
    """
    DEFECT-03 reproduction (Case 3):
    Verifies that _load_model_locked() explicitly calls .eval() on the loaded model.
    """
    import transformers

    adapter = UniPerceptAdapter()
    eval_called = False

    class FakePretrainedModel:
        def to(self, device):
            return self

        def eval(self):
            nonlocal eval_called
            eval_called = True
            return self

    monkeypatch.setattr(transformers.AutoModel, "from_pretrained", lambda *a, **kw: FakePretrainedModel())
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", lambda *a, **kw: object())
    monkeypatch.setattr(transformers.AutoProcessor, "from_pretrained", lambda *a, **kw: object())

    adapter.load_model()
    assert eval_called is True, "_load_model_locked() did not call self.model.eval()!"
    adapter.unload_model()





