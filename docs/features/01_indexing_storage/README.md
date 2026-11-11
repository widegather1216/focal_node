# 💾 [01_indexing_storage] Indexing Pipeline, Storage & RAW Media

- **현재 상태 (Lifecycle)**: `📐 Planning (DEFECT-01~11 및 REFACTOR-01 전수 해결 완료 / Active Iteration Step 1 진행 대기)`
- **구현 진척도**: `[□□□□] 0/4 Steps (Active Iteration)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

로컬 폴더 스캔, SHA-256 해싱, EXIF 추출, 360px 썸네일 캐싱, SigLIP 2 시각 임베딩/제로샷 태깅, Gemma 4 캡션/태그 생성, 파일 이동·이름 변경 자동 재연결(Relocation), 2-Pass 점진적 인덱싱 및 고용량 RAW 인메모리 스트리밍을 담당하는 도메인입니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### ✅ Current Baseline (As-Is 기구현 완료)
- [x] 로컬 폴더 등록/삭제 및 SHA-256 원자적 해싱
  - 📂 구현: [`indexing.py`](../../../backend/app/api/indexing.py), [`folders.py`](../../../backend/app/api/folders.py), [`indexing_service.py`](../../../backend/app/services/indexing_service.py) | 🧪 테스트: [`test_api_indexing.py`](../../../backend/tests/test_api_indexing.py), [`test_api_folders.py`](../../../backend/tests/test_api_folders.py) (`PASS`)
- [x] EXIF 메타데이터 추출 및 360px sRGB JPEG 썸네일 디스크 캐싱
  - 📂 구현: [`image.py`](../../../backend/app/utils/image.py), [`photo.py`](../../../backend/app/services/photo.py) | 🧪 테스트: [`test_api_photos.py`](../../../backend/tests/test_api_photos.py) (`PASS`)
- [x] SigLIP 2 768차원 임베딩/제로샷 힌트 추출, Gemma 4 캡션/태그 생성 및 ChromaDB + SQLite WAL 보상 트랜잭션
  - 📂 구현: [`pipeline.py`](../../../backend/app/services/pipeline.py), [`taxonomy.py`](../../../backend/app/services/taxonomy.py), [`atomic_transaction.py`](../../../backend/app/repositories/atomic_transaction.py) | 🧪 테스트: [`test_siglip_zero_shot.py`](../../../backend/tests/test_siglip_zero_shot.py) (`PASS`)
- [x] RAW 원본 인메모리 스트리밍(`MAX_CONCURRENT_DECODES=3`), 단일 사진 재분석(`POST /api/photos/{id}/reindex`) 및 다중 사진 SSE 내보내기
  - 📂 구현: [`photos.py`](../../../backend/app/api/photos.py), [`exportStream.ts`](../../../src/utils/exportStream.ts), [`api.ts`](../../../src/services/api.ts), [`useAppStore.ts`](../../../src/store/useAppStore.ts), [`ActionBar.tsx`](../../../src/components/ActionBar.tsx) | 🧪 테스트: [`test_api_photos.py`](../../../backend/tests/test_api_photos.py), [`test_backend_hardening.py`](../../../backend/tests/test_backend_hardening.py) (`PASS`)

### 🚀 Active Iteration: 스마트 오프라인, SHA-256 Relocation & 2-Pass 점진적 인덱싱 `[To-Be]`
- [ ] **Step 1 [DB & Types]**: `models.py`의 `Image`에 `is_offline: Boolean` 컬럼/마이그레이션 추가, `IndexingStatusResponse`에 `phase: "fast_preview" | "ai_enrichment"` 추가 및 `src/types/photo.ts` 동기화
- [ ] **Step 2 [Repo & API]**: `PhotoRepository`에 오프라인 마킹, SHA-256 경로 재연결(`relocate_photo_path`), 미분석 사진 조회(`get_pending_ai_photos`) 및 `POST /api/folders/prune-offline` 엔드포인트 추가
- [ ] **Step 3 [Service & Pipeline]**: `pipeline.py` 및 `indexing_service.py`를 **Pass 1(해시+EXIF+썸네일 즉시 커밋)** ➔ **Pass 2(백그라운드 SigLIP 2+Gemma 4 비동기 보강)** 2-Pass 구조로 분리하고, 파일 이동/이름 변경 시 비평·즐겨찾기 보존 재연결(`relocated`) 및 오프라인 마킹 적용
- [ ] **Step 4 [UI & Integration]**: `PhotoCard.tsx`에 `[Offline]` 및 `[AI 분석 대기]` 배지 렌더링, `IndexingProgressCard.tsx`에 2-Pass 단계 표시 및 `FullscreenViewer.tsx` 원본 연결 안내 표시

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-11-11 / systematic-debugger / DEFECT-11 해결 및 커밋 완료 (9b7f06d, 8434790 / TC-IDX-17 PASS)`
- **Recent Commits (2026-11-11 23:01)**:
  - `8434790` - `fix(ui): surface folder removal errors and guard active indexing`
  - `9b7f06d` - `fix(folders): enforce registered path match on folder deletion`
  - `aee3928` - `fix(ui): surface export failures and preserve failed selection`
  - `b4924d6` - `fix(media): enforce failure contracts in photo export sse stream`
  - `b0804df` - `fix(indexing): fix cross-thread pause loop binding and multi-loop wakeups`
  - `01eec79` - `fix(media): offload sync db and fs i/o in async photo endpoints`
  - `fc00077` - `fix(exif): guard empty exifread tag values and malformed numeric fields`
  - `ad2eca2` - `fix(indexing): normalize unicode paths to NFC during zombie cleanup`
  - `46ce1f9` - `fix(indexing): defer superseded record deletion until batch commit succeeds`
  - `6ffe113` - `fix(indexing): propagate batch commit errors and isolate run lifecycle`
  - `6cba0eb` - `fix(ui): surface indexing errors in tauri bridge and progress card`
