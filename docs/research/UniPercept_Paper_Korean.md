# UniPercept: 미학, 품질, 구조, 텍스처 전반의 통합 지각 수준 이미지 이해
*(UniPercept: Towards Unified Perceptual-Level Image Understanding across Aesthetics, Quality, Structure, and Texture)*

**저자:**  
Shuo Cao$^{1,2,*,\diamondsuit}$, Jiayang Li$^{3,*}$, Xiaohui Li$^{2,4}$, Yuandong Pu$^{2,4}$, Kaiwen Zhu$^{2,4}$, Yuanting Gao$^5$, Siqi Luo$^{2,4}$, Yi Xin$^{2,6}$, Qi Qin$^2$, Yu Zhou$^7$, Xiangyu Chen$^8$, Wenlong Zhang$^2$, Bin Fu$^2$, Yu Qiao$^2$, Yihao Liu$^{2,\dagger}$

**소속:**  
$^1$ 중국과학기술대학교 (University of Science and Technology of China)  
$^2$ 상하이 인공지능 연구소 (Shanghai AI Laboratory)  
$^3$ 베이징대학교 (Peking University)  
$^4$ 상하이교통대학교 (Shanghai Jiao Tong University)  
$^5$ 칭화대학교 (Tsinghua University)  
$^6$ 난징대학교 (Nanjing University)  
$^7$ 중산대학교 (Sun Yat-sen University)  
$^8$ Tele-AI  
$^*$ 동등 기여 (Equal contribution), $^\diamondsuit$ 상하이 AI Lab 인턴십 수행 연구, $^\dagger$ 교신 저자 (Corresponding author)

