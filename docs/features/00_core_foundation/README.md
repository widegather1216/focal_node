# 🏛️ [00_core_foundation] Core Foundation & System Architecture

- **현재 상태 (Lifecycle)**: `🩹 Debugging (DEFECT-09 해결 완료 — DEFECT-10~11 2건 해결 대기)`
- **구현 진척도**: `[■■■■] 4/4 Steps`
- **미해결 티켓 현황**: `🚨 DEFECT: 2건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
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

- **직전 완료 작업**: `2026-11-17 / systematic-debugger / 00_core_foundation DEFECT-09 해결 및 회귀 검증 완료 (fdd438e)`
- **조치 요약 (`DEFECT-09` RESOLVED)**:
  - `backend/app/chroma.py`: `_resolve_system_identifiers()`, `_evict_shared_system_cache()`, `_backup_corrupted_chroma_dir()`, `_heal_chroma_client_locked()` 도입으로 손상 `chroma.sqlite3` Self-Healing 시 해당 경로의 실패 `System`만 `SharedSystemClient`에서 정밀 제거·안전 `stop()` 후 `_collection = None` 동기화·재초기화(`AttributeError: bindings` 해소 및 타 클라이언트 보존).
  - `backend/app/repositories/vector_repository.py`: `has_embedding(photo_id)` 추가로 실제 Chroma `dict["ids"]` 누락 판정 및 `conftest.py` 미설정 `MagicMock` 환경 호환 보장.
  - `backend/app/services/indexing_service.py`: `_find_existing_id_or_skip()`·`_resolve_hash_conflict()`·`_ensure_existing_photo_vector()`·`_repair_missing_vector_sync()`로 누락 벡터 감지 시 SQLite `ImageMetadata` + SigLIP 2 임베딩만 In-place 업서트(`"vector_repaired"`)하여 `is_user_edited`·`critique`·`overall_score` 100% 보존 및 `GemmaAdapter` 미호출.
  - `backend/tests/test_backend_hardening.py`: `TC-CF-10` 회귀 테스트 2종(실제 `chromadb==1.5.9` 손상 `chroma.sqlite3` Self-Healing 격리 복구 및 `/api/index/sync`·`index_single_file_sync` 누락 벡터 복구·비평 보존·유사 검색 복원) 추가.
- **남은 핵심 결함 (`DEFECT-10~11`, 2건)**:
  - `DEFECT-10` (🟠 P1): `GemmaAdapter.generate_caption_and_tags` 예외 삼킴으로 빈 메타데이터 커밋 및 재인덱싱 영구 스킵
  - `DEFECT-11` (🟠 P1): Tauri IPC `save_binary_file` 무검증 임의 파일 쓰기 및 `tauri.conf.json` `"csp": null`
- **검증 명령어**: `./venv/bin/pytest backend/tests/test_backend_hardening.py backend/tests/test_api_indexing.py backend/tests/test_api_search.py -v` (`43 passed`), `./venv/bin/pytest backend/tests/ -q` (`164 passed`), `npx tsc --noEmit` (`PASS`)
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `systematic-debugger`로 다음 P1 티켓 `DEFECT-10` 해결 진행 권장 (`"00_core_foundation 도메인의 DEFECT-10 티켓 해결해줘"`).
  - (교차 도메인 참고) `01_indexing_storage`의 `folder_manager.py#L50-L65` `purge_photo_records_batch`도 `db.commit()` 전 썸네일/Chroma 선삭제 경합이 존재함.