- **해결된 결함 (Resolved Defect)**:
  - `DEFECT-11`: `backend/app/services/indexing_service.py` 및 `backend/app/api/folders.py`에서 빈/공백/상대/널바이트 경로를 `400`으로 사전 차단하고 `_resolve_path_without_leaf_symlink`·`_normalize_folder_deletion_path`로 리프 심볼릭 링크 확장 없이 NFC/NFD 및 말단 슬래시를 정규화한 뒤, 등록된 `IndexedFolder`와 **정확히 일치**하는 경우에만 삭제를 허용하도록 교정함(미등록 상위/루트/형제 경로 `FolderNotRegisteredError` -> `404`, 활성 인덱싱 중 삭제 `FolderDeletionConflictError` -> `409`, DB/ChromaDB 오류 롤백 후 재전파 -> `500`, 교차 파일 심볼릭 링크 및 형제 접두어 폴더 보존). 프론트엔드 `src/store/useAppStore.ts`(`removeFolder` 에러 전파·404 동기화), `src/components/sidebar/FolderList.tsx`(`isIndexing` 삭제 비활성화·실패 시 선택 유지 및 알림), `src/components/Sidebar.tsx`를 연동함(신규 회귀 테스트 `TC-IDX-17` 2종 및 `test_api_folders.py` 5종 포함 백엔드 151종·`tsc && vite build` 전수 통과).
  - `DEFECT-10`: `backend/app/api/photos.py`의 `_prepare_export_items_sync`·`_stream_export_events`에서 중복 ID 제거, 부분 DB 누락 항목 추적, `failed`/`partial`/`success` 상태 및 `failed_count`/`total_count`/`exported_ids`/`failed_ids`, 예기치 못한 스트림 오류 `event: error` SSE 계약을 정립함. 프론트엔드 `src/utils/exportStream.ts`로 WHATWG SSE 파서(CRLF·청크 경계 `\r` 보류·EOF/UTF-8 플러시·멀티라인 `data:`·주석/접두어 충돌 방어·`event: error`·`evaluateExportOutcome`)를 분리하고 `src/services/api.ts`(`AbortSignal` 연동·`Set` 중복 제거), `src/store/useAppStore.ts`(`deselectPhotoIds` 원자적 해제), `src/components/ActionBar.tsx`(실패 붉은색/부분실패 호박색 배너·선택 유지·`[다시 시도]`/`[닫기]`·`StrictMode`/타이머/중복 클릭/`AbortError` 세대 가드)를 연동함(신규 백엔드 회귀 테스트 `TC-IDX-16` 2종 및 전체 148종·`tsc`/`vite build`·Node 9종 전수 통과).
  - `DEFECT-09`: `backend/app/services/indexing_state.py`에 `RLock` 기반 `_ThreadSafeAsyncEvent(asyncio.Event)`를 도입해 sync FastAPI 워커 스레드의 `try_start_indexing()` 선행 호출 시 `_pause_loop` 영구 `None` 고착과 다중 루프 간 대기자 고아화·`cancel->start->pause` 기상 펄스 유실·닫힌 루프 `RuntimeError`를 구조적으로 해소함. 각 대기자의 `(waiter_loop, waiter_future)`를 추적해 락 해제 후 루프별 `call_soon_threadsafe`로 안전 기상시키며, 원자적 `wait_if_paused(run_id)`, `initialize_background_run`의 선점 일시정지 보존, `finalize_run("idle")` 이벤트 복구, `indexing_service.py` 스캔/좀비 정리 전 대기 가드, `api/indexing.py` 제어 라우트 원자적 `bool` 검사를 연동함(신규 회귀 테스트 `TC-IDX-15` 4종 및 백엔드 146종 전수 통과).
  - `DEFECT-08`: `backend/app/api/photos.py`의 비동기 라우트(`get_photo_thumbnail`, `get_photo_original`, `export_photos`) 내 동기 DB 조회(`get_by_id`, `get_by_ids`) 및 동기 파일시스템 I/O(`os.path.exists`/`isdir`/`stat`)를 `_fetch_photo_media_record_sync`, `_read_cached_thumbnail_sync`, `_stat_regular_file_sync`, `_decode_raw_original`, `_prepare_export_items_sync`로 분리해 `await asyncio.to_thread(...)` 내부에서 `database.SessionLocal()`을 열고 닫고 평문 값만 반환하도록 수정함. 또한 `get_decode_semaphore()`를 `WeakKeyDictionary` 기반 이벤트 루프별 격리로 전환하고 비-RAW `FileResponse` `stat_result`·`S_ISREG` 검증 및 `except HTTPException: raise`를 추가하여 404/422 계약을 복원함(신규 회귀 테스트 `TC-IDX-14` 3건 및 백엔드 142종 전수 통과).
  - `DEFECT-07`: `backend/app/utils/image.py`에 `_unwrap_tag_values`, `_parse_positive_float`, `_parse_int`, `_extract_tags_dict`를 도입하고 `_get_tag_val`이 빈 리스트(`[]`)/튜플/공백 문자열/빈 바이트를 건너뛰어 후속 대체 키를 계속 탐색하도록 수정함. 또한 `Ratio(n, 0)`(`ZeroDivisionError`) 및 비정형 튜플(`TypeError`)로 인한 후속 EXIF 필드 파싱 중단을 차단하고 신규 회귀 테스트 `TC-IDX-13`(`test_tc_idx_13_exif_empty_tag_values_preserves_remaining_metadata`) 및 백엔드 139종 전수 통과를 확인함.
  - `DEFECT-06`: `backend/app/services/indexing_service.py`에 `_normalize_path_for_comparison`·`_to_folder_prefix_pair`·`_belongs_to_any_folder`를 도입해 `os.path.realpath`/`normpath` 이후 `unicodedata.normalize("NFC", ...).lower()`를 일관 적용하고, `_identify_zombie_photo_ids` 및 `cleanup_zombie_records`가 NFC/NFD 경로 불일치로 한글 폴더 내 정상 사진을 좀비로 오판해 삭제하지 않도록 수정함(물리적 삭제 파일 및 유사 접두어 미등록 형제 폴더 정리는 유지, `TC-IDX-12` 신규 회귀 테스트 통과).
  - `DEFECT-05`: `index_single_file_sync`에서 배치 커밋 전 구 레코드를 즉시 삭제하던 `delete_photo_atomic_sync` 호출을 제거하고 stat/DB/해시 구간까지 예외 안전화(`_find_existing_id_or_skip`, `_resolve_hash_conflict`)한 뒤 top-level `replaces_image_id`를 전달하도록 개편함. `_save_photos_atomic_internal`에서 동일 미커밋 SQLite 트랜잭션 내 `db.add_all` 직전 `_delete_replaced_rows_in_tx(..., synchronize_session="fetch") + db.flush()`로 자식/부모 행을 선삭제해 `UNIQUE(file_path)` 충돌·롤백 유실·고아 행 잔류를 차단하고, 커밋 성공 직후에만 격리된 `_cleanup_replaced_artifacts`로 구 벡터/구 썸네일을 정리하도록 수정함.
  - `DEFECT-04`: `_commit_batch_with_retry`에서 세션 롤백 후 3회 실패 시 예외를 재전파하도록 수정하고, `IndexingStateManager`에 `run_id` 세대 격리·원자적 `finalize_run`·`error_message`를 도입해 예외 및 `BaseException` 발생 시 후속 청크 실행과 거짓 완료 로그(`Background indexing completed.`/`Sync completed.`) 발행을 차단하고 `status="error"`로 전이하도록 조치. Tauri `indexing-error` 이벤트, Zustand `reportIndexingError`/`dismissIndexingError`, `useIndexingStatus` `'error'` 분기, `IndexingProgressCard` 에러 전용 UI까지 전 계층 정합성을 보완함.
  - `DEFECT-03`: `IndexingStateManager`에 원자적 상태 선점 메서드 `try_start_indexing()`을 도입하여 락 내부에서 즉시 `"processing"`을 선점하고 중복 요청을 400 거부하도록 조치. 경로/DB 작업 예외 발생 시 `reset_status()` 안전 롤백 및 `run_indexing_background` startup 시 `initialize_background_run()`으로 상태가 순간적으로 `idle`로 풀리는 레이스를 원천 차단하여 중복 인덱서 실행 및 ChromaDB 벡터 영구 소실 해소.
  - `DEFECT-02`: `VectorRepository.delete`에서 ChromaDB `collection.delete` 실패 시 예외를 삼키던 결함을 제거하고 `logger.error` 후 `raise`로 재전파. `CompensatingTransactionManager.delete_and_commit`이 예외를 감지하여 SQLite `commit`을 방지하고 `rollback`을 수행함으로써 SQLite만 삭제되고 ChromaDB에 좀비 벡터가 영구 잔류하는 정합성 붕괴 완전 해소.
  - `DEFECT-01`: ChromaDB `get(include=["embeddings"])` 반환 `numpy.ndarray`에 대한 직접 불리언 평가 제거, Guard Clause 및 `.tolist()` 변환으로 100% `ValueError` 크래시 방지 및 단일 사진 재인덱싱/유사도 검색 안정화.
- **잔여 우선순위 결함 (Open DEFECT Logs)**:
  - 없음 (`0건` — Baseline `DEFECT-01~11` 및 `REFACTOR-01` 전수 해결 완료)
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_backend_hardening.py -k test_tc_idx_17 -v` (`2 passed`)
  - `./venv/bin/pytest backend/tests/test_api_folders.py -v` (`5 passed`)
  - `./venv/bin/pytest backend/tests/ -q` (`151 passed`)
  - `npx tsc --noEmit && npm run build` (`PASS`)
  - `python3 -B ~/.gemini/config/skills/interactive-feature-planner/scripts/check_wiki_health.py docs` (`exit 0`)
- **다음 세션 포커스 및 추천 프롬프트**:
  - `Active Iteration` Step 1 착수: `"01_indexing_storage 도메인 Step 1 개발 진행해줘"` (`is_offline` 컬럼/마이그레이션 및 `phase` 상태 계약 구현)
