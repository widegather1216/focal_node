# 🏛️ [00_core_foundation] Core Foundation & System Architecture

- **현재 상태 (Lifecycle)**: `🩹 Debugging (DEFECT-10 해결 완료 — DEFECT-11 1건 해결 대기)`
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

- **직전 완료 작업**: `2026-11-17 / systematic-debugger / 00_core_foundation DEFECT-10 해결 및 회귀 검증 완료 (73f6c10)`
- **조치 요약 (`DEFECT-10` RESOLVED)**:
  - `backend/app/services/mlx_adapters.py`: `GemmaAdapter.generate_caption_and_tags()`에서 `RuntimeError` 시 `logger.error` + `clear_mlx_cache(); gc.collect()` 복구 후 `raise`, 일반 `Exception`도 로깅 후 `raise`하도록 교정해 빈 딕셔너리(`{"caption": "", "tags": [], "aesthetic_tags": []}`) 은폐 반환 제거(`finally`의 `_release_model_request()`가 `active_requests` 안전 해제).
  - 연쇄 영향 검증: `pipeline.py` `AIInferenceStep.execute()`와 `indexing_service.py` `index_single_file_sync()`가 실패 파일 1건만 `"error"`로 격리해 동일 청크의 정상 파일 커밋 및 전체 인덱싱 루프를 보존하고, 실패 파일은 SQLite/ChromaDB에 미저장되어 다음 `/api/index/sync` 시 재시도됨을 실증(`reindex_single_photo_inplace()` 기존 DB 데이터 보존 포함).
  - `backend/tests/test_backend_hardening.py`: `TC-CF-11` 회귀 테스트 2종(`test_tc_cf_11_gemma_caption_inference_raises_and_clears_cache`, `test_tc_cf_11_pipeline_error_isolation_and_sync_retry`) 추가.
- **남은 핵심 결함 (`DEFECT-11`, 1건)**:
  - `DEFECT-11` (🟠 P1): Tauri IPC `save_binary_file` 무검증 임의 파일 쓰기 및 `tauri.conf.json` `"csp": null`
- **검증 명령어**: `./venv/bin/pytest backend/tests/test_backend_hardening.py -k "tc_cf_11" -v` (`2 passed`), `./venv/bin/pytest backend/tests/ -q` (`166 passed`), `npx tsc --noEmit` (`PASS`)
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `systematic-debugger`로 마지막 P1 티켓 `DEFECT-11` 해결 진행 권장 (`"00_core_foundation 도메인의 DEFECT-11 티켓 해결해줘"`).
  - (교차 도메인 참고) `01_indexing_storage`의 `folder_manager.py#L50-L65` `purge_photo_records_batch`도 `db.commit()` 전 썸네일/Chroma 선삭제 경합이 존재함.
