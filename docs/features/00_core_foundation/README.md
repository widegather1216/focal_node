# 🏛️ [00_core_foundation] Core Foundation & System Architecture

- **현재 상태 (Lifecycle)**: `🩹 Debugging (모델 다운로더 결함 DEFECT-01~04 해결 대기)`
- **구현 진척도**: `[■■■■] 4/4 Steps`
- **미해결 티켓 현황**: `🚨 DEFECT: 4건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
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

- **직전 완료 작업**: `2026-11-06 / deep-bug-hunter / 00_core_foundation 딥디버깅 결함 발권 (1cd1786 / 손상 인덱스 valid 오판 DEFECT-01, 실패 모델 무시 및 거짓 성공 이벤트 DEFECT-02, 미초기화 및 15초 폴링 블랙아웃 DEFECT-03, force=True 고아 스레드 및 HF 락 충돌 DEFECT-04)`
- **생성/수정된 핵심 파일**:
  - [`docs/features/00_core_foundation/verification.md`](./verification.md): `DEFECT-01~04` 4건 발권 및 테스트 매트릭스 갱신
  - [`docs/features/00_core_foundation/README.md`](./README.md): 도메인 수명주기 `🩹 Debugging` 전환
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_model_downloader.py backend/tests/test_backend_hardening.py backend/tests/test_concurrency_hardening.py`
  - `./venv/bin/pytest backend/tests/` (98 passed)
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `systematic-debugger` 스킬을 연결하여 `00_core_foundation`의 최우선 런타임 결함 `DEFECT-01`부터 순차 해결 권장 (`"00_core_foundation 도메인의 DEFECT-01 티켓 해결해줘"`).
