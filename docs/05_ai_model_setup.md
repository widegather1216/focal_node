# [Doc 5] AI 모델 설치 및 로컬 구동 가이드 (Apple Silicon)

본 문서는 Apple Silicon Mac (M 시리즈) 환경에서 **SigLIP 2**, **Gemma 4 (12B-it-8bit)** 및 **UniPercept 8B** 모델을 설치하고 가속 구동하기 위한 상세 가이드를 제공합니다.

---

## 🏛️ 1. AI 모델 개요 및 아키텍처 상의 역할

본 프로젝트에서는 로컬 하드웨어 리소스를 극도로 절약하면서 자연어 시맨틱 검색, 오프라인 메타데이터 추출 및 전문 AI 사진 비평을 달성하기 위해 다음 세 가지 모델을 사용합니다.

1. **SigLIP 2 (`google/siglip2-base-patch16-224`)**
   * **역할:** 이미지 및 텍스트의 768차원 특징 임베딩 추출 (ChromaDB 저장 및 코사인 유사도 검색용) 및 Zero-shot 키워드 추출.
   * **구동 백엔드:** PyTorch MPS (Metal 가속).
   * **특징:** 메모리 상주(Keep-alive) 상태로 빠른 검색 응답을 보장합니다.
2. **Gemma 4 (`mlx-community/gemma-4-12B-it-8bit`)**
   * **역할:** 이미지의 감각적인 상세 묘사(Caption) 생성, 태그 추출, 시각 키워드 교차 검증 및 비평 2-Pass 정밀 한국어 번역/요약 보고서 작성.
   * **구동 백엔드:** MLX VLM (Apple Native Metal C++ 런타임).
   * **특징:** 8-bit 양자화를 적용하여 높은 품질의 서정적 문장력과 빠른 추론 속도를 제공합니다. 작업 완료 후 60초간 Keep-alive 버퍼를 유지한 뒤 VRAM을 자동 반환합니다.
3. **UniPercept 8B (`widegather/unipercept-mirror`)**
   * **역할:** 전문 포트폴리오 수준의 사진 구도, 조명, 색감 기술 분석 및 깊이 있는 앙상블 비평/점수 산출.
   * **구동 백엔드:** PyTorch MPS (`bfloat16` 안정 정밀도).
   * **특징:** Hugging Face의 공식 공개 미러 저장소를 통해 토큰 인증 없이 100% 자동 다운로드를 지원합니다. `BaseKeepAliveModel` 기반 60초 Keep-alive 버퍼를 적용하고, 완료 후 `torch.mps.empty_cache()`를 통해 메모리를 회수합니다.

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
* **`mlx` & `mlx-vlm`**: Apple Silicon GPU 가속 기반으로 Gemma 4 모델을 로드하고 네이티브 텍스트/비전 추론을 처리하기 위한 코어 패키지.
* **`transformers>=4.49.0`**: SigLIP 2 및 최신 VLM 아키텍처 파싱을 위한 최신 허깅페이스 라이브러리.
* **`torch>=2.2.0`**: MPS(Metal Performance Shaders) 백엔드 가속을 사용하기 위한 파이토치 엔진.

### 🖥️ Apple Silicon GPU (Metal) 연동 검증
가상환경 내에서 아래 명령어를 실행하여 Metal 가속이 올바르게 잡혔는지 확인하십시오.
```bash
python3 -c "import mlx.core as mx; import torch; print('MLX:', mx.default_device()); print('Torch MPS:', torch.backends.mps.is_available())"
```
* **정상 결과:** `MLX: Device(gpu, 0)` 및 `Torch MPS: True`가 출력되면 성공입니다.

---

## 🤖 3. Gemma 4 설치 및 구동 방법 (MLX 네이티브)

* **공식 모델 식별자:** `mlx-community/gemma-4-12B-it-8bit`
* **동작 방식:** 백그라운드 인덱서 또는 AI 비평 요청 시 지연 로딩(Lazy Loading)되며, 작업 큐가 완전히 비워진 후 60초 Keep-alive 버퍼가 만료되면 자동으로 VRAM에서 해제됩니다.

---

## ⚡ 4. SigLIP 2 설치 및 구동 방법 (PyTorch MPS)

* **공식 모델 식별자:** `google/siglip2-base-patch16-224`
* **동작 방식:** 앱 기동 시 즉시 로드되어 메모리 상주(Keep-alive) 상태로 유지되며, 768차원 고속 임베딩 추출을 전담합니다.

---

## 🎨 5. UniPercept 8B 비평 모델 구동 및 메모리 관리 전략

* **공식 미러 식별자:** `widegather/unipercept-mirror`
* **토큰리스 자동 다운로드:** 공식 미러 저장소를 사용하여 Hugging Face 로그인 토큰 없이 원클릭 자동 다운로드가 수행됩니다.
* **메모리 수동/자동 언로드:** `BaseKeepAliveModel` 타이머(60초) 만료 시 자동 언로드되거나, `UniPerceptAdapter.unload_model()`을 호출하여 비평 직후 즉시 MPS 캐시 메모리를 반환할 수 있습니다.
