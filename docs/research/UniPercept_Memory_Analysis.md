# UniPercept RAM 30GB 점유 원인 정밀 분석 및 메모리 최적화 보고서
*(Analysis of UniPercept 30GB RAM Consumption and Memory Optimization Strategies)*

---

## 📌 요약 (Executive Summary)

UniPercept 모델 구동 시 시스템 메모리(RAM)가 약 **30GB에 육박하는 현상**은 메모리 누수(Memory Leak)가 아닌, **(1) 14B(140억 파라미터) 규모의 복합 VLM 구조**, **(2) 16-bit(bfloat16) 비양자화 원본 가중치 로드**, **(3) PyTorch MPS의 CPU-GPU 메모리 복제 현상**, **(4) 복수 AI 모델(Gemma, SigLIP)과의 메모리 누적**이 결합되어 발생하는 구조적 현상입니다.

본 보고서에서는 메모리 폭증의 4대 기술적 원인을 해부하고, 이를 **10GB 이하로 다이어트할 수 있는 실전 최적화 로드맵**을 제시합니다.

---

## 🔍 1. RAM 30GB 폭증의 4대 근본 원인

```
[ UniPercept 30GB RAM 점유 구조 분해 ]
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. InternViT-6B Vision Transformer (6B 가중치 @ bfloat16)        ➔ ~12.0 GB │
│ 2. Qwen2.5-8B Causal Language Model (8B 가중치 @ bfloat16)      ➔ ~16.0 GB │
│ 3. PyTorch .to("mps") 임시 CPU 버퍼 잔여 및 UMA 메모리 오버헤드 ➔  ~2.0 GB │
│ 4. 고해상도 타일링(Dynamic Patch=12) 및 어텐션 활성화 텐서      ➔  ~1.5 GB │
├─────────────────────────────────────────────────────────────────────────────┤
│ 💥 순수 가중치 및 런타임 합계:                                   약 31.5 GB │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 원인 1. 모델의 실제 크기: 8B가 아닌 '총 14B(140억 파라미터)' 거대 VLM

UniPercept는 단일 LLM이 아니라 **비전 인코더와 언어 모델이 결합된 초대형 앙상블 비전-언어 모델**입니다:

* **Vision Backbone:** `InternViT-6B` (약 60억 파라미터)
* **Language Model:** `Qwen2.5-8B` (약 80억 파라미터)
* **합계:** **총 140억 개 (14B) 파라미터**

#### 📊 데이터 정밀도(Dtype)별 순수 가중치 메모리 계산:
$$\text{Memory (GB)} = \text{Parameters (14B)} \times \text{Bytes per Parameter}$$

| 데이터 정밀도 (Precision) | 파라미터당 바이트 | 순수 가중치 크기 (Weight Size) | 비고 |
| :--- | :---: | :---: | :--- |
| **FP32 (float32)** | 4 Bytes | **56.0 GB** | CPU 단독 폴백 시 발생 가능 |
| **BF16 / FP16 (현재 상태)** | **2 Bytes** | **28.0 GB** | **현재 로드되어 있는 원본 상태** |
| **INT8 (8-bit 양자화)** | 1 Byte | **14.0 GB** | 양자화 적용 시 50% 절감 |
| **INT4 / 4-bit (AWQ/GPTQ)** | 0.5 Bytes | **7.0 GB** | 양자화 적용 시 75% 절감 |

> **결론:** 현재 16-bit(`bfloat16`) 원본 가중치로 모델을 올리고 있기 때문에, **디스크의 safetensors 파일 용량 합계(약 28GB)가 그대로 물리 RAM에 적재**되는 것이 정상적인 크기입니다.

---

### 원인 2. PyTorch `.to("mps")`의 CPU-GPU 메모리 이중 적재 오버헤드

Mac의 Apple Silicon은 CPU와 GPU가 하나의 물리 메모리를 공유하는 **통합 메모리 아키텍처(Unified Memory Architecture, UMA)**를 사용합니다.

그러나 PyTorch의 전통적인 모델 로딩 방식:
```python
# 1단계: CPU 메모리에 28GB 가중치 로드
self.model = AutoModel.from_pretrained(..., low_cpu_mem_usage=True) 

