# 🏛️ [00_core_foundation] Core Foundation & System Architecture

- **현재 상태 (Lifecycle)**: `🩹 Debugging (모델 다운로더 결함 DEFECT-04 해결 대기)`
- **구현 진척도**: `[■■■■] 4/4 Steps`
- **미해결 티켓 현황**: `🚨 DEFECT: 1건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

**Focal Node**의 전역 3-Tier 아키텍처, Tauri-FastAPI 동적 포트 브릿지, 하드웨어/런타임 6대 제약사항(`GPU_LOCK`, SQLite WAL, 모델 Keep-alive/즉시 언로드) 및 백그라운드 AI 모델 다운로더를 정의하는 헌법 도메인입니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### ✅ Baseline (As-Is 기구현 완료)
- [x] **Step 1 [Schema & Config]**: 환경별 데이터 경로 격리(`IS_PROD`), SQLite WAL & 외래키 리스너, 자동 스키마 마이그레이션(`run_migrations`) 및 ChromaDB Self-Healing 초기화
  - 📂 구현: [`config.py`](../../../backend/app/config.py), [`database.py`](../../../backend/app/database.py), [`chroma.py`](../../../backend/app/chroma.py), [`ports.py`](../../../backend/app/core/ports.py)
- [x] **Step 2 [Sidecar Host & System API]**: Tauri 동적 포트(`port=0`) 스폰/IPC 브릿지, 부모 프로세스 감시(`watch_parent`), `/api/health` 및 `/api/system/models/*` 라우트
  - 📂 구현: [`lib.rs`](../../../src-tauri/src/lib.rs), [`main.py`](../../../backend/app/main.py), [`process.py`](../../../backend/app/utils/process.py) | 🧪 테스트: [`test_backend_hardening.py`](../../../backend/tests/test_backend_hardening.py) (`PASS`)
- [x] **Step 3 [AI Lifecycle & Model Downloader]**: `GPU_LOCK` 직렬화, `BaseKeepAliveModel` 60초 타이머, HuggingFace 백그라운드 다운로더 및 진행률 트래커
  - 📂 구현: [`base_model.py`](../../../backend/app/services/base_model.py), [`ai_factory.py`](../../../backend/app/services/ai_factory.py), [`model_downloader.py`](../../../backend/app/services/model_downloader.py) | 🧪 테스트: [`test_model_downloader.py`](../../../backend/tests/test_model_downloader.py), [`test_concurrency_hardening.py`](../../../backend/tests/test_concurrency_hardening.py) (`PASS`)
- [x] **Step 4 [Client Bootstrapping & Splash UI]**: 포트 조회/헬스체크 훅, Tauri 네이티브 이벤트 리스너, 스플래시 및 모델 다운로드 모달
  - 📂 구현: [`App.tsx`](../../../src/App.tsx), [`useBackendInit.ts`](../../../src/hooks/useBackendInit.ts), [`useTauriEvents.ts`](../../../src/hooks/useTauriEvents.ts), [`useModelDownloadStatus.ts`](../../../src/hooks/useModelDownloadStatus.ts), [`AppSplash.tsx`](../../../src/components/common/AppSplash.tsx), [`ModelDownloadModal.tsx`](../../../src/components/ModelDownloadModal.tsx)

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-11-07 / systematic-debugger / DEFECT-03 해결 (13be25e / ModelDownloadStatusTracker KNOWN_MODEL_SIZES pending 사전 등록, _calculate_overall_progress 3개 모델 필수 검사 강제 및 useModelDownloadStatus 15초 폴링 블랙아웃 해소)`
- **생성/수정된 핵심 파일**:
  - [`backend/app/services/model_downloader.py`](../../../backend/app/services/model_downloader.py): `ModelDownloadStatusTracker`에 `KNOWN_MODEL_SIZES` pending/0% 사전 등록 및 `reset_statuses()` 신설
  - [`backend/app/main.py`](../../../backend/app/main.py): `_calculate_overall_progress`에서 `len(statuses) >= len(KNOWN_MODEL_SIZES)` 필수화 및 조기 `is_all_done: true` 방지
  - [`src/hooks/useModelDownloadStatus.ts`](../../../src/hooks/useModelDownloadStatus.ts): 대기/초기화 상태에서 2500ms 빠른 폴링 유지 및 `is_all_done` 불리언 판정 엄격화
  - [`backend/tests/test_model_downloader.py`](../../../backend/tests/test_model_downloader.py): `test_model_download_status_tracker_initial_pending_state`, `test_calculate_overall_progress_requires_all_known_models` 단위 테스트 추가
  - [`docs/features/00_core_foundation/verification.md`](./verification.md): `DEFECT-03` RESOLVED 및 `TC-CF-03` PASS 갱신
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_model_downloader.py` (8 passed)
  - `./venv/bin/pytest backend/tests/` (111 passed)
  - `npm run build` (tsc & vite build PASS)
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `systematic-debugger` 스킬을 연결하여 `00_core_foundation`의 차순위 런타임 결함 `DEFECT-04` 해결 권장 (`"00_core_foundation 도메인의 DEFECT-04 티켓 해결해줘"`).
