# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🛠️ Implementing (평점·영문원문 DB 정규화 Step 2 완료 / Step 3 대기 / REFACTOR 2건 대기)`
- **구현 진척도**: `[■■□□] 2/4 Steps (Active Iteration)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 2건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

2단계 온디맨드 AI 비평(UniPercept 8B 3-Way 채점/비평 ➔ Gemma 4 12B-it 한국어 번역/구조화), 정량 평점(`overall`/`iaa`/`iqa`/`ista`) 및 영문 원문(`critique_en`) DB 정규화, 캡션/태그 수동 편집, 백그라운드 비평 상태 Polling/취소/삭제, 포트폴리오 종합 총평 및 에디토리얼 매거진(Markdown/PDF) 내보내기를 담당하는 도메인입니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### ✅ Current Baseline (As-Is 기구현 완료)
- [x] `ai_analysis` 테이블, 비평 요청/응답/상태 스키마 및 프론트엔드 `CritiqueStatus` 타입
  - 📂 구현: [`models.py`](../../../backend/app/models.py), [`schemas.py`](../../../backend/app/schemas.py), [`critique.ts`](../../../src/types/critique.ts)
- [x] 온디맨드 비평 생성/Polling/취소/삭제/총평 라우터(`/api/chat/*`) 및 캡션/태그 수동 편집(`PATCH /api/photos/{id}/metadata`)
  - 📂 구현: [`chat.py`](../../../backend/app/api/chat.py), [`photos.py`](../../../backend/app/api/photos.py), [`api.ts`](../../../src/services/api.ts) | 🧪 테스트: [`test_critique_cancellation.py`](../../../backend/tests/test_critique_cancellation.py), [`test_critique_sleep_recovery.py`](../../../backend/tests/test_critique_sleep_recovery.py) (`PASS`)
- [x] `UniPerceptAdapter`(3-Way VR/VQA 및 즉시 언로드) ➔ `GemmaAdapter`(2-Pass 한국어 번역/구조화) 순차 파이프라인 및 4단계 진행률 매니저
  - 📂 구현: [`chat_service.py`](../../../backend/app/services/chat_service.py), [`critique_status.py`](../../../backend/app/services/critique_status.py), [`unipercept_adapter.py`](../../../backend/app/services/unipercept_adapter.py), [`mlx_adapters.py`](../../../backend/app/services/mlx_adapters.py) | 🧪 테스트: [`test_unipercept.py`](../../../backend/tests/test_unipercept.py), [`test_ensemble_math.py`](../../../backend/tests/test_ensemble_math.py) (`PASS`)
- [x] 상세 패널 비평 뷰, 전체 비평 대시보드, 에디토리얼 매거진 모달/독립 팝아웃 창 및 `html2canvas`+`jsPDF` 내보내기
  - 📂 구현: [`PhotoCritiqueView.tsx`](../../../src/components/detail/PhotoCritiqueView.tsx), [`PhotoAiAnalysisView.tsx`](../../../src/components/detail/PhotoAiAnalysisView.tsx), [`CritiqueView.tsx`](../../../src/components/CritiqueView.tsx), [`CritiqueContentRenderer.tsx`](../../../src/components/critique/CritiqueContentRenderer.tsx), [`CritiqueDocumentModal.tsx`](../../../src/components/critique/CritiqueDocumentModal.tsx)

### 🚀 Active Iteration: UniPercept 3대 정량 평점 & 영문 원문 DB 정규화 `[To-Be]`
- [x] **Step 1 [DB & Types]**: `models.py`의 `AIAnalysis`에 `overall_score`, `iaa_score`, `iqa_score`, `ista_score`(`Float`), `critique_en`(`String`) 추가, `database.py` 자동 마이그레이션/기존 텍스트 점수 백필(Backfill) 및 `schemas.py`/`src/types/critique.ts` 확장
  - 📂 구현: [`models.py`](../../../backend/app/models.py), [`database.py`](../../../backend/app/database.py), [`ai_parser.py`](../../../backend/app/services/ai_parser.py), [`schemas.py`](../../../backend/app/schemas.py), [`critique.ts`](../../../src/types/critique.ts) | 🧪 테스트: [`test_critique_score_normalization.py`](../../../backend/tests/test_critique_score_normalization.py) (`PASS`)
- [x] **Step 2 [Repo & API]**: `PhotoRepository.list_critiques(sort_by)`에 평점순 정렬(`overall_score`, `iaa_score`) 및 `delete_critique` 정규화 초기화 구현, `GET /api/chat/critiques` 응답에 정규화 평점/`critique_en` 연동, 프론트엔드 `ApiClient.getCritiques(sortBy?)` 타입 확장
  - 📂 구현: [`photo_repository.py`](../../../backend/app/repositories/photo_repository.py), [`chat.py`](../../../backend/app/api/chat.py), [`api.ts`](../../../src/services/api.ts) | 🧪 테스트: [`test_critique_repository_and_api.py`](../../../backend/tests/test_critique_repository_and_api.py) (`PASS`)
- [ ] **Step 3 [Service & State]**: `ChatService._save_critique_to_db`에서 `scores_dict`와 `raw_en`을 정규화 컬럼에 직접 저장하도록 개선
- [ ] **Step 4 [UI & Integration]**: `CritiqueContentRenderer.tsx`에서 정규화 점수/영문 원문 props를 우선 바인딩(레거시 정규식 폴백 유지)하고 `CritiqueView.tsx`에 `[최신순 / 종합평점순 / 미학점수순]` 정렬 토글 추가

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-10-24 / clean-code-developer / Step 2 [Repo & API] 완료: PhotoRepository.list_critiques(sort_by) 평점순 정렬 지원 및 delete_critique 정규화 초기화, GET /api/chat/critiques 응답에 정규화 4종 평점/critique_en 반영, ApiClient.getCritiques(sortBy) 타입 세분화, 신규 단위 테스트 9종 작성 및 도메인 회귀 40종·백엔드 82종 전수 통과`
- **생성/수정된 핵심 파일**:
  - `backend/app/repositories/photo_repository.py`: `list_critiques(sort_by)` 정렬 분기 및 `delete_critique` 정규화 컬럼 동시 초기화
  - `backend/app/api/chat.py`: `sort_by` Query 파라미터(`Literal["recent", "overall_score", "iaa_score"]`) 검증, `_to_critique_item_response` 헬퍼 추출 및 정규화 평점/영문원문 매핑
  - `src/services/api.ts`: `getCritiques(sortBy?: 'recent' | 'overall_score' | 'iaa_score'): Promise<CritiqueItem[]>` 타입 안전성 강화
  - `backend/tests/test_critique_repository_and_api.py`: 신규 단위 테스트 9종 작성
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_critique_repository_and_api.py backend/tests/test_critique_score_normalization.py backend/tests/test_unipercept.py backend/tests/test_ensemble_math.py backend/tests/test_critique_cancellation.py backend/tests/test_critique_sleep_recovery.py -v`
  - `npx tsc --noEmit && npm run build`
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - 다음은 **Step 3 [Service & State]** 차례임: `backend/app/services/chat_service.py`의 `_save_critique_to_db`에서 `scores_dict`(`overall`, `iaa`, `iqa`, `ista`)와 `raw_en`을 `ai_analysis` 테이블의 정규화 컬럼(`overall_score`, `iaa_score`, `iqa_score`, `ista_score`, `critique_en`)에 직접 저장하도록 개선할 것.
