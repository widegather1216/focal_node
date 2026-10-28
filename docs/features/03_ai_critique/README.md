# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🟢 Sign-Off 대기 (미학 주도형 EXIF 적응적 평점 개편 Step 1~4 완료)`
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

- **직전 완료 작업**: `2026-10-28 / clean-code-developer / 03_ai_critique 도메인 Step 4 [UI & Integration] 구현 완료 (ScoringGuideModal.tsx 컴포넌트 신규 구현 - 3대 지각 지표 정의 및 ISTA 밀도 안내, 4대 EXIF 가중치 표, 미학 보너스 안내, ESC/백드롭 닫기 지원; CritiqueContentRenderer.tsx 스코어보드 헤더 우측에 [?] 점수 산출 가이드 버튼 및 모달 렌더링 연결; TC-CRT-09 검증 완료; npx tsc --noEmit 및 npm run build 통과; 도메인 회귀 56종 및 백엔드 98종 전수 통과; Step 1~4 전 계층 구현 완료로 spec.md/architecture.md As-Is 승격 병합 완료)`
- **생성/수정된 핵심 파일**:
  - `src/components/critique/ScoringGuideModal.tsx`: [신규] 3대 지각 지표, 4대 EXIF 적응형 가중치 표, 미학적 탁월성 보너스 안내 모달 컴포넌트
  - `src/components/critique/CritiqueContentRenderer.tsx`: [수정] 스코어보드 헤더에 `[?] 점수 산출 가이드` 버튼 및 `ScoringGuideModal` 오픈/해제 상태 연결
  - `docs/features/03_ai_critique/spec.md`: Step 1~4 완료에 따른 To-Be ➔ As-Is 승격 병합
  - `docs/features/03_ai_critique/architecture.md`: 컴포넌트 파일 트리 [기존] 갱신
  - `docs/features/03_ai_critique/verification.md`: TC-CRT-09 `PASS` 및 인수 통과율 100%(4/4) 갱신
  - `docs/features/03_ai_critique/README.md`: Step 4 [x] 완료 및 Handoff 갱신
  - `docs/README.md`: Master Control Tower Spotlight 및 현황판 갱신
- **검증 완료된 테스트 실행 명령어**:
  - `npx tsc --noEmit && npm run build` (`PASS`, Vite v7.3.6 프로덕션 번들 정상 생성)
  - `./venv/bin/pytest backend/tests/test_adaptive_scoring.py backend/tests/test_critique_repository_and_api.py backend/tests/test_critique_service_save.py backend/tests/test_critique_cancellation.py backend/tests/test_critique_sleep_recovery.py backend/tests/test_ensemble_math.py backend/tests/test_unipercept.py backend/tests/test_critique_score_normalization.py -v` (`56 passed`)
  - `./venv/bin/pytest backend/tests/` (`98 passed`)
- **다음 세션 포커스 및 추천 실행 프롬프트**:
  - `03_ai_critique` 도메인의 모든 구현 Step(Step 1~4)이 완료되었습니다. `clean-code-auditor` 스킬을 통해 전체 계층 정적 분석 및 클린코드 품질 감사를 진행합니다.
  - 👉 추천 프롬프트: `"03_ai_critique 도메인 클린코드 품질 감사 진행해줘"`
