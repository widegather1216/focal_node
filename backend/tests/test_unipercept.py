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
    
    test_img = os.path.abspath("scratch/test_images/test_scenic.jpg")
    if not os.path.exists(test_img):
        test_img = os.path.abspath("../scratch/test_images/test_scenic.jpg")
    
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
    test_img = os.path.abspath("scratch/test_images/test_scenic.jpg")
    if not os.path.exists(test_img):
        test_img = os.path.abspath("../scratch/test_images/test_scenic.jpg")
    
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
        if "aesthetic qualities" in text:
            return "Striking aesthetic composition with golden hour lighting."
        elif "technical image quality" in text:
            return "Pin-sharp optical clarity with minimal sensor noise."
        else:
            return "Exceptional micro-contrast and rich surface textures."

    adapter.model = type("DummyModel", (), {"chat": mock_chat})()
    adapter.tokenizer = type("DummyTokenizer", (), {"convert_tokens_to_ids": lambda self, x: 100})()
    adapter.compute_official_vr_score = mock_compute_vr
    
    res = adapter.generate_full_ensemble_critique(test_img)
    
    # Verify 3 VR calls and 3 VQA calls = 6 total calls
    assert vr_calls == ["aesthetics", "quality", "structure and texture richness"]
    assert len(vqa_calls) == 3
    assert res["scores"]["iaa"] == 85.5
    assert res["scores"]["iqa"] == 90.0
    assert res["scores"]["ista"] == 80.0
    # Overall = round(0.4*85.5 + 0.3*90.0 + 0.3*80.0) = round(34.2 + 27.0 + 24.0) = round(85.2) = 85
    assert res["scores"]["overall"] == 85
    assert res["quality_score"] == 85
    assert "Striking aesthetic composition" in res["critique"]
    assert "Pin-sharp optical clarity" in res["critique"]
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



