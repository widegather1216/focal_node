# 🏛️ [00_core_foundation] Core Foundation & System Architecture

- **현재 상태 (Lifecycle)**: `🩹 Debugging (DEFECT-07 해결 완료 — DEFECT-08~11 4건 해결 대기)`
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

- **직전 완료 작업**: `2026-11-17 / systematic-debugger / 00_core_foundation DEFECT-07 해결 및 회귀 검증 완료 (fccd313)`
- **조치 요약 (`DEFECT-07` RESOLVED)**:
  - `backend/app/services/base_model.py`: `BaseKeepAliveModel`에 `pending_unload` 및 `_defer_or_skip_unload_locked()`를 도입해 `active_requests > 0`일 때 `unload_model()`을 지연 해제(`pending_unload = True`)하고, `active_requests == 0`일 때만 즉시 언로드하도록 교정.
  - `backend/app/services/mlx_adapters.py` & `unipercept_adapter.py`: `_release_model_request()`·`_release_model_for_request()`가 `max(0, active_requests - 1)` 후 `self.lock` 해제 뒤 `pending_unload`/취소 상태에 따라 마지막 활성 요청 종료 시 즉시 언로드하도록 교정. `_run_mlx_vlm_generation()` `GPU_LOCK -> self.lock` 재적재 가드 및 `_acquire_model_for_request()` 취소 시 `active_requests == 0` 가드 추가.
  - `backend/app/services/chat_service.py`: `_has_active_requests()` 타입 가드로 활성 GPU 추론 중 무잠금 `_clear_device_caches()` 호출 차단(기존 `MagicMock` 취소 테스트 계약 보존).
  - `backend/tests/test_concurrency_hardening.py`: `TC-CF-08` 회귀 테스트 4종 추가(Gemma/UniPercept `active_requests > 0` 지연 해제·재적재 가드·취소 공존 보호·`active_requests == 0` 즉시 언로드).
- **남은 핵심 결함 (`DEFECT-08~11`, 4건)**:
  - `DEFECT-08` (🟠 P1): `huggingface_hub==1.21.0` `force_download=False` 단락으로 손상 인덱스/샤드 재다운로드 영구 실패
  - `DEFECT-09` (🟠 P1): `chroma.py` Self-Healing 시 `SharedSystemClient` 캐시 오염으로 `AttributeError: bindings` 크래시 및 `/api/index/sync` 벡터 누락 스킵
  - `DEFECT-10` (🟠 P1): `GemmaAdapter.generate_caption_and_tags` 예외 삼킴으로 빈 메타데이터 커밋 및 재인덱싱 영구 스킵
  - `DEFECT-11` (🟠 P1): Tauri IPC `save_binary_file` 무검증 임의 파일 쓰기 및 `tauri.conf.json` `"csp": null`
- **검증 명령어**: `./venv/bin/pytest backend/tests/test_concurrency_hardening.py backend/tests/test_critique_cancellation.py backend/tests/test_unipercept.py -v` (`40 passed`), `./venv/bin/pytest backend/tests/ -q` (`159 passed`), `npx tsc --noEmit` (`PASS`)
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `systematic-debugger`로 다음 P1 티켓 `DEFECT-08` 해결 진행 권장 (`"00_core_foundation 도메인의 DEFECT-08 티켓 해결해줘"`).
  - (교차 도메인 참고) `01_indexing_storage`의 `folder_manager.py#L50-L65` `purge_photo_records_batch`도 `db.commit()` 전 썸네일/Chroma 선삭제 경합이 존재함.