**프로젝트 리소스:**
- **웹사이트:** [https://thunderbolt215.github.io/Unipercept-project](https://thunderbolt215.github.io/Unipercept-project)
- **코드:** [https://github.com/thunderbolt215/UniPercept](https://github.com/thunderbolt215/UniPercept)
- **벤치마크 및 체크포인트:** [https://hf.co/collections/Thunderbolt215215/unipercept](https://hf.co/collections/Thunderbolt215215/unipercept)
- **arXiv 식별자:** `arXiv:2512.21675v1 [cs.CV] 25 Dec 2025`

---

## 📖 목차 (Table of Contents)

1. [초록 (Abstract)](#초록-abstract)
2. [1. 서론 (Introduction)](#1-서론-introduction)
3. [2. 관련 연구 (Related Works)](#2-관련-연구-related-works)
   - [2.1 MLLM 벤치마크 (MLLM Benchmark)](#21-mllm-벤치마크-mllm-benchmark)
   - [2.2 이미지 평가 (Image Assessment)](#22-이미지-평가-image-assessment)
4. [3. UniPercept-Bench (벤치마크 설계)](#3-unipercept-bench)
   - [3.1 정의 (Definition)](#31-정의-definition)
   - [3.2 벤치마크 구축 (Benchmark Construction)](#32-벤치마크-구축-benchmark-construction)
5. [4. UniPercept 모델 (UniPercept Model)](#4-unipercept)
   - [4.1 도메인 적응형 사전 학습 (Domain-Adaptive Pre-Training)](#41-도메인-적응형-사전-학습-domain-adaptive-pre-training)
   - [4.2 VR 및 VQA를 위한 태스크 정렬 강화학습 (Task-Aligned RL for VR & VQA)](#42-태스크-정렬-강화학습-task-aligned-rl-for-vr--vqa)
6. [5. 실험 및 결과 (Experiments)](#5-실험-및-결과-experiments)
   - [5.1 구현 세부사항 (Implementation)](#51-구현-세부사항-implementation)
   - [5.2 벤치마크 결과 및 분석 (Benchmark Results with Analysis)](#52-벤치마크-결과-및-분석-benchmark-results-with-analysis)
   - [5.3 UniPercept에 대한 추가 심층 논의 (Further Discussion on UniPercept)](#53-unipercept에-대한-추가-심층-논의-further-discussion-on-unipercept)
7. [6. 결론 및 한계점 (Conclusion & Limitations)](#6-결론-및-한계점-conclusion--limitations)
8. [참고문헌 요약 (References)](#참고문헌-references)
9. [부록 7. 지각 수준 이미지 이해의 통합 (Unifying Perceptual-Level Image Understanding)](#부록-7-지각-수준-이미지-이해의-통합)
10. [부록 8. ISTA의 세부사항 및 수식 (Details of ISTA)](#부록-8-ista의-세부사항-및-수식)
11. [부록 9. UniPercept-Bench 세부사항 및 프롬프트 (Details of UniPercept-Bench)](#부록-9-unipercept-bench-세부사항-및-프롬프트)
12. [부록 10. UniPercept 추가 논의 및 제거 연구 (Further Discussion & Ablation Studies)](#부록-10-unipercept-추가-논의-및-제거-연구)
13. [부록 11. UniPercept-Bench 추가 문항 예시 (Figure 11 상세)](#부록-11-unipercept-bench-추가-문항-예시)
14. [부록 12. UniPercept 생성 이미지 프로파일 (Figures 12, 13, 14 상세)](#부록-12-unipercept-생성-이미지-프로파일)
15. [전체 도메인 정의 테이블 (Tables 10, 11, 12 전수 수록)](#전체-도메인-정의-테이블)

---

## 초록 (Abstract)

다중 모달 대규모 언어 모델(MLLMs)은 시각적 위치 지정(visual grounding), 세분화(segmentation), 캡셔닝(captioning)과 같은 시각 이해 태스크에서 괄목할 만한 진전을 이루었습니다. 그러나 지각 수준(perceptual-level)의 이미지 특징을 지각하는 능력은 여전히 제한적입니다. 

본 논문에서는 세 가지 핵심 도메인인 **미학(Aesthetics), 품질(Quality), 구조 및 텍스처(Structure and Texture)** 전반의 지각 수준 이미지 이해를 위한 통합 프레임워크인 **UniPercept-Bench**를 제시합니다. 우리는 계층적 정의 체계를 수립하고 지각 수준 이미지 이해를 평가하기 위한 대규모 데이터셋을 구축하였습니다. 

이러한 기반 위에서, 우리는 **도메인 적응형 사전 학습(Domain-Adaptive Pre-Training)**과 **태스크 정렬 강화학습(Task-Aligned RL)**을 통해 훈련된 강력한 베이스라인 **UniPercept**를 개발하였으며, 이는 **시각적 평점 부여(Visual Rating, VR)**와 **시각적 질의응답(Visual Question Answering, VQA)** 태스크 전반에서 강력한 일반화 능력을 발휘합니다. 

UniPercept는 지각 수준 이미지 이해에서 기존 MLLM들을 크게 능가하며, **텍스트-이미지 생성(text-to-image generation)을 위한 플러그 앤 플레이(plug-and-play) 보상 모델**로 활용될 수 있습니다. 본 연구는 MLLM 시대의 '지각 수준 이미지 이해'를 공식 정의하고, 강력한 베이스라인과 함께 포괄적인 벤치마크를 도입함으로써 지각 수준 멀티모달 이미지 이해의 발전을 위한 견고한 토대를 제공합니다.

---

## 1. 서론 (Introduction)

최근 몇 년 동안 다중 모달 대규모 언어 모델(MLLM)은 급격한 발전을 거듭하여, 세분화, 시각적 접지(visual grounding), 이미지 캡셔닝, 시각적 추론 등 다양한 비전-언어 태스크 전반에서 인상적인 성능을 달성하고 있습니다. 이러한 진보는 주로 객체와 장면을 식별하고, 상호 관계를 포착하며, 시각적 추론을 수행할 수 있도록 의미 수준(semantic-level)의 표현을 학습하고 정렬하는 강력한 능력에 기인합니다.

그러나 의미론적 이해에 대한 광범위한 진전에도 불구하고, **인간이 미학, 품질, 구조, 텍스처를 어떻게 지각하는지에 대한 이미지의 지각 수준(perceptual-level) 이해는 여전히 실질적으로 미개척 상태**로 남아 있습니다. 

* **의미 수준 태스크 (Semantic-level tasks):** 시각적 개체에 대한 고차원적 해석(예: 객체 속성 식별, 맥락적 추론)에 초점을 맞춥니다.
* **지각 수준 태스크 (Perceptual-level tasks):** 미적 조화, 열화 심각도, 구조적 규칙성, 표면 텍스처와 같은 **세밀한 저수준(low-level) 시각적 외형**을 평가하는 것을 요구합니다. 이러한 지각적 속성은 본질적으로 미묘하고 주관적인 경우가 많으며 인간의 시각적 경험과 직결되어 있어 일반적인 의미 수준 태스크와는 근본적으로 다릅니다.

인간의 시각 지각은 단순한 객체 인식을 훨씬 능가합니다. 이미지가 어떻게 보이고 느껴지는지에 대한 섬세하고 미묘한 판단을 수반합니다. 이러한 지각적 단서는 콘텐츠 제작, 이미지 화질 개선, 생성 모델의 인간 선호 정렬과 같은 수많은 다운스트림 응용 분야에서 핵심적인 역할을 수행합니다. 그럼에도 불구하고 현재의 MLLM들은 미적 품질, 지각적 열화, 구조적 일관성을 평가할 때 불안정하거나 일관성 없는 예측을 내놓으며 이러한 영역에서 어려움을 겪고 있습니다. 

이러한 격차는 MLLM의 지각 수준 이해를 명시적으로 정의하고, 평가하며, 개선할 수 있는 통합 프레임워크의 필요성을 강력히 부각합니다. 왜냐하면 지각적 속성은 의미적 속성에 비해 표준화가 훨씬 덜 되어 있고 연구가 미진했기 때문입니다. 이 누락된 계층을 해결하는 것은 인간의 판단과 더 밀접하게 정렬되어 궁극적으로 더 높은 시각적 품질을 달성하는 모델을 구축하는 데 필수적입니다.

```
+----------------------------------------------------------------------------------------------------+
| [의미 수준 이해 (Semantic-level Understanding)] - 맥락과 의미 해석                                    |
|  - 객체 시각적 추론: "해변 근처의 사람들은 무엇을 보고 있는가?" -> "바다 너머로 지는 일몰."            |
|  - 이미지 캡셔닝: "장면을 자연어로 서술하라." -> "맑고 푸른 하늘 아래 정교한 첨탑과 석조 조각이 있는    |
|                     웅장한 대성당의 모습이며 광장에 사람들이 둘러서 있다."                           |
+----------------------------------------------------------------------------------------------------+
| [지각 수준 이해 (Perceptual-level Understanding)] - 외형과 품질 인지                                |
|  - 미학 평가: "시각적 균형을 평가하라." -> "고양이의 중앙 배치가 시각적 균형을 달성하는 핵심 요소이며   |
|                 시선을 집중시키는 초점(focal point) 역할을 수행함..."                             |
|  - 구조/텍스처 평가: "표면 텍스처를 평가하라." -> "불규칙한 주름과 접힘, 매트(matte) 마감이 특징인      |
|                      구겨진 질감의 표면을 묘사하고 있음..."                                        |
+----------------------------------------------------------------------------------------------------+
```

이 간극을 메우기 위해, 우리는 세 가지 핵심 도메인인 **이미지 미학 평가(IAA)**, **이미지 품질 평가(IQA)**, **이미지 구조 및 텍스처 평가(ISTA)** 전반을 다루는 최초의 통합 지각 수준 이미지 이해 프레임워크인 **UniPercept**를 제안합니다. 우리의 기여는 다음과 같이 요약됩니다:

1. **UniPercept-Bench:** 지각적 속성에 대해 **도메인(Domain) – 카테고리(Category) – 기준(Criterion)**의 점진적인 3단계로 구성된 포괄적인 계층적 분류 체계를 수립하였습니다. 이 분류 체계를 기반으로 MLLM의 지각 수준 이미지 이해를 체계적으로 평가하는 벤치마크인 `UniPercept-Bench`를 구축했습니다. 본 벤치마크는 세밀한 지각 속성을 다루며 **시각적 평점(VR)** 및 **시각적 질의응답(VQA)** 태스크를 모두 지원합니다.
2. **UniPercept 모델:** 대규모 **도메인 적응형 사전 학습(DAPT)**과 **태스크 정렬 강화학습(Task-Aligned RL)**을 통해 강력한 베이스라인 MLLM인 UniPercept를 개발했습니다. 추가적인 인간 피드백에 의존하지 않고도 다양한 시각 도메인에 걸쳐 지각적 속성을 신뢰성 있게 평가하는 능력을 학습합니다. VR과 VQA 모두에서 강력한 일반화 능력을 입증하며, IAA, IQA, ISTA 세 도메인 모두에서 SOTA 범용 및 특화 MLLM을 크게 상회합니다.
3. **UniPercept의 응용 (Applications):** 텍스트-이미지(T2I) 생성 모델의 사후 학습을 위한 강력한 플러그 앤 플레이 보상 모델로 기능하여, 미적 품질, 구조적 풍부함, 장면 다양성과 같은 지각 수준 신호의 직접적인 최적화를 가능하게 합니다. 또한 이미지 평가를 위한 통합 지각 지표이자 대규모 데이터셋의 지각 분포를 특성화하는 도구로도 활용됩니다.

---

## 2. 관련 연구 (Related Works)

### 2.1. MLLM 벤치마크 (MLLM Benchmark)
MLLM의 급속한 발전으로 모델 평가의 범위는 이미지 인식이나 세분화와 같은 단순한 의미 이해 작업을 훨씬 넘어섰습니다.
- **MMMU:** 다양한 학문 분야에 걸친 대학 수준의 시험 문제에 초점.
- **MMMU-Pro:** 복잡한 도메인 간 교차 추론 과제로 확장.
- **MEGA-Bench:** 대규모 멀티모달 이해 및 지식 통합 강조.
- **MMStar:** 시각적 맥락에서의 일반적 추론 및 사실적 이해 목표.
- **MMBench:** 일상 이미지 전반의 종합적인 지각 및 추론 평가.
- **MathVista:** 시각 장면 내 수학적/기하학적 추론 집중.
- **OCRBench:** 이미지에 포함된 텍스트의 인식 및 해석 능력 테스트.

그러나 이러한 기존 벤치마크들은 추론을 수행하기 전에 시각적 콘텐츠를 텍스트 표현으로 변환하는 것에 크게 의존하므로, 진정한 시각적 이해보다는 **언어 기반 추론을 강조**합니다. 이와 대조적으로 UniPercept-Bench는 기술적 실행력, 왜곡 위치, 재질 묘사와 같은 지각 수준의 시각적 속성을 직접 평가하여 지각적 이해와 의미적 이해 사이의 공백을 메웁니다.

### 2.2. 이미지 평가 (Image Assessment)
지각 수준의 이미지 평가와 관련하여 이전 연구들은 주로 두 가지 분야에 집중해 왔습니다:
1. **이미지 미학 평가 (IAA):** Q-Align, UNIAA, ArtiMuse 등.
2. **이미지 품질 평가 (IQA):** MUSIQ, DepictQA, DeQA, Q-Insight 등.

반면, 또 다른 핵심적인 지각 차원인 **이미지 구조 및 텍스처 평가 (ISTA)**는 체계적인 관심을 거의 받지 못했습니다. 소수의 선행 연구들이 구조적/텍스처적 지각의 일부 측면을 다루었으나, ISTA에 대한 통합적이거나 포괄적인 정의를 제시하지 못했습니다.

또한 대부분의 기존 데이터셋은 수치 점수 산출이나 단답형 질문 답변 등 단일 측면에만 초점을 맞추어 다차원적인 평가 프레임워크를 제공하지 못했습니다. 멀티모달 대형 모델이 지속적으로 발전함에 따라 기존 벤치마크에서는 이미 매우 높은 정확도를 달성하여 더 우수한 모델을 판별하는 변별력이 저하되었습니다. UniPercept-Bench는 다중 지각 차원을 아우르고 상세한 평가 데이터를 제공함으로써 이러한 한계를 극복합니다.

---

## 3. UniPercept-Bench

### 3.1. 정의 (Definition)
UniPercept-Bench는 세 가지 핵심 도메인을 평가합니다:
1. **IAA (이미지 미학 평가):** 구도, 스타일, 감정, 전반적 시각적 매력 등 인지된 미적 속성에 초점.
2. **IQA (이미지 품질 평가):** 노이즈, 블러, 압축 아티팩트, 전반적 왜곡 수준 등 인지된 충실도와 열화 요인 평가.
3. **ISTA (이미지 구조 및 텍스처 평가):** 기하학, 재질 특성, 국소 세부 묘사의 풍부함을 강조하며 장면의 구조적/텍스처적 특성 평가.

이 세 영역은 평가 대상이 근본적으로 다릅니다:
- 고품질(IQA가 높음) 이미지가 반드시 뛰어난 미적 가치(IAA)를 가지는 것은 아닙니다.
- 미적으로 매력적인(IAA가 높음) 이미지가 단순하거나 희소한 텍스처(ISTA가 낮음)만을 가질 수 있습니다.

### 3.2. 벤치마크 구축 (Benchmark Construction)

UniPercept-Bench는 **Domain – Category – Criterion**의 3계층 분류 체계로 구성됩니다 (3개 도메인, 17개 카테고리, 43개 세부 기준).

#### 1) 두 가지 상호보완적 태스크 형태
- **시각적 평점 부여 (Visual Rating, VR):** 모델이 0~100 사이의 연속형 점수를 출력하여 정량적 이해도를 측정합니다. ISTA의 경우 이미지에서 추출된 구조적 속성의 수를 집계/가중 합산하여 점수를 산출하는 방식을 설계했습니다.
- **시각적 질의응답 (Visual Question Answering, VQA):** 도메인-카테고리-기준 수준에서 구축된 질문들로 정성적 이해 및 설명적 추론 능력을 측정합니다.

#### 2) 데이터 생성 3단계 파이프라인
1. **초기 QA 생성 (Initial QA Generation):** 전문 평가 데이터셋(ArtiMuse, Q-Ground, DataDepictQA 등)을 기반으로, ISTA에 대해서는 구조적 주석을 생성합니다. 생성기 MLLM(GPT-4o)이 이미지, 주석, 질문 템플릿을 결합하여 후보 QA 쌍 및 추론 근거를 생성합니다.
2. **거절 샘플링 (Reject Sampling):** 이종 판별기 MLLM(Qwen-2.5-VL-78B-Instruct)이 질문 유효성, 답변 유효성, 추론 유효성, 기준 관련성을 5점 척도로 평가하여 하위 약 40%의 샘플을 제거합니다.
3. **인간 정제 (Human Refinement):** 이미지 평가 전문 훈련을 받은 자원봉사자들이 수동 검증 및 정제를 거쳐 최종 고품질 데이터셋을 완성합니다.

---

## 4. UniPercept 모델

UniPercept는 **InternVL3-8B**를 기본 백본으로 사용하며 2단계 학습을 거칩니다.

### 4.1. 도메인 적응형 사전 학습 (Domain-Adaptive Pre-Training, DAPT)
지각 수준 이해의 기초 능력을 형성하기 위해 약 **800K 샘플**로 구성된 사전 학습을 수행합니다:
- **텍스트 기반 QA 쌍:** IAA, IQA, ISTA에 대한 대규모 QA (ISTA의 경우 세부 구조 추론을 위한 구조화 JSON 출력 QA 포함).
- **VR 기반 QA 쌍:** 정량적 점수와 시각적 지각 속성을 직접 매핑하는 데이터.

### 4.2. 태스크 정렬 강화학습 (Task-Aligned RL for VR & VQA)
VR과 VQA의 정밀한 정렬을 위해 **GRPO(Group Relative Policy Optimization)** 알고리즘을 사용합니다.

#### 1) VQA 보상 함수 (Binary Reward)
$$r_{vqa} = \begin{cases} 1, & \text{예측된 답변이 정답인 경우} \\ 0, & \text{그 외의 경우} \end{cases} \quad (1)$$

#### 2) VR 보상 함수: 적응형 가우시안 소프트 보상 (Adaptive Gaussian Soft Reward)
정답과의 수치적 오차에 따라 연속적인 보상을 부여합니다:
$$r_{vr} = \exp\left( -\frac{(|p_i - g_i|)^2}{2\sigma_{dyn}^2} \right), \quad \sigma_{dyn} = \sigma_0 \left(1 + \alpha \frac{|p_i - g_i|}{100}\right) \quad (2)$$

- $p_i, g_i \in [0, 100]$: 예측 점수 및 정답 점수
- $\sigma_0$: 기본 평활화 계수
- $\alpha$: 적응형 평활도 제어 인자
- **Token As Score 전략:** 예측된 토큰의 확률 분포로부터 연속 점수를 역산출하여 회귀 안정성을 확보합니다.

#### 3) GRPO 최적화 목적 함수
$$J_{GRPO}(\theta) = \mathbb{E}_{B} \left[ \frac{1}{\sum_{i=1}^G |o_i|} \sum_{i=1}^G \sum_{t=1}^{|o_i|} r_i \cdot \min\left( r_t^i(\theta)\hat{A}_t^i, \; \text{clip}(r_t^i(\theta), 1-\epsilon, 1+\epsilon)\hat{A}_t^i \right) \right] \quad (3)$$

- $r_t^i(\theta) = \frac{\pi_\theta(o_t^i | q_i, o_{<t}^i)}{\pi_{old}(o_t^i | q_i, o_{<t}^i)}$: 정책 비율
- $\hat{A}_t^i$: 추정된 어드밴티지(Advantage)
- $r_i$: 식 (1) 또는 식 (2)의 태스크별 보상

---

## 5. 실험 및 결과 (Experiments)

### 5.1. 구현 세부사항 (Implementation)
- **평가 대상 (총 18개 모델):**
  1. *상용 독점 모델:* GPT-4o, Llama-4-Scout, Gemini-2.5-Pro, Claude-Sonnet-4.5, Claude-Sonnet-4.5-Think
  2. *오픈소스 선도 모델:* InternVL3/3.5 시리즈, QwenVL-2.5/3 시리즈, GLM-4.5-V, LLaVA-OneVision-1.5
  3. *특화 모델:* Q-Align, ArtiMuse, DeQA, Q-Insight
- **학습 파라미터:** 16장의 NVIDIA A100 GPU, 각 단계별 2 에포크, 배치 사이즈 128, GRPO 샘플 수 $n=8$, $\beta=0.001$, $\epsilon=0.2$, $\sigma=0.8$.

---

### 5.2. 벤치마크 결과 및 분석

#### 📊 표 1. UniPercept-Bench-VR (시각적 평점 평가) 성능 비교
*(평가지표: SRCC / PLCC — 스피어만 순위 상관계수 / 피어슨 선형 상관계수. * 표시는 ArtiMuse-10K, KonIQ-10K, ISTA-10K로 재학습된 모델)*

| 모델 분류 | 모델명 | ArtiMuse-10K [4] | AVA [38] | TAD66K [14] | FLICKR-AES [40] | VR-IAA 평균 | KonIQ-10K [15] | SPAQ [11] | KADID [30] | PIPAL [13] | VR-IQA 평균 | VR-ISTA (ISTA-10K) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **상용 독점** | GPT-4o | 0.333/0.276 | 0.509/0.485 | 0.278/0.282 | 0.605/0.597 | 0.431/0.410 | 0.695/0.744 | 0.874/0.881 | 0.677/0.646 | 0.325/0.349 | 0.643/0.655 | -0.003/0.116 |
| | Llama-4-Scout | 0.204/0.147 | 0.345/0.329 | 0.236/0.210 | 0.548/0.506 | 0.333/0.298 | 0.503/0.653 | -0.041/0.007 | -0.099/-0.004 | -0.007/0.023 | 0.089/0.170 | -0.025/0.047 |
| | Gemini-2.5-pro | 0.187/0.035 | 0.248/0.100 | 0.143/0.037 | 0.357/0.206 | 0.234/0.095 | 0.582/0.316 | 0.087/0.212 | 0.436/0.274 | 0.225/-0.019 | 0.333/0.196 | -0.230/-0.118 |
| | Claude-Sonnet-4.5 | 0.041/0.027 | 0.003/0.013 | 0.040/0.047 | 0.037/0.049 | 0.030/0.034 | -0.037/-0.043 | 0.036/0.085 | 0.223/0.273 | -0.131/-0.088 | 0.023/0.057 | 0.125/0.089 |
| | Claude-Sonnet-4.5-Think | 0.066/0.103 | 0.018/0.019 | 0.026/0.039 | -/- | 0.037/0.054 | -/- | -/- | -/- | -/- | -/- | -/- |
| **오픈소스** | LLaVA-OV-1.5-8B | 0.274/0.212 | 0.381/0.378 | 0.213/0.224 | 0.586/0.541 | 0.364/0.339 | 0.639/0.744 | -/- | 0.505/0.534 | 0.417/0.407 | 0.520/0.562 | -0.094/0.027 |
| | GLM-4.5-V-106B | 0.346/0.249 | 0.464/0.420 | 0.289/0.278 | 0.651/0.597 | 0.438/0.386 | 0.721/0.765 | -0.040/-0.038 | -0.142/-0.128 | 0.013/0.020 | 0.138/0.155 | 0.083/0.117 |
| | InternVL3-8B | 0.245/0.211 | 0.372/0.344 | 0.205/0.191 | 0.547/0.476 | 0.342/0.306 | 0.574/0.646 | 0.828/0.800 | 0.496/0.475 | 0.435/0.459 | 0.583/0.595 | -0.127/0.046 |
| | InternVL3-78B | 0.223/0.206 | 0.385/0.344 | 0.221/0.220 | 0.518/0.433 | 0.337/0.301 | 0.635/0.676 | 0.849/0.852 | 0.579/0.553 | 0.415/0.457 | 0.619/0.634 | -/- |
| | InternVL3.5-8B | 0.135/0.104 | 0.308/0.295 | 0.180/0.182 | 0.519/0.448 | 0.286/0.257 | 0.663/0.660 | 0.783/0.777 | 0.541/0.478 | 0.351/0.386 | 0.585/0.575 | -0.096/-0.025 |
| | InternVL3.5-38B | 0.219/0.175 | 0.359/0.357 | 0.201/0.208 | 0.559/0.529 | 0.334/0.317 | 0.578/0.652 | 0.840/0.831 | 0.568/0.537 | 0.448/0.457 | 0.608/0.619 | 0.262/0.345 |
| | QwenVL-2.5-7B | 0.223/0.143 | 0.359/0.324 | 0.208/0.195 | 0.588/0.520 | 0.345/0.296 | 0.708/0.762 | -/- | 0.521/0.517 | 0.350/0.361 | 0.526/0.547 | -0.046/0.076 |
| | QwenVL-2.5-72B | 0.233/0.197 | 0.408/0.387 | 0.232/0.235 | 0.626/0.589 | 0.375/0.352 | 0.762/0.820 | -/- | 0.606/0.570 | 0.381/0.407 | 0.583/0.599 | 0.091/0.148 |
| | QwenVL-3-8B | 0.156/0.094 | 0.280/0.170 | 0.191/0.121 | 0.507/0.388 | 0.283/0.193 | 0.761/0.822 | 0.612/0.604 | 0.723/0.696 | 0.434/0.427 | 0.633/0.637 | 0.033/0.044 |
| | QwenVL-3-32B | 0.227/0.130 | 0.353/0.198 | 0.200/0.095 | 0.572/0.413 | 0.338/0.209 | 0.796/0.838 | 0.690/0.657 | 0.673/0.682 | 0.414/0.402 | 0.643/0.644 | 0.084/0.106 |
| **특화 모델** | ArtiMuse [4] | 0.614/0.627 | 0.397/0.385 | 0.230/0.232 | 0.349/0.334 | 0.398/0.395 | -/- | -/- | -/- | -/- | -/- | -/- |
| | DeQA [69] | -/- | -/- | -/- | -/- | -/- | 0.953/0.941 | 0.895/0.896 | 0.694/0.687 | 0.472/0.478 | 0.753/0.750 | -/- |
| | Q-Align* [60] | 0.551/0.573 | 0.398/0.386 | 0.194/0.197 | 0.137/0.123 | 0.320/0.320 | 0.941/0.940 | 0.886/0.887 | 0.674/0.684 | 0.403/0.419 | 0.726/0.733 | -/- |
| | Q-Insight [27] | -/- | -/- | -/- | -/- | -/- | 0.933/0.916 | 0.907/0.905 | 0.742/0.736 | 0.486/0.474 | 0.767/0.758 | -/- |
| | Q-Insight* [27] | 0.228/0.175 | 0.405/0.376 | 0.212/0.217 | 0.617/0.537 | 0.366/0.326 | 0.733/0.750 | 0.800/0.938 | 0.580/0.548 | 0.369/0.368 | 0.621/0.651 | 0.060/0.152 |
| **우리 모델** | **UniPercept** | **0.746/0.738** | **0.589/0.577** | **0.336/0.346** | **0.688/0.681** | **0.590/0.586** | **0.940/0.949** | **0.904/0.895** | **0.872/0.870** | **0.581/0.594** | **0.824/0.827** | **0.778/0.767** |

---

#### 📊 표 2. UniPercept-Bench-VQA (IAA 미학 평가) 세부 성능 비교 (%)

| 모델 | Comp. | VisStr. | Tech. | Creat. | Theme. | Emo. | Gest. | CompEv. | Lv.Pred | How | What | Which | Why | Yes-No | 전체(Overall) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Random Guess | 23.08 | 27.27 | 21.95 | 29.63 | 25.93 | 22.86 | 23.68 | 32.56 | 24.14 | 21.28 | 30.43 | 25.32 | 24.00 | 29.49 | 25.17 |
| **상용 모델** | | | | | | | | | | | | | | | |
| GPT-4o | 64.62 | 59.57 | 57.58 | 60.19 | 65.19 | 67.62 | 51.95 | 30.23 | 38.86 | 78.17 | 72.46 | 62.66 | 72.67 | 70.51 | 60.04 |
| Llama-4-Scout | 62.56 | 68.45 | 59.76 | 61.11 | 57.78 | 70.48 | 48.68 | 32.56 | 43.97 | 70.92 | 69.57 | 61.39 | 77.33 | 70.51 | 60.91 |
| Gemini-2.5-pro | 71.79 | 68.45 | 61.59 | 76.85 | 67.41 | 63.81 | 61.84 | 37.21 | 45.98 | 78.72 | 73.91 | 67.72 | 84.67 | 84.62 | 66.44 |
| Claude-Sonnet-4.5 | 70.26 | 70.05 | 62.20 | 71.30 | 64.44 | 67.62 | 50.00 | 46.51 | 46.84 | 77.30 | 76.09 | 65.19 | 86.00 | 69.23 | 65.45 |
| Claude-Sonnet-4.5-T | 71.28 | 69.52 | 61.21 | 68.52 | 62.22 | 66.67 | 53.25 | 41.86 | 44.57 | 75.89 | 77.54 | 67.09 | 86.00 | 66.67 | 64.73 |
| **오픈소스 모델** | | | | | | | | | | | | | | | |
| LLaVA-OV-1.5-8B | 67.18 | 68.62 | 61.21 | 62.96 | 67.41 | 62.86 | 53.25 | 20.93 | 34.86 | 85.21 | 79.71 | 65.82 | 83.33 | 69.23 | 62.60 |
| GLM-4.5-V-106B | 67.18 | 65.78 | 60.98 | 75.00 | 64.44 | 68.57 | 51.32 | 46.51 | 45.40 | 71.63 | 78.26 | 65.82 | 84.67 | 70.51 | 64.46 |
| InternVL3-8B | 65.64 | 67.55 | 59.39 | 67.59 | 69.63 | 62.86 | 50.65 | 25.58 | 36.00 | 81.69 | 73.91 | 67.72 | 86.00 | 71.79 | 62.60 |
| InternVL3-78B | 71.79 | 73.26 | 61.21 | 73.15 | 74.81 | 74.29 | 53.25 | 37.21 | 45.14 | 85.82 | 81.16 | 72.15 | 86.00 | 75.64 | 68.28 |
| InternVL3.5-8B | 32.31 | 29.41 | 30.30 | 26.85 | 28.89 | 26.67 | 23.38 | 9.30 | 17.14 | 41.13 | 26.81 | 19.62 | 36.00 | 58.97 | 28.18 |
| InternVL3.5-38B | 37.44 | 40.11 | 27.88 | 39.81 | 34.81 | 38.10 | 45.45 | 6.98 | 34.00 | 47.52 | 26.09 | 28.48 | 37.33 | 50.00 | 35.67 |
| QwenVL-2.5-7B | 67.18 | 70.74 | 56.36 | 66.67 | 68.89 | 63.81 | 48.05 | 37.21 | 38.86 | 76.76 | 75.36 | 67.09 | 87.33 | 71.79 | 63.19 |
| QwenVL-2.5-72B | 22.05 | 24.60 | 25.45 | 29.63 | 30.37 | 18.10 | 19.48 | 6.98 | 14.00 | 19.86 | 17.39 | 24.05 | 41.33 | 51.28 | 23.74 |
| QwenVL-3-8B | 31.28 | 32.09 | 32.12 | 37.04 | 34.07 | 22.86 | 37.66 | 25.58 | 35.43 | 14.89 | 17.39 | 34.81 | 28.67 | 73.08 | 31.92 |
| QwenVL-3-32B | 23.08 | 26.74 | 32.12 | 26.85 | 32.59 | 20.95 | 33.77 | 20.93 | 33.43 | 9.22 | 13.77 | 31.01 | 18.67 | 66.67 | 27.39 |
| **특화 모델** | | | | | | | | | | | | | | | |
| ArtiMuse | 67.69 | 68.45 | 64.85 | 74.07 | 71.85 | 64.76 | 61.04 | 32.56 | 39.14 | 88.65 | 76.81 | 72.78 | 85.33 | 79.49 | 66.31 |
| **우리 모델** | **80.00** | **77.54** | **69.70** | **80.56** | **79.26** | **80.95** | **67.53** | **69.77** | **63.71** | **92.20** | **81.88** | **75.32** | **86.67** | **84.62** | **76.55** |

---

#### 📊 표 3. UniPercept-Bench-VQA (IQA 품질 평가) 세부 성능 비교 (%)

| 모델 | Loc. (위치) | Sev. (심각도) | Type. (유형) | Lv.Pred | How | What | Which | Why | Yes-No | 전체(Overall) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Random Guess | 23.67 | 24.75 | 20.08 | 24.75 | 27.03 | 16.05 | 25.00 | 21.39 | 22.99 | 23.16 |
| **상용 모델** | | | | | | | | | | |
| GPT-4o | 71.74 | 53.18 | 70.49 | 53.18 | 83.78 | 59.26 | 61.31 | 80.21 | 67.82 | 66.36 |
| Llama-4-Scout | 60.18 | 58.19 | 52.05 | 58.19 | 82.16 | 37.04 | 38.69 | 66.31 | 62.07 | 57.81 |
| Gemini-2.5-pro | 32.84 | 52.84 | 40.98 | 52.84 | 40.54 | 32.72 | 29.17 | 41.18 | 28.74 | 40.17 |
| Claude-Sonnet-4.5 | 71.19 | 51.51 | 66.80 | 51.51 | 90.81 | 50.00 | 50.60 | 82.89 | 71.26 | 64.80 |
| Claude-Sonnet-4.5-T | 71.19 | 55.52 | 66.80 | 55.52 | 89.19 | 50.00 | 51.79 | 82.89 | 72.41 | 65.90 |
| **오픈소스 모델** | | | | | | | | | | |
| LLaVA-OV-1.5-8B | 76.51 | 59.87 | 77.46 | 59.87 | 91.35 | 70.37 | 61.31 | 82.35 | 75.86 | 72.15 |
| GLM-4.5-V-106B | 70.09 | 35.79 | 54.51 | 35.79 | 88.11 | 48.77 | 44.05 | 74.33 | 68.97 | 57.17 |
| InternVL3-8B | 71.56 | 52.84 | 59.43 | 52.84 | 87.03 | 59.88 | 48.81 | 71.12 | 71.26 | 63.69 |
| InternVL3-78B | 75.41 | 51.84 | 81.56 | 51.84 | 93.51 | 66.67 | 63.10 | 88.24 | 66.67 | 70.31 |
| InternVL3.5-8B | 38.17 | 44.82 | 38.11 | 44.82 | 35.14 | 41.98 | 30.36 | 36.36 | 56.32 | 39.98 |
| InternVL3.5-38B | 38.90 | 49.83 | 45.08 | 49.83 | 46.49 | 41.36 | 31.55 | 33.16 | 62.07 | 43.29 |
| QwenVL-2.5-7B | 74.13 | 48.83 | 66.39 | 48.83 | 88.65 | 60.49 | 53.57 | 78.61 | 77.01 | 65.44 |
| QwenVL-2.5-72B | 31.01 | 4.68 | 16.39 | 4.68 | 35.14 | 14.81 | 11.31 | 22.99 | 66.67 | 20.50 |
| QwenVL-3-8B | 34.68 | 55.18 | 16.39 | 55.18 | 20.54 | 18.52 | 27.38 | 25.67 | 77.01 | 36.21 |
| QwenVL-3-32B | 29.54 | 14.38 | 16.80 | 14.38 | 11.89 | 18.52 | 25.60 | 22.46 | 74.71 | 22.52 |
| **우리 모델** | **77.43** | **79.60** | **90.98** | **79.60** | **87.03** | **80.86** | **75.60** | **83.42** | **79.31** | **81.07** |

---

#### 📊 표 4. UniPercept-Bench-VQA (ISTA 구조 및 텍스처 평가) 세부 성능 비교 (%)

| 모델 | Scene. (장면) | Phys. (물리) | Mat. (재질) | Geo. (기하) | Sem. (의미) | How | What | Which | Why | Yes-No | 전체(Overall) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Random Guess | 26.50 | 23.63 | 24.73 | 30.30 | 30.58 | 26.28 | 23.84 | 24.29 | 33.77 | 33.33 | 26.60 |
| **상용 모델** | | | | | | | | | | | |
| GPT-4o | 75.64 | 79.12 | 73.48 | 33.33 | 77.27 | 71.79 | 78.78 | 69.23 | 77.92 | 72.46 | 74.64 |
| Llama-4-Scout | 73.50 | 75.27 | 71.68 | 72.73 | 67.77 | 75.64 | 69.77 | 69.64 | 77.27 | 69.57 | 71.86 |
| Gemini-2.5-pro | 76.50 | 82.42 | 77.06 | 66.67 | 77.69 | 78.21 | 78.20 | 75.71 | 82.47 | 71.01 | 77.73 |
| Claude-Sonnet-4.5 | 76.92 | 78.57 | 74.91 | 90.91 | 77.69 | 76.92 | 77.03 | 74.49 | 81.82 | 79.71 | 77.32 |
| Claude-Sonnet-4.5-T | 77.35 | 78.02 | 73.12 | 87.88 | 75.21 | 76.28 | 74.71 | 74.09 | 81.82 | 76.81 | 76.08 |
| **오픈소스 모델** | | | | | | | | | | | |
| LLaVA-OV-1.5-8B | 78.63 | 85.16 | 82.44 | 72.73 | 80.17 | 83.33 | 81.40 | 75.30 | 84.42 | 88.41 | 81.13 |
| GLM-4.5-V-106B | 81.20 | 79.67 | 74.55 | 72.73 | 75.21 | 80.77 | 76.74 | 73.68 | 79.87 | 78.26 | 77.22 |
| InternVL3-8B | 75.64 | 79.12 | 73.48 | 33.33 | 77.27 | 71.79 | 78.78 | 69.23 | 77.92 | 72.46 | 74.64 |
| InternVL3-78B | 79.06 | 85.16 | 77.42 | 69.70 | 78.51 | 81.41 | 79.65 | 73.68 | 84.42 | 81.16 | 79.28 |
| InternVL3.5-8B | 54.27 | 50.55 | 58.42 | 39.39 | 36.36 | 46.79 | 56.69 | 48.58 | 29.87 | 71.01 | 49.79 |
| InternVL3.5-38B | 50.00 | 55.49 | 61.29 | 30.30 | 35.95 | 50.64 | 59.30 | 42.91 | 37.01 | 57.97 | 50.10 |
| QwenVL-2.5-7B | 74.79 | 72.53 | 74.91 | 51.52 | 73.55 | 73.72 | 77.33 | 66.80 | 74.03 | 73.91 | 73.30 |
| QwenVL-2.5-72B | 14.10 | 29.12 | 19.71 | 12.12 | 18.60 | 20.51 | 12.21 | 14.57 | 31.17 | 46.38 | 19.59 |
| QwenVL-3-8B | 27.78 | 32.42 | 25.45 | 39.39 | 24.79 | 14.74 | 23.26 | 28.34 | 25.32 | 81.16 | 27.63 |
| QwenVL-3-32B | 26.50 | 24.73 | 19.00 | 15.15 | 18.60 | 11.54 | 18.31 | 22.67 | 17.53 | 66.67 | 21.65 |
| **우리 모델** | **89.74** | **85.71** | **82.44** | **93.94** | **78.51** | **82.69** | **89.24** | **78.54** | **83.12** | **85.51** | **84.23** |

---

### 5.3. UniPercept에 대한 추가 심층 논의

#### 1) 텍스트-이미지 생성(T2I)을 위한 보상 모델로서의 UniPercept
UniPercept는 미학(IAA), 품질(IQA), 구조/텍스처 풍부도(ISTA)의 세 가지 시각적 평가 점수를 독립적으로 또는 통합하여 생성 모델 훈련의 보상 신호로 제공할 수 있습니다. 우리는 FLUX.1-dev 베이스라인 모델에 Flow-GRPO 파이프라인을 적용하여 미세조정 실험을 수행했습니다.

#### 📊 표 5. FLUX.1-dev w/ UniPercept Reward 성능 비교

| 모델 설정 | PickScore [22] | HPSv3 [36] | DeQA [69] | LAION-Aes [42] | ArtiMuse [4] | UniPercept-IAA | UniPercept-IQA | UniPercept-ISTA |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FLUX.1-dev Baseline** | 22.46 | 10.71 | 4.32 | 5.77 | 59.02 | 65.18 | 73.59 | 46.64 |
| + UniPercept IAA Reward | 22.47 | 10.09 | 4.09 | **6.19** | **67.02** | **76.20** | 76.39 | 54.83 |
| + UniPercept IQA Reward | 22.63 | **11.21** | **4.37** | 6.02 | 63.64 | 72.16 | 76.87 | 52.34 |
| + UniPercept ISTA Reward | **22.72** | 11.09 | **4.37** | 6.16 | 63.75 | 72.23 | 76.17 | **59.61** |
| **+ UniPercept Reward (All)** | 22.67 | 10.93 | 4.33 | **6.19** | 65.52 | 74.24 | **77.04** | 59.08 |

- **IAA 보상 단독:** 미학 지표(LAION-Aes: 6.19, ArtiMuse: 67.02)를 크게 끌어올립니다.
- **IQA 보상 단독:** 선명도 및 왜곡 제거 등 화질 지표(HPSv3: 11.21, DeQA: 4.37)에서 최대 향상을 나타냅니다.
- **ISTA 보상 단독:** 구조적/텍스처적 풍부함을 크게 향상시켜 ISTA 점수를 59.61까지 높입니다.
- **All (통합 보상):** 세 영역의 장점을 고루 결합하여 전반적인 시각적 완성도와 인간 선호도에서 가장 조화로운 결과를 얻습니다.

---

#### 2) T2I 모델 및 대규모 데이터셋에 대한 지각 평가 지표 (UniPercept Metrics)

#### 📊 표 6. DPG 메트릭 및 UniPercept 메트릭에 의한 T2I 모델 평가

| 모델명 | Global | Entity | Attribute | Relation | Other | DPG 전체 | UniPercept-IAA | UniPercept-IQA | UniPercept-ISTA | UniPercept 평균 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| OmniGen [62] | – | – | – | – | – | – | 62.83 | 72.22 | 45.09 | 60.04 |
| OmniGen2 [57] | 88.81 | 88.83 | 90.18 | 89.37 | 90.27 | 83.57 | 58.51 | 71.89 | 43.31 | 57.90 |
| BAGEL [10] | 88.94 | 90.37 | 91.29 | 90.82 | 88.67 | 85.07 | 60.20 | 70.52 | 45.78 | 58.83 |
| SANA-1.6B [63, 64] | 86.00 | 91.50 | 88.90 | 91.90 | 90.70 | 84.80 | 40.33 | 42.89 | 42.41 | 41.87 |
| Lumina-DiMOO [65] | 81.46 | 92.08 | 88.98 | 94.31 | 82.00 | 86.04 | 61.00 | 71.14 | 44.83 | 58.99 |
| FLUX.1-dev [25] | 74.35 | 90.00 | 88.96 | 90.87 | 88.33 | 83.84 | 65.18 | 73.59 | 46.64 | 61.80 |
| GPT-Image-1 [1] | 88.89 | 88.94 | 89.84 | 92.63 | 90.96 | 85.15 | 62.27 | 72.87 | 44.88 | 60.00 |
| Qwen-Image [56] | 91.32 | 91.56 | 92.02 | 94.31 | 92.73 | 88.32 | 62.89 | 72.15 | 47.23 | 60.76 |

#### 📊 표 7. GenEval 메트릭 및 UniPercept 메트릭에 의한 T2I 모델 평가

| 모델명 | Single Obj. | Two Obj. | Counting | Colors | Position | Attr. Bind. | GenEval 전체 | UniPercept-IAA | UniPercept-IQA | UniPercept-ISTA | UniPercept 평균 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| OmniGen [62] | 0.99 | 0.86 | 0.64 | 0.85 | 0.31 | 0.55 | 0.70 | 58.84 | 75.62 | 41.00 | 58.49 |
| OmniGen2 [57] | 0.99 | 0.96 | 0.74 | 0.98 | 0.71 | 0.75 | 0.86 | 54.20 | 75.16 | 34.48 | 54.61 |
| BAGEL [10] | 0.99 | 0.94 | 0.81 | 0.88 | 0.64 | 0.63 | 0.82 | 58.68 | 71.24 | 38.35 | 56.09 |
| SANA-1.6B [63, 64] | 0.99 | 0.77 | 0.62 | 0.88 | 0.21 | 0.47 | 0.66 | 34.34 | 35.11 | 31.22 | 33.56 |
| Lumina-DiMOO [65] | 1.00 | 0.94 | 0.85 | 0.89 | 0.85 | 0.76 | 0.88 | 51.93 | 71.98 | 30.86 | 51.59 |
| FLUX.1-dev [25] | 0.98 | 0.81 | 0.74 | 0.79 | 0.22 | 0.45 | 0.66 | 64.24 | 74.96 | 41.14 | 60.11 |
| GPT-Image-1 [1] | 0.99 | 0.92 | 0.85 | 0.92 | 0.75 | 0.61 | 0.84 | 69.07 | 76.74 | 51.26 | 65.69 |
| Qwen-Image [56] | 0.99 | 0.92 | 0.89 | 0.88 | 0.76 | 0.77 | 0.87 | 52.02 | 74.44 | 34.13 | 53.53 |

#### 📊 표 8. 다양한 이미지 데이터셋에 대한 UniPercept 지표 평가 결과

| 데이터셋 분류 | 데이터셋 명칭 | UniPercept-IAA | UniPercept-IQA | UniPercept-ISTA | 3개 도메인 평균 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **자연 이미지 (Natural)** | ImageNet [41] | 53.88 | 61.90 | 36.79 | 50.85 |
| | Unsplash [51] | 62.49 | 69.19 | 43.32 | 58.33 |
| | DF2K [18, 48–50] | 45.99 | 52.92 | 34.78 | 44.56 |
| | LAION-5B [43] | 60.56 | 69.21 | 38.85 | 56.21 |
| **AIGC 이미지** | Blip3o-60K [7] | 63.81 | 73.88 | 49.38 | 62.36 |
| | ImgEdit [66] | 55.83 | 59.77 | 36.88 | 50.83 |

---

## 6. 결론 및 한계점 (Conclusion & Limitations)

우리는 지각 수준 이미지 이해를 위한 계층적 정의에 기반한 통합 벤치마크인 **UniPercept-Bench**를 제공합니다. 또한 도메인 적응형 사전 학습과 태스크 정렬 강화학습을 통해 여러 지각 도메인 전반에서 우수한 일반화 성능을 발휘하고 기존 MLLM들을 압도하는 강력한 베이스라인 **UniPercept**를 개발했습니다. UniPercept는 T2I 모델의 사후 학습을 위한 플러그 앤 플레이 보상 모델로서 지각적 속성의 제어 가능한 개선을 가능하게 합니다. 아울러 체계적인 행동 양식과 데이터셋 수준의 패턴을 드러내는 통합 지각 진단 도구로서 향후 지각 수준 연구에 광범위한 유용성을 제공합니다.

**한계점 (Limitations):** UniPercept-Bench는 현재 지각 수준 태스크용으로는 충분히 방대하지만, 일반적인 의미 수준 벤치마크에 비해서는 규모가 상대적으로 작습니다. 데이터 규모의 추가 확장은 향후 연구 과제로 남겨둡니다.

---

## 참고문헌 (References)
*(핵심 인용 논문 발췌 요약)*
- `[1] GPT-4 Technical Report (OpenAI, 2023)`
- `[2] LLaVA-OneVision-1.5 (2025)`
- `[3] Qwen2.5-VL Technical Report (Alibaba, 2025)`
- `[4] ArtiMuse: Fine-grained image aesthetics assessment (Cao et al., 2025)`
- `[5] Q-Ground: Image quality grounding with large multi-modality models (Chen et al., 2024)`
- `[9] Describing textures in the wild - DTD (Cimpoi et al., CVPR 2014)`
- `[15] KonIQ-10k: An ecologically valid database for IQA (Hosu et al., IEEE TIP 2020)`
- `[25] FLUX.1 Kontext (Black Forest Labs, 2025)`
- `[27] Q-Insight: Understanding image quality via visual RL (Li et al., 2025)`
- `[32] Flow-GRPO: Training flow matching models via online RL (Liu et al., 2025)`
- `[44] DeepSeekMath: Pushing the limits of mathematical reasoning in open models (Shao et al., 2024)`
- `[60] Q-Align: Teaching LMMs for visual scoring via discrete text-defined levels (Wu et al., ICML 2024)`
- `[67, 68] DepictQA: Descriptive image quality assessment (You et al., ECCV 2024)`
- `[69] DeQA: Teaching LLMs to regress accurate image quality scores (You et al., CVPR 2025)`
- `[75] InternVL3: Exploring advanced training and test-time recipes (Zhu et al., 2025)`

---

## 부록 7. 지각 수준 이미지 이해의 통합

### 7.1. 의미론에서 지각으로 (From Semantics to Perception)
고수준 이미지 이해가 이미지가 '무엇을 묘사하는가'(객체, 행동, 장면 등)를 다룬다면, **지각 수준 이미지 이해는 이미지가 인간 관찰자에게 '어떻게 보이고 느껴지는가'**를 다룹니다. 이는 의미론적 콘텐츠의 인식 여부와 독립적인 시각 신호 본연의 속성을 포착합니다. 이미지는 의미론적으로 완전히 이해 가능하더라도 구도 불량, 압축 왜곡, 비현실적인 텍스처로 인해 지각적으로 결함이 있을 수 있습니다.

### 7.2. IAA, IQA, ISTA의 세부 설명
1. **IAA (미학 평가):** 가장 높은 지각적 추상화 계층. 구도(균형, 프레이밍, 3분할법, 시선 유도선), 시각 요소(조화, 노출, 분위기), 창의성(의도, 참신성), 감정(주제 소통, 스토리텔링)을 포함하며 인간의 심리에 크게 의존하므로 가장 주관적인 차원입니다.
2. **IQA (품질 평가):** 주관적 지각과 객관적 물리 신호 형성 과정을 연결. 신호 충실도(선명도, 노출, 색상 자연스러움), 아티팩트(블러, 노이즈, 압축 아티팩트, 앨리어싱), 지각적 무결함을 평가합니다.
3. **ISTA (구조 및 텍스처 평가):** 이미지가 구조적으로 일관되고 텍스처적으로 풍부한지를 결정하는 국소 지각 프리미티브 측정. 국소 구조(에지, 윤곽, 기하학적 일관성), 텍스처 통계(입상성, 반복성, 거칠기/매끄러움), 재질적 단서(직물 직조, 나뭇결 등)를 다룹니다.

### 7.3. 지각적 계층 구조 및 통합 이유
- IAA (거시적 아름다움/선호도, 고도의 주관성)
- IQA (기술적 충실도/왜곡, 객관/주관 혼합)
- ISTA (세밀한 구조 및 질감 사실성, 객관성 중심)

이 세 차원은 상호 보완적이지만 비중복적입니다. 통합의 5대 이점:
1. **공유 지각 표현:** 단일 범용 지각 임베딩 공간 형성.
2. **생성/복원 모델의 우수한 평가자:** 의미 지표를 넘어선 결함 진단.
3. **제어 가능한 생성/편집:** 화질 저하 없이 질감만 강화하는 등의 독립 축 제어.
4. **데이터셋 큐레이션:** 미학, 화질, 구조별 필터링 및 리웨이팅.
5. **인간 중심 응용:** 단순 의미가 아닌 인간 체감 품질 최적화.

---

## 부록 8. ISTA의 세부사항 및 수식

### 8.1. 구조적 주석 템플릿 및 프롬프트

#### ISTA 구조적 주석 JSON 스키마 (Figure 9)
```json
{
  "SceneType": "<SceneType: Single Scene 또는 Composite Scene>",
  "SceneName": "<SceneName: 장면 명칭>",
  "Components": [
    {
      "ComponentName": "<Component_1: 객체 명칭>",
      "DescriptionContent": {
        "PhysicalStructure": {
          "BaseMorphology": ["<기본 형태학 용어>"],
          "Arrangement": ["<배치/방향성>"]
        },
        "MaterialRepresentation": {
          "MaterialClass": ["<재질 분류>"],
          "SurfaceProperties": ["<표면 광학 속성>"]
        },
        "GeometricComposition": {
          "PlanarContour": ["<2D 평면 외곽선>"],
          "VolumetricForm": ["<3D 체적 형태>"]
        },
        "SemanticPerception": {
          "FunctionalInference": ["<기능적 추론>"],
          "StyleType": ["<스타일 분류>"]
        }
      }
    }
  ]
}
```

#### ISTA 사전 지식 베이스 (Prior Knowledge Base Lexicon)
- **기본 형태학 (Base Morphology - 42개 어휘):**  
  `blotchy` (얼룩덜룩한), `braided` (땋은), `bubbly` (거품 모양의), `bumpy` (울퉁불퉁한), `chequered` (체크무늬의), `cobwebbed` (거미줄 모양의), `cracked` (갈라진), `crosshatched` (교차선 무늬의), `crystalline` (결정질의), `dotted` (점박이의), `fibrous` (섬유질의), `flecked` (얼룩이 묻은), `freckled` (주근깨 모양의), `frilly` (주름장식의), `grid` (격자무늬의), `grooved` (홈이 파인), `honeycombed` (벌집 모양의), `interlaced` (얽힌), `knitted` (뜨개질한), `lacelike` (레이스 모양의), `lined` (줄무늬의), `marbled` (대리석 무늬의), `matted` (엉킨), `meshed` (그물망의), `paisley` (페이즐리), `perforated` (구멍 뚫린), `pitted` (오목하게 파인), `pleated` (주름잡힌), `porous` (다공성의), `scaly` (비늘 모양의), `smeared` (번진), `spiralled` (나선형의), `sprinkled` (흩뿌려진), `stratified` (층상의), `striped` (스트라이프), `studded` (박힌), `swirly` (소용돌이치는), `veined` (맥상의), `woven` (직조된), `wrinkled` (주름진), `zigzagged` (지그재그의), `smooth` (매끄러운).
- **재질 유형 (Material Type):**
  1. *천연 재질 (7종):* Foliage(나뭇잎), Grass(풀), Skin(피부), Stone(돌), Wood(나무), Water(물), Hair(모발).
  2. *인공 재질 (16종):* Brick(벽돌), Carpet(카펫), Ceramic(도자기), Fabric(직물), Glass(유리), Leather(가죽), Metal(금속), Mirror(거울), Painted Surface(도색 표면), Paper(종이), Plastic(플라스틱), Polished Stone(연마된 석재), Tile(타일), Wallpaper(벽지), Concrete(콘크리트), Food Surface(음식 표면).
  3. *환경/배경 텍스처 (3종):* Sky(하늘), Clouds(구름), Fog/Mist(안개/무무).
- **2차원 형태 (Two-Dimensional Shape - 25종):**  
  Rectangle, Square, Circle, Ellipse/Oval, Triangle, Equilateral Triangle, Isosceles Triangle, Scalene Triangle, Right Triangle, Trapezoid/Trapezium, Parallelogram, Rhombus, Pentagon, Hexagon, Heptagon, Octagon, Nonagon, Decagon, Star, Pentagram, Hexagram, Cross, Arrow, Semicircle, Sector, Crescent, Annulus/Ring, Heart, Lemniscate, Lune/Bow Shape, Spiral, Waveform, Teardrop.
- **3차원 형태 범주 (Three-Dimensional Shape Categories - 28종):**  
  Sphere, Ellipsoid, Cube, Cuboid, Cylinder, Cone, Pyramid, Tetrahedron, Octahedron, Dodecahedron, Icosahedron, Prism, Triangular Prism, Rectangular Prism, Pentagonal Prism, Hexagonal Prism, Torus, Annular Torus, Paraboloid, Hyperboloid, Elliptic Cylinder, Hyperbolic Cylinder, Truncated Cone, Truncated Pyramid, Capsule, Dome, Lens, Bipyramid, Frustum, Möbius Strip, Knot, Klein Bottle.
- **스타일 시맨틱 (Style Semantics - 13종):**  
  Embossed(양각), Engraved(음각), Rough(거친), Smooth(매끄러운), Matte(무광), Glossy(유광), Brushed(브러시 처리된), Honeycomb(벌집형), Geometric(기하학적), Fractal(프랙탈), Tile Mosaic(타일 모자이크), Chinese Cloud Pattern(중국 상운문), Dragon Scale(용 비늘), Cyberpunk Holographic(사이버펑크 홀로그램), Steampunk Mechanical(스팀펑크 기계식).

---

### 8.2. ISTA-10K 평점 산출 공식

#### 1) 텍스처 강도 매핑 함수 (Texture Intensity Mapping)
$$w(t) = \begin{cases} 1, & t \in T_{weak} \\ 2, & t \in T_{medium} \\ 3, & t \in T_{strong} \\ 0, & \text{그 외} \end{cases} \quad (4)$$

- **Weak (가중치 1):** `smooth`, `plain`, `uniform`, `lined`, `grid`, `striped`, `chequered`, `dotted`, `freckled` (9종)
- **Medium (가중치 2):** `braided`, `woven`, `crosshatched`, `meshed`, `cobwebbed`, `lacelike`, `knitted`, `spiralled`, `swirly` (9종)
- **Strong (가중치 3):** `bumpy`, `blotchy`, `bubbly`, `cracked`, `crystalline`, `flecked`, `frilly`, `grooved`, `honeycombed`, `marbled`, `matted`, `paisley`, `perforated`, `pitted`, `pleated`, `porous`, `scaly`, `smeared`, `sprinkled`, `stratified`, `studded`, `veined`, `wrinkled`, `zigzagged` (24종)

#### 2) 컴포넌트 단위 평점 산출
$$S(c) = S_{PS}(c) + S_{MR}(c) + S_{GC}(c) + S_{SP}(c) \quad (5)$$

각 하위 점수 공식 ("N/A" 항목 제외):
$$S_{PS}(c) = \sum_{t \in \text{BaseMorphology}(c)} w(t) + |\text{Arrangement}(c)| \quad (6)$$
$$S_{MR}(c) = |\text{MaterialClass}(c)| + |\text{SurfaceProperties}(c)| \quad (7)$$
$$S_{GC}(c) = |\text{PlanarContour}(c)| + |\text{VolumetricForm}(c)| \quad (8)$$
$$S_{SP}(c) = |\text{FunctionalInference}(c)| + |\text{StyleType}(c)| \quad (9)$$

#### 3) 이미지 단위 최종 ISTA 평점
- 컴포넌트 집합 $C$가 존재하는 복합 이미지:
  $$S_{ISTA} = |C| + \sum_{c \in C} S(c) \quad (10)$$
- 명시적 컴포넌트 분해가 없는 단일 이미지:
  $$S_{ISTA} = 1 + S(c_{image}) \quad (11)$$
- 최종 0~100 점수 범위 클리핑:
  $$S_{ISTA} \leftarrow \min(S_{ISTA}, 100) \quad (12)$$

---

## 부록 9. UniPercept-Bench 세부사항 및 프롬프트

### 시각적 평점 평가(VR) 전용 프롬프트
- **IAA 평가 프롬프트:**  
  `"Please rate the aesthetics of this image and provide a score between 0 and 100, where 0 represents the lowest quality and 100 represents the highest. Your response should contain only an integer value."`
- **IQA 평가 프롬프트:**  
  `"Please rate the quality of this image and provide a score between 0 and 100, where 0 represents the lowest quality and 100 represents the highest. Your response should contain only an integer value."`
- **ISTA 평가 프롬프트:**  
  `"Please rate the structure and texture richness of this image and provide a score between 0 and 100, where 0 represents the lowest quality and 100 represents the highest. Your response should contain only an integer value."`

---

#### 📊 표 13. 기존 벤치마크 및 데이터셋과의 비교

| 벤치마크명 | 테스트 수 (# Test) | QA 카테고리 수 | 데이터 형식 | 주석 수준 | 주석자 | IAA 지원 | IQA 지원 | ISTA 지원 | VQA 태스크 | VR 태스크 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **VQA 벤치마크** | | | | | | | | | | |
| Q-Bench [58] | ~1.5K | – | 텍스트 | 카테고리 수준 | 인간 | – | ✓ | – | ✓ | – |
| AesBench [17] | ~10K | 10 | 텍스트 | 예제 수준 | 인간 | ✓ | – | – | ✓ | – |
| DQ-495K [67] | ~56K | – | 텍스트 | 카테고리 수준 | 인간 & MLLM | – | ✓ | – | ✓ | – |
| Q-Instruct-DB [59] | – | – | 텍스트 | 카테고리 수준 | 인간 & MLLM | – | ✓ | – | ✓ | – |
| Co-Instruct [61] | – | – | 텍스트 | 카테고리 수준 | 인간 & MLLM | – | ✓ | – | ✓ | – |
| Q-Ground-100K [5] | ~1K | – | 텍스트 | 카테고리 수준 | 인간 & MLLM | – | ✓ | – | ✓ | – |
| **VR 벤치마크** | | | | | | | | | | |
| ArtiMuse-10K [4] | ~1K | 15 | 평점 & 텍스트 | 예제 수준 | 인간 | ✓ | – | – | – | ✓ |
| AVA [38] | ~20K | – | 평점 | 예제 수준 | 인간 | ✓ | – | – | – | ✓ |
| TAD66K [14] | ~15K | – | 평점 | 예제 수준 | 인간 | ✓ | – | – | – | ✓ |
| KonIQ-10K [15] | ~2K | – | 평점 | 예제 수준 | 인간 | – | ✓ | – | – | ✓ |
| SPAQ [11] | ~1K | – | 평점 | 예제 수준 | 인간 | – | ✓ | – | – | ✓ |
| KADID [30] | ~1K | – | 평점 | 예제 수준 | 인간 | – | ✓ | – | – | ✓ |
| **UniPercept-Bench (Ours)** | **~6K** | **44** | **평점 & 텍스트** | **예제 수준** | **인간 & MLLM** | **✓** | **✓** | **✓** | **✓** | **✓** |

---

## 부록 10. UniPercept 추가 논의 및 제거 연구

#### 📊 표 14. 도메인 적응형 사전 학습(DAPT) 데이터 개요 (총 약 800K)

| 도메인 | 데이터 유형 | 규모 | 원천 출처 |
| :--- | :---: | :---: | :--- |
| **IAA** | 텍스트 | ~360K | APDDv2 [19], Impressions [24], AVA [38], TAD66K [14], FLICKR-AES [40] |
| | 평점 | ~9K | ArtiMuse-10K [4] |
| **IQA** | 텍스트 | ~380K | Q-Ground-100K [5], DQ-495K [68], DataDepictQA [67, 68], SPAQ [11], KADID [30], PIPAL [13] |
| | 평점 | ~7K | KonIQ-10K [15] |
| **ISTA** | 텍스트 | ~40K | DTD [9], FMD [45], Big and Small Objects [23], Scene Size x Clutter Database [39], Reachspaces [20], Flickr2K [29], LSDIR [28] |
| | 구조화 주석 | ~40K | 상기 텍스트 데이터셋과 동일 이미지 |

#### 📊 표 15. 태스크 정렬 강화학습(Task-Aligned RL) 데이터 개요

| 도메인 | 태스크 | 규모 | 원천 출처 |
| :--- | :---: | :---: | :--- |
| **IAA** | VR | ~9K | ArtiMuse-10K [4] |
| | VQA | ~10K | UniPercept Data-VQA (train) |
| **IQA** | VR | ~7K | KonIQ-10K [15] |
| | VQA | ~10K | UniPercept Data-VQA (train) |
| **ISTA** | VR | ~10K | ISTA-10K |
| | VQA | ~10K | UniPercept Data-VQA (train) |

---

### 제거 연구 (Ablation Studies)

Q-Insight 방식의 임계값 기반 이진 보상 함수(Threshold-based Reward):
$$r_{thr}^{(i)} = \begin{cases} 1, & \text{if } |p_i - g_i| < \epsilon \\ 0, & \text{otherwise} \end{cases} \quad (13)$$

#### 📊 표 16. UniPercept-Bench-VR 제거 연구 결과 (SRCC / PLCC)

| 실험 조건 | IAA (ArtiMuse-10K) | IAA 평균 | IQA (KonIQ-10K) | IQA 평균 | ISTA (ISTA-10K) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **학습 전략 제거** | | | | | |
| w/ Threshold Reward (임계값 보상) | 0.604/0.556 | 0.617/0.596 | 0.882/0.888 | 0.801/0.790 | 0.303/0.334 |
| w/o Adaptive Pre-Training (DAPT 제거) | 0.546/0.510 | 0.481/0.421 | 0.851/0.817 | 0.733/0.700 | 0.755/0.732 |
| **학습 태스크 분리** | | | | | |
| VQA-Only (VQA 단독 학습) | 0.591/0.582 | 0.585/0.598 | 0.816/0.847 | 0.769/0.774 | 0.206/0.206 |
| VR-Only (VR 단독 학습) | 0.629/0.596 | 0.558/0.509 | 0.907/0.828 | 0.794/0.749 | 0.767/0.767 |
| **도메인 분리 학습** | | | | | |
| IAA-Only | 0.621/0.608 | 0.508/0.464 | 0.641/0.644 | 0.706/0.680 | 0.197/0.197 |
| IQA-Only | 0.369/0.352 | 0.468/0.435 | 0.901/0.839 | 0.786/0.726 | 0.341/0.337 |
| ISTA-Only | 0.351/0.319 | 0.275/0.288 | 0.595/0.575 | 0.611/0.570 | 0.771/0.782 |
| **UniPercept (Ours)** | **0.746/0.738** | **0.590/0.586** | **0.940/0.949** | **0.824/0.827** | **0.778/0.767** |

#### 📊 표 17. UniPercept-Bench-VQA 제거 연구 결과 (정확도, %)

| 실험 조건 | IAA 정확도 | IQA 정확도 | ISTA 정확도 | 전체 평균 (Avg.) |
| :--- | :---: | :---: | :---: | :---: |
| **학습 전략 제거** | | | | |
| w/ Threshold-based Reward | 72.32% | 76.29% | 81.65% | 76.75% |
| w/o Adaptive Pre-Training | 69.16% | 75.09% | 80.00% | 74.75% |
| **학습 태스크 분리** | | | | |
| VQA-Only | 71.92% | 76.29% | 81.44% | 76.55% |
| VR-Only | 68.57% | 68.38% | 75.15% | 70.70% |
| **도메인 분리 학습** | | | | |
| IAA-Only | 73.69% | 69.67% | 75.57% | 72.98% |
| IQA-Only | 64.73% | 76.01% | 77.53% | 72.76% |
| ISTA-Only | 69.56% | 69.58% | 82.27% | 73.80% |
| **UniPercept (Ours)** | **76.55%** | **81.07%** | **84.23%** | **80.62%** |

---

## 부록 11. UniPercept-Bench 추가 문항 예시

*(Figure 11에 수록된 18개 대표 질의응답 문항 전수 번역)*

### 1. IAA (미학 평가) 문항
1. **Composition & Design [위계적 강조 / What]:**
   - **Q:** 위계적 강조로 인해 이미지에서 가장 두드러지는 시각적 요소는 무엇인가?
   - **A:** 원형 내부의 문화적 복식 (Cultural attire within the circle)
2. **Emotion & Viewer Response [감정 수준 / Level Prediction]:**
   - **Q:** 이 사진에서 감정 및 관객 반응 품질에 대한 평가는 어떠한가?
   - **A:** 높음 (High)
3. **Technical Execution [재료 숙련도 / Why]:**
   - **Q:** 작가가 모란 꽃잎에 겹겹이 붓질(layered brushstrokes)을 한 이유는 무엇인가?
   - **A:** 자연스러운 꽃잎 표면을 시뮬레이션하기 위해 (Simulate natural petal surfaces)
4. **Originality & Creativity [창의적 문제 해결 / What]:**
   - **Q:** 이미지에서 웅장함을 느끼게 하는 데 가장 큰 영향을 미치는 구도적 결정은 무엇인가?
   - **A:** 수직적 레이어 강조 (Emphasizing vertical layers)
5. **Visual Elements & Structure [선 역동성 / Why]:**
   - **Q:** 선의 역동성이 원숭이의 장난스러운 표정과 포즈를 향상시키는 이유는 무엇인가?
   - **A:** 선들이 움직임과 흐름을 생성하기 때문 (Lines create movement and flow)
6. **Comprehensive Evaluation [종합 평가 / Level Prediction]:**
   - **Q:** 이 그림의 종합 평가 품질 수준은 어떠한가?
   - **A:** 높음 (High)

### 2. IQA (품질 평가) 문항
7. **Distortion Location [위치 설명 / How]:**
   - **Q:** 조명이 전경의 텍스처 가시성에 어떤 영향을 미치는가?
   - **A:** 돌의 텍스처 선명도를 향상시킴 (Enhances stone texture clarity)
8. **Distortion Location [위치 설명 / How]:**
   - **Q:** 나무 바닥과 고양이 털 사이의 공간적 선명도 차이는 어떠한가?
   - **A:** 바닥 결이 털 텍스처보다 더 선명함 (Floor grain is sharper than fur texture)
9. **Distortion Type [왜곡 유형 / Which]:**
   - **Q:** 색상 사실성에 영향을 미치는 왜곡 유형은 무엇인가?
   - **A:** YCrCb 채도 강화 왜곡 (Saturate strengthen YCrCb distortion)
10. **Distortion Type [왜곡 유형 / What]:**
    - **Q:** 이 이미지의 색상 표현에서 가장 두드러진 왜곡 유형은 무엇인가?
    - **A:** 과다 노출 (Over-Exposure)
11. **Distortion Severity [심각도 수준 / Level Prediction]:**
    - **Q:** 이미지 전반의 왜곡 심각도를 어떻게 평가하겠는가?
    - **A:** 약간 있음 (Slight - 간신히 인지 가능하나 존재함)
12. **Distortion Location [위치 설명 / What]:**
    - **Q:** 랜턴 표면에서 가장 눈에 띄는 구체적 왜곡은 무엇인가?
    - **A:** 텍스처 디테일을 가리는 블러 (Blurring obscuring texture details)

### 3. ISTA (구조 및 텍스처 평가) 문항
13. **Geometric Composition [2D 외곽선 / What]:**
    - **Q:** 벌집 구조에서 보이는 주요 2D 외곽선 모양은 무엇인가?
    - **A:** 육각형 (Hexagon)
14. **Geometric Composition [2D 외곽선 / Why]:**
    - **Q:** 이미지의 윤곽선이 나선형으로 분류되는 이유는 무엇인가?
    - **A:** 다중 루프를 가지고 있기 때문 (It has multiple loops)
15. **Physical Structure [기본 형태학 / What]:**
    - **Q:** 모래 장면의 표면 텍스처를 가장 잘 설명하는 용어는 무엇인가?
    - **A:** 홈이 파인 (Grooved)
16. **Semantic Perception [스타일 분류 / Which]:**
    - **Q:** 리무진 인테리어의 전반적인 시각적 테마를 가장 잘 설명하는 양식 분류는?
    - **A:** 현대적 럭셔리 (Modern Luxury)
17. **Material Representation [표면 거동 / Which]:**
    - **Q:** 표면 속성에서 가장 높은 광택(glossiness)을 나타내는 구성 요소는?
    - **A:** 연어 (Salmon)
18. **Material Representation [재질 식별 / Yes-No]:**
    - **Q:** 이미지의 텍스처가 시각적으로 금속(Metal)에 해당하는가?
    - **A:** 아니오 (No)

---

## 부록 12. UniPercept 생성 이미지 프로파일

UniPercept는 단일 이미지를 입력받아 **IAA / IQA / ISTA의 정량적 평점**과 함께 **세부 지각적 프로파일 텍스트**를 종합 생성합니다.

### 🖼️ 프로파일 예시 1: 극도로 흐린 정원 야경 (Figure 12)
- **UniPercept 평점:** **IAA: 29 / 100**, **IQA: 35 / 100**, **ISTA: 46 / 100**
- **미학 평가 (IAA):**
  - *구도 및 디자인:* 완전히 흐리고 불명확한 피사체로 인해 구도가 존재하지 않음. 요소들이 무작위로 흩어져 균형이나 리듬을 찾을 수 없음.
  - *기술적 실행:* 치명적인 기술적 결함을 노출. 극심한 블러로 인해 모든 디테일이 보이지 않으며 초점이 완전히 상실됨.
  - *종합 평가:* 시각적 응집력이 전무하여 미적 가치가 0에 수렴함.
- **품질 평가 (IQA):**
  - *왜곡 위치:* 파고라, 랜턴, 배경 식물을 포함한 전체 장면이 초점을 벗어나 선명도가 완전히 소실됨.
  - *왜곡 심각도:* 상상할 수 있는 최대치의 극심한 블러 왜곡.
  - *전반적 화질:* 피사체를 분별할 수 있는 디테일이 전무한 완전한 화질 실패.
- **구조 및 텍스처 평가 (ISTA):**
  - *장면 분해:* 흐린 복합 장면 (Blurred Composite Scene) - 파고라와 조명이 있는 정원.
  - *파고라:* 물리적 구조 [선형(Lined), 수평], 재질 [유리, 유광], 기하 형태 [구(Sphere)].
  - *배경 식물:* 물리적 구조 [엉킨(Matted), 적층], 재질 [잎, 무광], 기하 형태 [자연물].
  - *조명:* 물리적 구조 [매끄러움(Smooth), 군집], 재질 [유리, 유광], 기하 형태 [구(Sphere)].

---

### 🖼️ 프로파일 예시 2: 식민지풍 역사적 가옥 (Figure 13)
- **UniPercept 평점:** **IAA: 87 / 100**, **IQA: 75 / 100**, **ISTA: 56 / 100**
- **미학 평가 (IAA):**
  - *독창성 및 창의성:* 정통적이고 클래식한 프레젠테이션으로 잘 보존된 가옥을 표현. 실험성은 부족하나 전통적 기록 양식에 충실함.
  - *감정 및 관객 반응:* 역사적 건축에 대한 강한 향수와 감탄을 자아냄. 울창한 녹음과 고풍스러운 건물이 평화롭고 매력적인 분위기 조성.
  - *종합 평가:* 대칭 구도로 강렬한 시각적 임팩트를 제공하며 역사적/시각적 우수성이 돋보임.
- **품질 평가 (IQA):**
  - *왜곡:* 왜곡이 전혀 없음.
  - *전반적 화질:* 우수한 선명도와 생생한 색상. 균형 잡힌 구도, 정밀한 초점, 완벽한 노출. 결함 없는 고품질 사진.
- **구조 및 텍스처 평가 (ISTA):**
  - *장면 분해:* 복합 장면 - 주변 환경을 가진 역사적 가옥.
  - *본채(House):* 물리적 구조 [선형, 매끄러움, 수평], 재질 [목재, 무광], 기하 형태 [직사각형, 직육면체], 양식 [식민지 건축].
  - *지붕(Roof):* 물리적 구조 [타일형(Tiled), 적층], 재질 [타일, 무광], 기하 형태 [직사각형], 양식 [전통 양식].
  - *굴뚝(Chimneys):* 물리적 구조 [벽돌(Brick), 수직], 재질 [벽돌, 무광], 기하 형태 [직사각형, 직육면체], 양식 [전통 양식].

---

### 🖼️ 프로파일 예시 3: 레고 정글 신전 장면 (Figure 14)
- **UniPercept 평점:** **IAA: 75 / 100**, **IQA: 81 / 100**, **ISTA: 82 / 100**
- **미학 평가 (IAA):**
  - *시각 요소 및 구조:* 생생한 색상의 조화로운 조화. 정글의 녹색과 주황색 배경이 아름다운 대비를 이루며 피라미드와 캐릭터로 시선이 집중됨.
  - *주제 및 소통:* 인디아나 존스 스타일의 모험과 위험 요소를 정교한 레고 아트로 탁월하게 전달.
  - *종합 게슈탈트:* 레고 예술의 걸작으로서 모든 요소가 완벽하게 결합됨.
- **품질 평가 (IQA):**
  - *왜곡:* 블러, 과다노출, 압축 아티팩트가 전혀 없는 무결점 화질.
  - *전반적 화질:* 디테일과 입체감을 살리는 완벽한 조명과 구도.
- **구조 및 텍스처 평가 (ISTA):**
  - *장면 분해:* 복합 장면 - 레고 정글 신전.
  - *신전 구조:* 물리적 구조 [블록형(Blocky), 격자(Grid), 적층], 재질 [플라스틱, 무광], 기하 형태 [직사각형, 직육면체].
  - *야자수:* 물리적 구조 [섬유질(Fibrous), 주름장식(Frilly), 수직], 재질 [플라스틱, 무광], 기하 형태 [원기둥(Cylinder)].
  - *식물군(Flora):* 물리적 구조 [엉킨(Matted), 주름장식, 군집], 재질 [플라스틱, 무광].
  - *피규어:* 물리적 구조 [블록형, 군집], 재질 [플라스틱, 무광].

---

## 전체 도메인 정의 테이블

### 📋 표 10. IAA (이미지 미학 평가) 도메인 정의 세부사항 (31개 기준 전수)

| 번호 | 카테고리 | 기준 (Criterion) | 상세 설명 (Description) |
| :---: | :--- | :--- | :--- |
| 1 | Composition & Design (Comp.) | Visual Balance (시각적 균형) | 프레임 전반의 균형을 판단하기 위해 형상, 톤, 색상과 같은 시각적 요소의 분포를 평가. |
| 2 | Composition & Design | Hierarchical Emphasis (위계적 강조) | 크기, 대비, 위치에 기반하여 시각적 요소들의 상대적 중요도와 돌출도를 평가. |
| 3 | Composition & Design | Structural Organization (구조적 조직) | 이미지 프레임 내 요소들의 공간적 정렬, 그리드 일치성, 그룹화를 검토. |
| 4 | Composition & Design | Compositional Rhythm (구성적 리듬) | 시각적 템포를 암시하는 요소들의 반복, 간격, 방향적 연속성을 평가. |
| 5 | Composition & Design | Harmonic Unity (조화로운 통일성) | 형상 비율, 상대적 크기, 방향 패턴의 시각적 일관성을 평가. |
| 6 | Composition & Design | Composition & Design Level (구도 완성도 등급) | 균형, 리듬, 구조적 조화를 반영하는 전반적인 구도 품질 수준을 나타냄. |
| 7 | Visual Elements & Structure (VisStr.) | Line Dynamics (선 역동성) | 시각적 형태 형성에 기여하는 선화(linework)의 구조, 방향성, 밀도를 평가. |
| 8 | Visual Elements & Structure | Shape Clarity (형태 명확성) | 2D 형상 경계의 선명도 및 배경과의 분리도를 평가. |
| 9 | Visual Elements & Structure | Form Realization (입체 구현) | 음영, 조명 그래디언트, 원근 단서를 통한 3D 입체 표현의 완성도를 평가. |
| 10 | Visual Elements & Structure | Spatial Illusion (공간 착시) | 겹침(차폐), 크기 변화, 선형 원근법과 같은 깊이 단서를 판단. |
| 11 | Visual Elements & Structure | Light Modeling (조명 모델링) | 조명, 하이라이트, 그림자의 일관성과 사실성을 평가. |
| 12 | Visual Elements & Structure | Visual Elements & Structure Level (시각 요소 등급) | 선, 형상, 형태, 공간적 일관성을 포함한 기초 시각 요소의 숙련도를 측정. |
| 13 | Technical Execution (Tech.) | Material Proficiency (재료 숙련도) | 붓질 규율을 포함하여 표현 매체를 다루는 통제력과 정밀도를 평가. |
| 14 | Technical Execution | Rendering Precision (렌더링 정밀도) | 에지 정의, 그래디언트 전환, 마이크로 디테일의 정교함을 평가. |
| 15 | Technical Execution | Focus Control (초점 제어) | 시각적 위계를 구성하기 위한 선명도, 블러, 피사계 심도(DoF) 활용도를 판단. |
| 16 | Technical Execution | Tonal and Exposure Control (톤/노출 제어) | 휘도 분포와 톤 범위를 평가. |
| 17 | Technical Execution | Technical Execution Level (기술적 실행 등급) | 톤 제어, 정밀도, 렌더링 품질을 망라하는 기술적 숙련도를 표현. |
| 18 | Originality & Creativity (Creat.) | Concept Innovation (개념적 혁신) | 개념 또는 서사의 독창성을 평가. |
| 19 | Originality & Creativity | Creative Problem-Solving (창의적 문제 해결) | 시각적 실행이나 구도적 의사결정에서의 독창성을 평가. |
| 20 | Originality & Creativity | Originality & Creativity Level (독창성 등급) | 혁신성, 상상력, 개념적 고유성을 반영하는 창의적 역량을 표현. |
| 21 | Theme & Communication (Theme.) | Subject Clarity (주제 명확성) | 피사체 또는 전달 메시지의 명확성을 평가. |
| 22 | Theme & Communication | Narrative Depth (서사적 깊이) | 상징적 또는 서사적 다층성을 평가. |
| 23 | Theme & Communication | Cultural Insight (문화적 통찰) | 문화적, 역사적, 사회적 관념과의 연계를 판단. |
| 24 | Theme & Communication | Theme & Communication Level (주제 전달 등급) | 주제적 명확성과 소통 효과성을 평가. |
| 25 | Emotion & Viewer Response (Emo.) | Emotional Resonance (정서적 공명) | 정서적 톤과 관객의 정서적 반응을 평가. |
| 26 | Emotion & Viewer Response | Viewer Engagement (관객 몰입도) | 장기적으로 관객을 매료시키는 흡입력을 평가. |
| 27 | Emotion & Viewer Response | Interpretive Openness (해석적 개방성) | 해석을 유도하는 명확성과 모호성 사이의 균형을 판단. |
| 28 | Emotion & Viewer Response | Emotion & Viewer Response Level (감정 반응 등급) | 정서적 및 심리적 충격력을 측정. |
| 29 | Overall Gestalt (Gest.) | Holistic Cohesion (전체적 응집성) | 시각적, 개념적 요소들이 단일한 총체로 통합되는 정도를 평가. |
| 30 | Overall Gestalt | Overall Gestalt Level (게슈탈트 등급) | 모든 구성 요소 전반의 총체적 통합 수준을 표현. |
| 31 | Comprehensive Evaluation (CompEv.) | Comprehensive Evaluation Level (종합 평가 등급) | 지각적 품질과 개념적 깊이를 아우르는 모든 예술적 차원을 종합 평가. |

---

### 📋 표 11. IQA (이미지 품질 평가) 도메인 정의 세부사항 (4개 기준 전수)

| 번호 | 카테고리 | 기준 (Criterion) | 상세 설명 (Description) |
| :---: | :--- | :--- | :--- |
| 1 | Distortion Location (Loc.) | Location Description (위치 설명) | 왜곡이 보이거나 집중된 이미지 내의 특정 공간 영역을 정밀하게 식별하고 설명. 질문은 이미지 전체가 아닌 구체적인 부분을 명시적으로 참조해야 함. |
| 2 | Distortion Location | Object Association (객체 연계) | 왜곡에 의해 영향을 받거나 변형된 이미지 내의 의미적/구조적 객체를 지정. 질문은 일반적인 왜곡 유형이 아닌 구체적인 객체를 명시적으로 지정해야 함. |
| 3 | Distortion Severity (Sev.) | Severity Level (심각도 수준) | 가시성과 지각적 영향을 반영하여 왜곡 심각도를 없음(None), 약간(Slight), 뚜렷함(Obvious)의 3단계로 평가. |
| 4 | Distortion Type (Type.) | Distortion Types Present (존재하는 왜곡 유형) | 블러, 노이즈, 압축, 밝기, 대비, 채도, 샤프닝, 양자화, 노출, 픽셀화, 색상 번짐, 지터, 전송 에러 및 복합 왜곡을 포함하는 포괄적 분류 체계로부터 장면의 왜곡 유형을 식별. |

---

### 📋 표 12. ISTA (이미지 구조 및 텍스처 평가) 도메인 정의 세부사항 (9개 기준 전수)

| 번호 | 카테고리 | 기준 (Criterion) | 상세 설명 (Description) |
| :---: | :--- | :--- | :--- |
| 1 | Scene Decomposition (Scene.) | Scene Classification (장면 분류) | 장면을 (A) 단일 주요 피사체가 있는 단일 객체 장면 또는 (B) 구별 가능한 다중 컴포넌트가 포함된 복합 장면으로 분류하고 주요 객체를 명확히 기술. |
| 2 | Physical Structure (Phys.) | Base Morphology (기본 형태학) | 섬유질(fibrous), 홈이 파인(grooved), 대리석무늬(marbled), 맥상(veined), 매끄러움(smooth) 등의 지각적 설명어를 사용하여 표면 텍스처를 서술. |
| 3 | Physical Structure | Spatial Arrangement (공간적 배치) | 영역 전반에 걸친 텍스처 방향성, 분포 패턴, 밀도 변화를 서술 (예: 수평, 군집, 적층, 방사형, 균일). |
| 4 | Material Representation (Mat.) | Material Identification (재질 식별) | 표준화된 분류 체계(천연 재질, 인공 재질, 환경 재질)를 사용하여 이미지에 존재하는 인지된 재질 범주를 식별. |
| 5 | Material Representation | Surface Behavior (표면 거동) | 광택성(glossiness), 반투명성(translucency), 무광 마감(matte finish)과 같은 광학적 표면 속성을 서술. |
| 6 | Geometric Composition (Geo.) | 2D Contour (2D 외곽선) | 기본 형태, 다각형, 특수 형태, 유기적/곡선 형태를 포함하는 표준 어휘집을 사용하여 2D 외곽선 형상을 분류. |
| 7 | Geometric Composition | 3D Volume (3D 체적) | 기본 입체, 다면체, 각기둥, 복합 수학적 형상의 분류 체계를 사용하여 암시된 3D 체적 형태를 서술. |
| 8 | Semantic Perception (Sem.) | Functional Suggestion (기능적 암시) | 표준화된 기능적 텍스처/스타일 설명어를 참조하여 외형에 기반한 텍스처/모티프의 기능적 또는 상징적 함의를 추론. |
| 9 | Semantic Perception | Stylistic Classification (양식적 분류) | 시각적 요소와 장식적 단서에 기반하여 양식 범주(예: 미니멀리즘, 고딕, 아르데코, 미래주의, 사이버펑크, 중국 상운문)를 부여. |
