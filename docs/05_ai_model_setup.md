# [Doc 5] AI 모델 설치 및 로컬 구동 가이드 (Apple Silicon)

본 문서는 Apple Silicon Mac (M 시리즈) 환경에서 **Gemma 4 E4B-it** 및 **SigLIP 2** 모델을 설치하고 GPU(Metal) 가속으로 구동하기 위한 상세 가이드를 제공합니다.

---

## 🏛️ 1. AI 모델 개요 및 아키텍처 상의 역할

본 프로젝트에서는 로컬 하드웨어 리소스를 극도로 절약하면서 자연어 시맨틱 검색과 오프라인 메타데이터 추출을 달성하기 위해 다음 두 가지 모델을 사용합니다.

1. **SigLIP 2 (google/siglip2-base-patch16-224)**
   * **역할:** 이미지 및 텍스트의 고차원 특징 임베딩 추출 (ChromaDB 저장 및 코사인 유사도 검색용).
   * **특징:** 비교적 가볍지만 강력한 이미지-텍스트 매칭 성능을 보장하며, Apple Silicon GPU(MPS) 가속을 통해 수 ms 단위의 속도로 연산이 가능합니다.
2. **Gemma 4 E4B-it (google/gemma-4-E4B-it)**
   * **역할:** 이미지의 상세 묘사(Caption) 생성 및 핵심 태그(tags) 리스트 자동 추출.
   * **특징:** 구글의 온디바이스 최적화 경량 멀티모달 VLM 모델입니다. 네이티브 `system` 롤을 지원하여 정형화된 JSON 형태의 시스템 지침을 오차 없이 수행합니다.

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
* **`mlx-lm`**: Apple Silicon GPU 가속 기반으로 Gemma 4 E4B-it 모델을 로드하고 텍스트/비전 추론을 처리하기 위한 코어 패키지.
* **`transformers>=4.49.0`**: SigLIP 2 최신 아키텍처 모델을 공식 파싱하고 로드하기 위한 최신 허깅페이스 라이브러리.
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

* **추천 모델 식별자:** `mlx-community/gemma-4-e4b-it-4bit`

### 파이썬 구현 코드 예시

```python
from PIL import Image
from mlx_lm import load, generate

# 1. 4-bit 양자화 모델 및 프로세서 로드
# (최초 실행 시 Hugging Face 캐시 디렉토리에 자동으로 다운로드됩니다)
model, processor = load("mlx-community/gemma-4-e4b-it-4bit")

# 2. 분석할 이미지 로드 및 RGB 변환
image_path = "path/to/your/photo.jpg"
image = Image.open(image_path).convert("RGB")

# 3. Gemma 4 system role을 활용한 지침 및 유저 메시지 구성
messages = [
    {
        "role": "system",
        "content": (
            "당신은 사진 검색 시스템을 위한 전문 AI 이미지 분석가입니다.\n"
            "마크다운 기호(예: ```json 등)나 추가적인 설명 없이 오직 아래 포맷만 출력하십시오.\n"
            "{\"caption\": \"사실적인 1~2줄 묘사\", \"tags\": [\"태그1\", \"태그2\"]}"
        )
    },
    {
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": "이 사진을 정밀 분석하여 JSON으로 출력하십시오."}
        ]
    }
]

# 4. 입력 데이터 텐서 변환 및 추론 수행
prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
output = generate(model, processor, prompt=prompt, images=[image], verbose=False)

print("출력 결과 JSON:", output)
```

---

## ⚡ 4. SigLIP 2 설치 및 구동 방법 (PyTorch MPS)

SigLIP 2 모델은 PyTorch의 MPS(Metal Performance Shaders)를 활용해 원본 모델을 메모리에 상주시킨 뒤 고속으로 임베딩 벡터를 추출합니다.

* **모델 식별자:** `google/siglip2-base-patch16-224`

### 파이썬 구현 코드 예시

```python
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModel

# 1. Metal(mps) 장치 지정 및 모델 로드
device = "mps" if torch.backends.mps.is_available() else "cpu"
model_id = "google/siglip2-base-patch16-224"

# SDPA(Scaled Dot-Product Attention) 활성화로 속도 극대화
model = AutoModel.from_pretrained(model_id, attn_implementation="sdpa").to(device)
processor = AutoProcessor.from_pretrained(model_id)

# 2. 이미지 및 비교 텍스트 준비
image = Image.open("path/to/your/photo.jpg").convert("RGB")
texts = ["비 오는 카페 풍경", "맑은 하늘과 바다"]

# 3. 전처리 후 GPU 메모리로 텐서 이동
inputs = processor(
    text=texts, 
    images=image, 
    padding="max_length", 
    return_tensors="pt"
).to(device)

# 4. 그라디언트 계산 없이 임베딩 텐서 추출
with torch.no_grad():
    outputs = model(**inputs)
    
    # 최종 특징 임베딩 (768차원 벡터)
    image_embeds = outputs.image_embeds # Shape: [1, 768]
    text_embeds = outputs.text_embeds   # Shape: [2, 768]

print("이미지 임베딩 벡터:", image_embeds[0].tolist()[:5]) # 일부 출력
```

---

## ⚠️ 5. 에이전트 구현 시 주의사항 (Troubleshooting)

1. **Python 아키텍처 정합성:**
   * Python 실행 환경이 Rosetta 2 환경이 아닌 네이티브 `arm64`로 빌드되었는지 터미널에서 `uname -p`로 재확인하십시오 (`arm` 출력 필수). Rosetta 환경의 경우 MLX 추론 중 세그멘테이션 오류나 속도 저하가 일어납니다.
2. **첫 로드 시 딜레이 방어:**
   * 모델 로드 시 수 기가바이트의 모델 가중치가 디스크에서 RAM으로 적재됩니다.
   * `04_implementation_constraints.md` 문서의 비동기 처리 지침에 따라, 모델 로딩 및 추론 함수를 실행할 때는 반드시 **`asyncio.to_thread()`**를 사용하여 FastAPI 비동기 루프의 블로킹(UI 프리징)을 철저히 차단하십시오.
