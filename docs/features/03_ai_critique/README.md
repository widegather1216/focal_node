# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🛠️ Implementing (평점·영문원문 DB 정규화 Step 1 완료 / Step 2 대기 / REFACTOR 2건 대기)`
- **구현 진척도**: `[■□□□] 1/4 Steps (Active Iteration)`
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
- [ ] **Step 2 [Repo & API]**: `PhotoRepository.list_critiques(sort_by)`에 평점순 정렬(`overall_score`, `iaa_score`) 지원 추가 및 `GET /api/chat/critiques` 응답에 정규화 평점/`critique_en` 반영
- [ ] **Step 3 [Service & State]**: `ChatService._save_critique_to_db`에서 `scores_dict`와 `raw_en`을 정규화 컬럼에 직접 저장하도록 개선
- [ ] **Step 4 [UI & Integration]**: `CritiqueContentRenderer.tsx`에서 정규화 점수/영문 원문 props를 우선 바인딩(레거시 정규식 폴백 유지)하고 `CritiqueView.tsx`에 `[최신순 / 종합평점순 / 미학점수순]` 정렬 토글 추가

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-10-20 / clean-code-developer / Step 1 [DB & Types] 완료: ai_analysis 정규화 컬럼 추가, run_migrations DDL/인덱스 생성 및 6-Way 스코어보드 자동 백필(Backfill), Pydantic/TypeScript 타입 확장, 단위 테스트 8종 작성 및 도메인 회귀 31종 전수 통과`
- **생성/수정된 핵심 파일**:
  - `backend/app/models.py`: `AIAnalysis`에 `overall_score`, `iaa_score`, `iqa_score`, `ista_score`, `critique_en` 추가 및 `to_detail_dict()` 반영
  - `backend/app/services/ai_parser.py`: `parse_scoreboard_scores` 스코어보드 정규식 파서 추가
  - `backend/app/database.py`: `run_migrations()` DDL 확장 및 `_backfill_critique_scores` 자동 백필 로직 구현
  - `backend/app/schemas.py`: `AIAnalysisSchema`, `CritiqueResponse`, `CritiqueItemResponse`, `CritiqueStatusResponse` 확장
  - `backend/app/services/critique_status.py`: 비평 진행/완료 상태에 정규화 점수 및 영문 원문 반영
  - `src/types/critique.ts`: `CritiqueItem`, `CritiqueStatus`, `CritiqueResponse` 인터페이스 확장
  - `src/hooks/usePhotoDetail.ts`: `ai_analysis` 상태 인터페이스 확장
  - `backend/tests/test_critique_score_normalization.py`: 파서, 마이그레이션, 자동 백필, 직렬화 단위 테스트 8종 신규 작성
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_critique_score_normalization.py backend/tests/test_unipercept.py backend/tests/test_ensemble_math.py backend/tests/test_critique_cancellation.py backend/tests/test_critique_sleep_recovery.py -v`
  - `npx tsc --noEmit && npm run build`
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - 다음은 **Step 2 [Repo & API]** 차례임: `backend/app/repositories/photo_repository.py`의 `list_critiques(sort_by="recent"|"overall_score"|"iaa_score")` 구현 및 `backend/app/api/chat.py`의 `GET /api/chat/critiques` 응답에 정규화 평점/`critique_en` 연동할 것.
