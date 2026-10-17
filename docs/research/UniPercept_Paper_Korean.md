# 📄 UniPercept 논문 핵심 요약 및 Focal Node 적용 레퍼런스

* **원문 제목:** *UniPercept: Towards Unified Perceptual-Level Image Understanding across Aesthetics, Quality, and Structure and Texture*
* **발표:** CVPR 2026 (`arXiv:2512.21675`)
* **저자:** Stanislaw Szymanowicz,釋(Shuo) Cao, Xiaohui Li, Yihao Liu, Yu Qiao, Chao Dong 외 (Shanghai AI Lab, CUHK, SenseTime Research 등)
* **모델 가중치:** `widegather/unipercept-mirror` (InternVL3-8B 아키텍처 기반 멀티모달 VLM)
* **관련 구현체:** [`backend/app/services/unipercept_adapter.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/unipercept_adapter.py), [`src/components/critique/CritiqueContentRenderer.tsx`](file:///Users/kimbeomjun/focal_node/src/components/critique/CritiqueContentRenderer.tsx)

---

## 🎯 1. 연구 배경: Semantic Level vs. Perceptual Level

기존 멀티모달 대형 언어 모델(MLLM)은 **"무엇이 있는가(Semantic-level: 객체 인식, 캡셔닝, OCR)"**에는 강하지만, **"이미지가 시각적으로 어떻게 느껴지고 얼마나 완성도가 높은가(Perceptual-level)"**를 평가하는 데는 한계가 있었습니다.

**UniPercept**는 인간의 시각 지각 체계를 **3대 핵심 축(IAA, IQA, ISTA)**과 **2대 태스크(VR 정량 채점, VQA 정성 비평)**로 통합한 최초의 지각 수준(Perceptual-level) 통합 비전-언어 모델입니다.

---

## 📐 2. 3대 지각 평가 분류 체계 (Perceptual Taxonomy)

Focal Node의 2단계 전문가 AI 비평(`03_ai_critique`)은 UniPercept가 정의한 3대 지각 차원을 그대로 채택하여 사진을 다각도로 진단합니다.

### 2.1. IAA (Image Aesthetics Assessment — 심미성 평가)
예술적·시각적 매력과 작가의 의도를 평가합니다.
* **Theme & Narrative (주제 및 서사성):** 주제의 명확성, 스토리텔링, 감정적 울림.
* **Composition & Framing (구도 및 프레이밍):** 삼분할, 소실점, 시선 유도선(Leading Lines), 여백의 균형.
* **Color & Lighting (색채 및 조명):** 색조 조화, 보색 대비, 빛의 방향성(역광/사광), 하이라이트와 섀도우의 드라마틱한 표현.

### 2.2. IQA (Image Quality Assessment — 기술적 화질 평가)
광학적·디지털 신호 처리 관점의 결함과 화질 저하(Degradation)를 정밀 진단합니다.
* **Sharpness & Focus (선예도 및 초점):** 주 피사체의 칼핀 여부, 모션 블러(Motion Blur), 심도(DoF) 표현의 정확성.
* **Noise & Artifacts (노이즈 및 아티팩트):** 고감도(ISO) 루미넌스/크로마 노이즈, JPEG 압축 아티팩트, 색수차(Chromatic Aberration).
* **Exposure & Dynamic Range (노출 및 다이내믹 레인지):** 하이라이트 클리핑(백트임), 암부 묻힘(블랙 크러시), 계조 표현력.

### 2.3. ISTA (Image Structure & Texture Assessment — 구조 및 질감 평가)
기하학적 구조와 표면 물성(Materiality)의 디테일을 분석합니다.
* **Geometric Structure (기하학적 구조):** 수평/수직 왜곡, 원근감(Perspective), 레이어(전경·중경·배경)의 공간적 분리도.
* **Surface Texture (표면 질감):** 피부 결, 직물, 금속, 수면, 나뭇잎 등 미세 텍스처(Micro-contrast)의 생생한 재현력.
* **Visual Complexity & Pattern (시각적 복잡도 및 패턴):** 반복되는 기하 패턴, 프랙탈 구조, 디테일의 밀도 균형.

---

## 🧮 3. 2대 추론 메커니즘: VR 채점 & VQA 비평

UniPercept는 단일 아키텍처(InternVL3-8B) 위에서 **정량 점수 산출(Visual Rating, VR)**과 **정성 시각 질의응답(Visual Question Answering, VQA)**을 동시에 수행합니다.

### 3.1. Visual Rating (VR) — Logit 확률 가중 기대값 채점
단순히 텍스트로 숫자를 생성하게 하면 토큰 편향(Token Bias)으로 인해 불연속적인 점수만 출력됩니다. UniPercept는 첫 번째 응답 토큰 위치에서 **5단계 평점 어휘(`excellent`, `good`, `fair`, `poor`, `bad`)의 Logit 확률 분포**를 추출하여 연속적인 실수 점수를 계산합니다.

$$S_{\text{raw}} = \sum_{i=1}^{5} w_i \cdot P(t_i) = 5 \cdot P(\text{excellent}) + 4 \cdot P(\text{good}) + 3 \cdot P(\text{fair}) + 2 \cdot P(\text{poor}) + 1 \cdot P(\text{bad})$$

$$S_{100} = \frac{S_{\text{raw}} - 1}{4} \times 100 \quad \in [0, 100]$$

* **Focal Node 구현:** [`unipercept_adapter.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/unipercept_adapter.py)의 `_compute_vr_score()`에서 `model.forward()`로 마지막 토큰 Logit을 추출하고, 5개 등급 토큰 ID에 대해 `softmax`를 취한 뒤 0~100점 스케일(`iaa_score`, `iqa_score`, `ista_score`)로 변환합니다.

