# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🩹 Debugging (Baseline 검증 완료 / REFACTOR 2건 대기)`
- **구현 진척도**: `[■■■■] 4/4 Steps`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 2건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

2단계 온디맨드 AI 비평(UniPercept 8B 3-Way 채점/비평 ➔ Gemma 4 12B-it 한국어 번역/구조화), 캡션/태그 수동 편집, 백그라운드 비평 상태 Polling/취소/삭제, 다중 사진 포트폴리오 총평 및 에디토리얼 매거진(Markdown/PDF) 내보내기를 담당하는 도메인입니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### ✅ Baseline (As-Is 기구현 완료)
- [x] **Step 1 [Schema & Types]**: `ai_analysis` 테이블(`critique`, `critique_updated_at`, `is_user_edited`), 비평 요청/응답/상태 스키마 및 프론트엔드 `CritiqueStatus` 타입
  - 📂 구현: [`models.py`](../../../backend/app/models.py), [`schemas.py`](../../../backend/app/schemas.py), [`critique.ts`](../../../src/types/critique.ts)
- [x] **Step 2 [Data Access & API]**: 온디맨드 비평 생성/Polling/취소/삭제/총평 라우터(`/api/chat/*`) 및 캡션/태그 수동 편집(`PATCH /api/photos/{id}/metadata`)
  - 📂 구현: [`chat.py`](../../../backend/app/api/chat.py), [`photos.py`](../../../backend/app/api/photos.py), [`api.ts`](../../../src/services/api.ts) | 🧪 테스트: [`test_critique_cancellation.py`](../../../backend/tests/test_critique_cancellation.py), [`test_critique_sleep_recovery.py`](../../../backend/tests/test_critique_sleep_recovery.py) (`PASS`)
- [x] **Step 3 [Domain Service & AI Adapters]**: `UniPerceptAdapter`(3-Way VR/VQA 및 즉시 언로드) ➔ `GemmaAdapter`(2-Pass 한국어 번역/구조화) 순차 파이프라인 및 4단계 진행률 매니저
  - 📂 구현: [`chat_service.py`](../../../backend/app/services/chat_service.py), [`critique_status.py`](../../../backend/app/services/critique_status.py), [`unipercept_adapter.py`](../../../backend/app/services/unipercept_adapter.py), [`mlx_adapters.py`](../../../backend/app/services/mlx_adapters.py) | 🧪 테스트: [`test_unipercept.py`](../../../backend/tests/test_unipercept.py), [`test_ensemble_math.py`](../../../backend/tests/test_ensemble_math.py) (`PASS`)
- [x] **Step 4 [UI & Editorial Export]**: 상세 패널 비평 뷰, 전체 비평 대시보드, 에디토리얼 매거진 모달/독립 팝아웃 창 및 `html2canvas`+`jsPDF` 내보내기
  - 📂 구현: [`PhotoCritiqueView.tsx`](../../../src/components/detail/PhotoCritiqueView.tsx), [`PhotoAiAnalysisView.tsx`](../../../src/components/detail/PhotoAiAnalysisView.tsx), [`CritiqueView.tsx`](../../../src/components/CritiqueView.tsx), [`CritiqueContentRenderer.tsx`](../../../src/components/critique/CritiqueContentRenderer.tsx), [`CritiqueDocumentModal.tsx`](../../../src/components/critique/CritiqueDocumentModal.tsx)

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-10-17 / clean-code-auditor / 2-모델 순차 비평 파이프라인 문서 동기화 및 코드 감사 티켓 발행`
- **생성/수정된 핵심 파일**:
  - `docs/features/03_ai_critique/*`: 4단계 비평 Polling 스키마, `DELETE /api/chat/critique/{photo_id}`, 팝아웃 윈도우 및 `save_binary_file` IPC 명세 반영
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_unipercept.py backend/tests/test_ensemble_math.py backend/tests/test_critique_cancellation.py backend/tests/test_critique_sleep_recovery.py`
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `REFACTOR-01` 해결 시 `CritiqueDocumentModal.tsx`(1,745줄)에서 프린트 HTML 생성(`generatePrintHtml`)과 Markdown/PDF 내보내기 유틸리티를 `src/utils/critiqueExporter.ts`로 먼저 분리할 것.
