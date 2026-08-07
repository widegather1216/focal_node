# [Doc 5] AI 모델 설치 및 로컬 구동 가이드 (Apple Silicon)

본 문서는 Apple Silicon Mac (M 시리즈) 환경에서 **SigLIP 2**, **Gemma 4 E4B-it** 및 **UniPercept 8B** 모델을 설치하고 GPU(Metal) 가속으로 구동하기 위한 상세 가이드를 제공합니다.

---

## 🏛️ 1. AI 모델 개요 및 아키텍처 상의 역할

본 프로젝트에서는 로컬 하드웨어 리소스를 극도로 절약하면서 자연어 시맨틱 검색, 오프라인 메타데이터 추출 및 전문 AI 사진 비평을 달성하기 위해 다음 세 가지 모델을 사용합니다.

1. **SigLIP 2 (google/siglip2-base-patch16-224)**
   * **역할:** 이미지 및 텍스트의 768차원 특징 임베딩 추출 (ChromaDB 저장 및 코사인 유사도 검색용) 및 Zero-shot 키워드 추출.
   * **특징:** 메모리 상주(Keep-alive) 상태로 빠른 검색 응답을 보장합니다.
2. **Gemma 4 26B-A4B (mlx-community/gemma-4-26B-A4B-it-qat-OptiQ-4bit)**
   * **역할:** 이미지의 감각적인 상세 묘사(Caption) 생성, 태그 추출, 시각 키워드 교차 검증 및 비평 요약 보고서 작성.
   * **특징:** 26B MoE(Active 4B) 아키텍처에 QAT + OptiQ 4-bit 양자화를 적용하여 빠른 추론 속도와 뛰어난 지침 준수 능력을 제공합니다. 60초 Keep-alive 데몬 관리를 적용하여 VRAM을 자진 반환합니다.
3. **UniPercept 8B (unipercept/UniPercept-8B)**
   * **역할:** 전문 포트폴리오 수준의 사진 구도, 조명, 색감 기술 분석 및 깊이 있는 비평/점수 산출.
   * **특징:** 대용량 비평 전문 VLM으로 16GB 메모리 절약을 위해 비평 생성이 완료되면 즉시 메모리를 언로드(`mx.clear_cache()`)합니다.

---

## ⚙️ 2. 환경 준비 및 패키지 설치

로컬 가상환경(venv)을 활성화한 뒤, 필요한 가속 라이브러리와 의존성 패키지를 설치합니다.

```bash
# 1. 가상환경 활성화 (프로젝트 루트 기준)
source venv/bin/activate

# 2. requirements.txt를 통한 일괄 설치
pip install -r backend/requirements.txt
```

### 필수 패키지 목록 (`backend/requirements.txt`에 포함됨)
* **`mlx-lm`**: Apple Silicon GPU 가속 기반으로 Gemma 4 및 UniPercept 모델을 로드하고 텍스트/비전 추론을 처리하기 위한 코어 패키지.
* **`transformers>=4.49.0`**: SigLIP 2 및 최신 VLM 아키텍처 파싱을 위한 최신 허깅페이스 라이브러리.
* **`torch>=2.2.0`**: MPS(Metal Performance Shaders) 백엔드 가속을 사용하기 위한 파이토치 엔진.

### 🖥️ Apple Silicon GPU (Metal) 연동 검증
가상환경 내에서 아래 한 줄 명령어를 실행하여 Metal GPU 장치가 올바르게 잡혔는지 확인하십시오.
```bash
python3 -c "import mlx.core as mx; print(mx.default_device())"
```
* **정상 결과:** `Device(gpu, 0)`이 출력되면 성공입니다.

---

## 🤖 3. Gemma 4 E4B-it 설치 및 구동 방법 (MLX 네이티브)

VRAM 점유율을 획기적으로 낮추기 위해 **4-bit 양자화(Quantized) 버전** 사용을 권장합니다.

* **추천 모델 식별자:** `mlx-community/gemma-4-26B-A4B-it-qat-OptiQ-4bit`

---

## ⚡ 4. SigLIP 2 설치 및 구동 방법 (PyTorch MPS)

* **모델 식별자:** `google/siglip2-base-patch16-224`

---

## 🎨 5. UniPercept 8B 비평 모델 구동 및 메모리 언로드 전략

* **모델 식별자:** `unipercept/UniPercept-8B`
* **메모리 수동 언로드:** `UniPerceptAdapter.unload_model()`을 호출하여 비평 직후 메모리를 반환함으로써 멀티태스킹 메모리 점유를 최적화합니다.
