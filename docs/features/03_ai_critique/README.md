# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🟡 In Progress (UniPercept 지각 앵커 + Gemma 4 직접 비평 하이브리드 파이프라인 기획 완료)`
- **구현 진척도**: `[■■□□] 2/4 Steps (Active Iteration Step 1~2 N/A 완료 / Step 3~4 대기)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 1건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

2단계 온디맨드 AI 비평(UniPercept 8B 3-Way 채점 + 단일 패스 통합 지각 앵커 ➔ Gemma 4 12B-it 지각 앵커 기반 한국어 직접 심층 비평), 미학 주도형 EXIF 적응적 종합 평점 모델, 정량 평점(`overall`/`iaa`/`iqa`/`ista`) 및 영문 원문(`critique_en`) DB 정규화, 캡션/태그 수동 편집, 백그라운드 비평 상태 Polling/취소/삭제, 포트폴리오 종합 총평 및 에디토리얼 매거진(Markdown/PDF) 내보내기를 담당하는 도메인입니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### 🚀 Active Iteration: UniPercept 지각 앵커 + Gemma 4 직접 심층 비평 하이브리드 파이프라인
- [x] **Step 1 [Schema & Types]**: `[N/A - 기존 DB 컬럼(critique, critique_en, 4종 평점) 및 프론트엔드 타입 100% 호환 재사용]`
- [x] **Step 2 [Data Access & API]**: `[N/A - 기존 POST /api/chat/critique 및 응답 스키마 100% 호환]`
- [ ] **Step 3 [Domain Service & Logic]**:
  - `ai_parser.py`: 단일 패스 통합 지각 앵커 프롬프트 및 Gemma 4 지각 앵커 기반 비평 프롬프트 정의
  - `unipercept_adapter.py`: 단일 패스 통합 지각 VQA 구현 및 디코딩 파라미터 정상화(`repetition_penalty=1.0`, `do_sample=True`, `temp=0.7`)
  - `mlx_adapters.py`: `generate_perceptual_critique` 신설 (지각 앵커 + EXIF + 사진 직접 결합 비평)
  - `chat_service.py`: `_execute_unipercept_critique_pipeline`을 앵커 기반 직결 파이프라인으로 개편
  - 📂 구현: [`chat_service.py`](../../../backend/app/services/chat_service.py), [`mlx_adapters.py`](../../../backend/app/services/mlx_adapters.py), [`unipercept_adapter.py`](../../../backend/app/services/unipercept_adapter.py), [`ai_parser.py`](../../../backend/app/services/ai_parser.py)
  - 🧪 테스트: [`test_unipercept.py`](../../../backend/tests/test_unipercept.py) (`TC-CRT-11~13`)
- [ ] **Step 4 [UI & Integration]**:
  - 프론트엔드 한/영 원문 토글 카드(`OriginalEnglishCritiqueCard.tsx`) 및 상세 패널 통합 회귀 검증
  - 🧪 검증: `npm run build` 및 엔드투엔드 비평 생성/취소 회귀 검증

### ✅ Previous Baseline (As-Is 기구현 완료)
- [x] `ai_analysis` 테이블, 비평 요청/응답/상태 스키마 및 프론트엔드 `CritiqueStatus` 타입
- [x] 온디맨드 비평 생성/Polling/취소/삭제/총평 라우터(`/api/chat/*`) 및 캡션/태그 수동 편집
- [x] UniPercept 3대 정량 평점 및 영문 원문 DB 정규화 & 아카이브 정렬
- [x] EXIF 적응형 4대 가중치, 미학적 탁월성 보너스 연산 모듈 및 점수 가이드 모달
- [x] 상세 패널 비평 뷰, 전체 비평 대시보드, 에디토리얼 매거진 모달/독립 팝아웃 창 및 내보내기

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **Recent Commits**:
  - `a9b398b` - `docs(critique): specify hybrid perceptual anchor pipeline with gemma 4 direct critique`
  - `756e6be` - `refactor(critique): eliminate silent fail blocks and decompose long adapter methods`
  - `1f0151c` - `refactor(critique): decompose monolithic critique components for SRP conformance`
- **직전 완료 작업**: `2026-11-04 / interactive-feature-planner / UniPercept 지각 앵커 + Gemma 4 직접 심층 비평 하이브리드 파이프라인 기획 및 위키(spec.md, architecture.md, decisions.md, verification.md) 갱신 완료`
- **기획된 핵심 변경 사항**:
  1. `UniPercept`: 3-Way VR 채점 + 단일 패스 통합 지각 VQA(3~4문장 앵커)로 경량화 (~10초, 어휘 붕괴 방지)
  2. `Gemma 4`: 2단계 번역 제거, UniPercept 점수+지각 앵커를 뼈대 삼아 직접 한국어 리포트(3대 헤더+실전조언) 작성 (~15초)
  3. 전체 생성 시간 기존 3~5분 ➔ 20~30초로 단축, 비평 품질 및 전문성 시너지 확보
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_unipercept.py -v` (`13 passed`)
  - `npm run build` (`PASS`)
- **다음 세션 포커스 및 추천 실행 프롬프트**:
  - `03_ai_critique` 도메인의 Step 3 개발(단일 패스 지각 앵커 및 직결 심층 비평 파이프라인 구현)을 진행합니다.
  - 👉 추천 프롬프트: `"03_ai_critique 도메인 Step 3 개발 진행해줘"`