### 3.2. Visual Question Answering (VQA) — 구조화된 시각 비평 생성
점수 산출 직후, 세 가지 지각 영역(Aesthetics, Quality, Structure & Texture)을 아우르는 심층 분석 프롬프트를 입력하여 `model.generate()`로 영문 전문 비평문을 생성합니다.
* **Focal Node 구현:** 생성된 영문 VQA 비평(`unipercept_raw_en`)과 3대 VR 점수는 후속 파이프라인에서 **Gemma 4 (12B-it-8bit)**에 전달되어 한국어 매거진 에디토리얼 JSON 포맷으로 번역 및 구조화됩니다.

---

## 🧠 4. 2단계 학습 파이프라인 (DAPT & GRPO)

UniPercept가 인간 전문가 수준의 지각 능력을 획득한 핵심 학습 기법은 다음과 같습니다.

1. **Stage 1 — Domain-Adaptive Pre-Training (DAPT):**
   * 약 **80만 건(800K)** 규모의 다중 도메인 지각 데이터셋(**UniPercept-Bench** 전구체: KonIQ-10k, SPAQ, AVA, APDD, Q-Instruct, DepictQA 및 자체 구축 ISTA 코퍼스)을 통합하여 지각 도메인 어휘와 시각적 미묘함을 사전 학습합니다.
2. **Stage 2 — Group Relative Policy Optimization (GRPO) 기반 강화학습:**
   * 정량 채점(VR)에는 **연속형 가우시안 보상(Adaptive Gaussian Reward)**을, 정성 비평(VQA)에는 **이진 정확도 및 구조 보상(Format & Accuracy Reward)**을 결합한 GRPO를 적용하여 점수 예측 정밀도와 비평 논리성을 동시에 극대화했습니다.

---

## 🛠️ 5. Focal Node 엔지니어링 통합 요약

| 논문 구성 요소 | Focal Node 적용 위치 | 구현 세부 사항 |
| :--- | :--- | :--- |
| **백본 가중치** | [`unipercept_adapter.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/unipercept_adapter.py) | `widegather/unipercept-mirror` (`bfloat16`, PyTorch MPS, `trust_remote_code=True`) |
| **픽셀 전처리** | [`unipercept_adapter.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/unipercept_adapter.py) | `448x448` Dynamic Patch Tiling (`max_num=6`) + ImageNet 정규화 |
| **IAA / IQA / ISTA VR 채점** | [`unipercept_adapter.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/unipercept_adapter.py) | 3개 도메인 프롬프트 각각에 대해 `model.forward()` 1-step Logit 확률 기대값 계산 (`0~100`점) |
| **VQA 영문 비평 생성** | [`unipercept_adapter.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/unipercept_adapter.py) | `model.generate(max_new_tokens=512, do_sample=False)`로 영문 종합 비평 추출 |
| **Gemma 4 한영 브릿지** | [`gemma_adapter.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/gemma_adapter.py) | UniPercept 영문 비평 + VR 3종 점수를 입력받아 한국어 구조화 비평 JSON 생성 |
| **프론트엔드 시각화** | [`CritiqueContentRenderer.tsx`](file:///Users/kimbeomjun/focal_node/src/components/critique/CritiqueContentRenderer.tsx) | IAA/IQA/ISTA 프로그레스 바, `<think>` 추론 아코디언, 한/영 원문 토글 렌더링 |
| **메모리 수명주기 제어** | [`critique.py`](file:///Users/kimbeomjun/focal_node/backend/app/api/critique.py) | 추론 직후 `finally` 블록에서 즉시 `unload_model()` 및 `torch.mps.empty_cache()` 호출 ([상세 메모리 분석](file:///Users/kimbeomjun/focal_node/docs/research/UniPercept_Memory_Analysis.md)) |