# 2단계: MPS(Metal GPU) 디바이스로 텐서 이동/복사
self.model = self.model.to("mps")
```
* **문제점:** 
  1. `from_pretrained`가 먼저 CPU RAM에 28GB 텐서를 생성합니다.
  2. `.to("mps")`가 이를 Metal GPU 셰이더 메모리로 복제합니다.
  3. CPU 측의 원본 텐서가 가비지 컬렉션(`gc.collect()`) 및 Metal 캐시 정리(`torch.mps.empty_cache()`)로 완전히 해제되기 전까지, **순간 피크 메모리가 30GB~35GB 이상으로 치솟는 현상**이 발생합니다.

---

### 원인 3. 복수 AI 모델(Gemma, SigLIP 2)과의 메모리 동시 공존

Focal Node는 단일 모델만 사용하는 것이 아니라 3개의 AI 모델이 유기적으로 협업합니다:

1. **SigLIP 2 (Keep-alive 상주):** 시각 검색 임베딩 추출 (~1.5 GB)
2. **Gemma 4 E4B-it (MLX):** 캡셔닝 및 비평 한국어 번역 (~4.5 GB)
3. **UniPercept (PyTorch MPS):** 14B 지각/화질/미학 평가 (~28.0 GB)

* **결과:** UniPercept가 구동되는 순간, 시스템에는 **28GB + 4.5GB + 1.5GB = 약 34GB의 AI 모델 메모리**가 동시에 올라가게 됩니다.

---

### 원인 4. Dynamic Patching(12개 타일)으로 인한 중간 Activation 텐서 증가

* `config.json`에 정의된 `max_dynamic_patch: 12`로 인해 고해상도 이미지가 입력되면 이미지가 최대 12개 타일로 분할됩니다.
* 이로 인해 **3,072개의 비전 토큰**이 28개 레이어의 Attention 연산을 통과하면서, Forward Pass 동안 중간 계산 결과(Activation Tensors)가 **추가로 1.5GB ~ 2.5GB의 런타임 메모리**를 점유합니다.

---

## 🛠️ 2. RAM 30GB ➔ 8~10GB 다이어트 4대 해결 방안

```
[ 메모리 다이어트 로드맵 ]
┌───────────────────────────┬──────────────┬──────────────┬──────────────┐
│ 최적화 단계               │ 가중치 크기  │ 런타임 RAM   │ 절감 효과    │
├───────────────────────────┼──────────────┼──────────────┼──────────────┤
│ 🔴 현재 (16-bit Unquant)  │ 28.0 GB      │ ~31.5 GB     │ 기준점       │
│ 🟡 8-bit 양자화 (INT8)    │ 14.0 GB      │ ~15.5 GB     │ -50% 절감    │
│ 🟢 4-bit 양자화 (AWQ/MLX) │ 7.0 GB       │ ~8.5 GB      │ -73% 절감    │
│ 🔵 Sequential Model Swap  │ 7.0 GB       │ ~7.5 GB      │ -76% 절감    │
└───────────────────────────┴──────────────┴──────────────┴──────────────┘
```

---

### 🚀 해결책 1. 4-bit / 8-bit 양자화 (Quantization) 적용 [가장 효과적]
14B 크기의 모델 가중치를 INT4(4비트) 또는 INT8(8비트)로 양자화하여 배포/로드합니다:
* **4-bit AWQ / GGUF / MLX 포맷 변환:**
  - 28GB ➔ **약 7.5GB**로 즉각 다이어트.
  - 지각적 평가 성능(SRCC/PLCC) 손실은 1~2% 미만으로 무시할 수 있는 수준.

---

### 🚀 해결책 2. Direct Device Allocation (CPU 복제 오버헤드 제거)
`accelerate`의 `device_map` 기능을 활용하여 CPU 경유 없이 바로 MPS/GPU 메모리로 가중치를 다이렉트 매핑합니다:
```python
self.model = AutoModel.from_pretrained(
    self.model_id,
    torch_dtype=torch.bfloat16,
    device_map="mps",          # CPU 임시 복사 단계 완전 생략
    low_cpu_mem_usage=True,
    trust_remote_code=True
)
```
* **효과:** 로딩 시 30GB 이상 치솟던 일시적 메모리 스파이크(Spike) 제거.

---

### 🚀 해결책 3. Dynamic Tile 수 조정 (`max_dynamic_patch: 12 ➔ 1~2`)
평가 시 12개 타일 분할 대신 448×448 단일 패치(또는 최대 2패치)로 제한하여 이미지 토큰 수를 3,072개 ➔ **256~512개**로 축소합니다.
* **효과:** 런타임 Activation 메모리 2GB 절감 및 추론 속도 대폭 향상.

---

### 🚀 해결책 4. 상호 배타적 모델 스왑 (Sequential Lifecycle Management)
비평 생성 파이프라인에서 UniPercept와 Gemma가 동시에 RAM에 머무르지 않도록 제어합니다:
1. **[1단계]** UniPercept 로드 ➔ 점수(VR) 및 영문 비평(VQA) 생성 ➔ **UniPercept 즉시 언로드(`del self.model`, `torch.mps.empty_cache()`)**
2. **[2단계]** Gemma 로드 ➔ 한국어 번역 및 정제 ➔ Gemma 완료
* **효과:** 28GB + 4.5GB의 동시 점유를 방지하여 최대 피크 메모리를 안전하게 억제.

---

## 📋 결론

현재 RAM 30GB 점유는 **14B 초대형 VLM이 16-bit 원본 정밀도(`bfloat16`)로 정상 로드되었을 때 필연적으로 발생하는 정직한 물리 메모리 크기**입니다.

향후 실사용 배포 시에는 **4-bit 양자화(AWQ/MLX 변환)** 및 **모델 스왑 라이프사이클**을 적용함으로써 **최대 8GB 이하**의 가벼운 메모리로 동일한 품질의 비평 기능을 제공할 수 있습니다.
