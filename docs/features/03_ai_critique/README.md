# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🟢 Verified (DEFECT-01 해결 완료, 리팩토링 티켓 3건 대기)`
- **구현 진척도**: `[■■■■] 4/4 Steps (Active Iteration Step 1~4 전 계층 구현 완료)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 3건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

2단계 온디맨드 AI 비평(UniPercept 8B 3-Way 채점/비평 ➔ Gemma 4 12B-it 한국어 번역/구조화), 미학 주도형 EXIF 적응적 종합 평점 모델, 정량 평점(`overall`/`iaa`/`iqa`/`ista`) 및 영문 원문(`critique_en`) DB 정규화, 캡션/태그 수동 편집, 백그라운드 비평 상태 Polling/취소/삭제, 포트폴리오 종합 총평 및 에디토리얼 매거진(Markdown/PDF) 내보내기를 담당하는 도메인입니다.

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
- [x] UniPercept 3대 정량 평점(`overall`/`iaa`/`iqa`/`ista`) 및 영문 원문(`critique_en`) DB 정규화 & 아카이브 정렬
  - 📂 구현: [`models.py`](../../../backend/app/models.py), [`database.py`](../../../backend/app/database.py), [`photo_repository.py`](../../../backend/app/repositories/photo_repository.py), [`chat_service.py`](../../../backend/app/services/chat_service.py), [`CritiqueCard.tsx`](../../../src/components/critique/CritiqueCard.tsx) | 🧪 테스트: [`test_critique_score_normalization.py`](../../../backend/tests/test_critique_score_normalization.py), [`test_critique_repository_and_api.py`](../../../backend/tests/test_critique_repository_and_api.py), [`test_critique_service_save.py`](../../../backend/tests/test_critique_service_save.py) (`PASS`)
- [x] **Step 1 [DB & Migration]**: `database.py`의 `run_migrations()`에 `image_metadata` 연계 `overall_score` 적응형 일괄 재계산 백필 로직 추가 및 `scoring.py` 순수 연산 모듈 분리
  - 📂 구현: [`database.py`](../../../backend/app/database.py), [`scoring.py`](../../../backend/app/services/scoring.py) | 🧪 테스트: [`test_adaptive_scoring.py`](../../../backend/tests/test_adaptive_scoring.py) (`TC-CRT-08`, `PASS`)
- [x] **Step 2 [Repo & API]**: `[N/A - 기존 API 및 리포지토리 계약 그대로 재사용]`
  - 📂 사유: DB 컬럼 및 REST 엔드포인트 규격 변경 없이 내부 계산식만 정밀화되므로 계층 변경 없음
- [x] **Step 3 [Domain Service]**: `unipercept_adapter.py`의 `_resolve_perceptual_weights`, `_calculate_aesthetic_bonus`, `_calculate_overall_vr_score` 구현 및 `chat_service.py` 연동 단위 테스트 작성
  - 📂 구현: [`unipercept_adapter.py`](../../../backend/app/services/unipercept_adapter.py), [`chat_service.py`](../../../backend/app/services/chat_service.py) | 🧪 테스트: [`test_adaptive_scoring.py`](../../../backend/tests/test_adaptive_scoring.py) (`TC-CRT-06~07`, `PASS`)
- [x] **Step 4 [UI & Integration]**: `ScoringGuideModal.tsx` 컴포넌트 추가 및 `CritiqueContentRenderer.tsx` 스코어보드 헤더에 `[?] 점수 산출 가이드` 버튼 연결
  - 📂 구현: [`ScoringGuideModal.tsx`](../../../src/components/critique/ScoringGuideModal.tsx), [`CritiqueContentRenderer.tsx`](../../../src/components/critique/CritiqueContentRenderer.tsx) | 🧪 검증: `npx tsc --noEmit && npm run build` (`TC-CRT-09`, `PASS`)

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **Recent Commits**:
  - `e99482f` - `fix(critique): force unload VLM models and synchronize MPS queue on cancellation`
  - `16aaff0` - `test(critique): add regression test cases for cancellation and MPS cache synchronization`
- **직전 완료 작업**: `2026-11-03 / systematic-debugger / 03_ai_critique 도메인 DEFECT-01 결함 해결 (비평 취소/중지 시 Gemma active_requests 가드 해제 force=True 지원, asyncio Task task.cancel() 신호 전달, PyTorch MPS torch.mps.synchronize() 동기화로 Metal 캐시 즉각 반환 및 100% 회귀 검증 통과)`
- **생성/수정된 핵심 파일**:
  - `backend/app/services/base_model.py`: [수정] `_unload_model_locked`에 `torch.mps.synchronize()` 추가
  - `backend/app/services/chat_service.py`: [수정] `_clear_device_caches` 동기화 보강, `_unload_critique_models(force=True)` 도입, `cancel_critique` 백그라운드 태스크 취소 연동
  - `backend/tests/test_critique_cancellation.py`: [수정] 결함 재현(Red) 및 검증(Green) 테스트 케이스 4건 추가
  - `docs/features/03_ai_critique/verification.md`: [수정] `TC-CRT-10` PASS 전환, `DEFECT-01` RESOLVED 동기화
- **검증 완료된 테스트 실행 명령어**:
  - `npm run build` (`tsc & vite build PASS`)
  - `./venv/bin/pytest backend/tests/test_critique_cancellation.py -v` (`8 passed`)
  - `./venv/bin/pytest backend/tests/test_critique_cancellation.py backend/tests/test_critique_sleep_recovery.py backend/tests/test_adaptive_scoring.py backend/tests/test_critique_score_normalization.py backend/tests/test_critique_repository_and_api.py backend/tests/test_critique_service_save.py -v` (`43 passed`)
- **다음 세션 포커스 및 추천 실행 프롬프트**:
  - `verification.md`에 등록된 `REFACTOR-01` (거대 컴포넌트 SRP 분할) 또는 다른 리팩토링 티켓을 진행합니다.
  - 👉 추천 프롬프트: `"03_ai_critique 도메인의 REFACTOR-01 리팩토링 티켓 해결해줘"`
