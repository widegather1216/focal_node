# 🏛️ [00_core_foundation] Core Foundation & System Architecture

- **현재 상태 (Lifecycle)**: `🩹 Debugging (DEFECT-08 해결 완료 — DEFECT-09~11 3건 해결 대기)`
- **구현 진척도**: `[■■■■] 4/4 Steps`
- **미해결 티켓 현황**: `🚨 DEFECT: 3건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
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

- **직전 완료 작업**: `2026-11-17 / systematic-debugger / 00_core_foundation DEFECT-08 해결 및 회귀 검증 완료 (eed8ba5)`
- **조치 요약 (`DEFECT-08` RESOLVED)**:
  - `backend/app/services/model_downloader.py`: `_force_redownload_files()`·`_remove_corrupted_snapshot_pointer()`·`_repair_sharded_files()`를 도입해 손상된 `*.index.json` 및 누락/손상(`<=1MB`) 샤드 포인터만 선제거 후 `force_download=True`로 재수신하고(정상 완료 대용량 샤드 보존), 인덱스 복구 후 드러난 누락 샤드까지 연쇄 복구.
  - `backend/app/services/model_downloader.py`: 단일 가중치 모델(`_find_undersized_weight_files`, 내부 심볼릭 링크 제외) `<=1MB` 손상 복구, 불완전/무인덱스 스냅샷 `snapshot_download(..., force_download=True)` 폴백, `_is_model_cached()`의 `local_files_only=True`·`force_download=True` 동시 전달 차단을 추가.
  - `backend/tests/test_model_downloader.py`: `TC-CF-09` 회귀 테스트 3종(손상 `index.json` 및 `<1MB` 샤드 `force_download=True` 복구, 단일 가중치 복구 및 `_is_model_cached`/`hf_transfer` kwargs 보존, 실제 `huggingface_hub==1.21.0` 캐시 단락 우회 검증) 추가.
- **남은 핵심 결함 (`DEFECT-09~11`, 3건)**:
  - `DEFECT-09` (🟠 P1): `chroma.py` Self-Healing 시 `SharedSystemClient` 캐시 오염으로 `AttributeError: bindings` 크래시 및 `/api/index/sync` 벡터 누락 스킵
  - `DEFECT-10` (🟠 P1): `GemmaAdapter.generate_caption_and_tags` 예외 삼킴으로 빈 메타데이터 커밋 및 재인덱싱 영구 스킵
  - `DEFECT-11` (🟠 P1): Tauri IPC `save_binary_file` 무검증 임의 파일 쓰기 및 `tauri.conf.json` `"csp": null`
- **검증 명령어**: `./venv/bin/pytest backend/tests/test_model_downloader.py -v` (`13 passed`), `./venv/bin/pytest backend/tests/ -q` (`162 passed`), `npx tsc --noEmit` (`PASS`)
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `systematic-debugger`로 다음 P1 티켓 `DEFECT-09` 해결 진행 권장 (`"00_core_foundation 도메인의 DEFECT-09 티켓 해결해줘"`).
  - (교차 도메인 참고) `01_indexing_storage`의 `folder_manager.py#L50-L65` `purge_photo_records_batch`도 `db.commit()` 전 썸네일/Chroma 선삭제 경합이 존재함.
