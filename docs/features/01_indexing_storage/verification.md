# 🧪 [01_indexing_storage] Verification & Ticket Logs

- **검증 상태**: `🩹 Debugging (DEFECT-01~11 및 REFACTOR-01 해결 완료 / REFACTOR-02 1건 대기)`
- **인수 조건 통과율**: `1 / 4 (Baseline 100%)`
- **미해결 티켓**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 1건`

---

## 🎯 1. Given-When-Then 인수 조건 (Acceptance Criteria)

### AC 1. 폴더 연동 및 1단계 백그라운드 인덱싱 `[As-Is]`
* **Given:** 사용자가 JPEG 및 RAW(ARW, CR3, NEF)가 포함된 로컬 폴더를 등록했을 때,
* **When:** 백그라운드 인덱싱 파이프라인이 실행되면,
* **Then:**
  1. 각 파일의 SHA-256 해시가 SQLite `images.id`와 ChromaDB `photo_embeddings` ID로 원자적으로 등록되어야 한다.
  2. Thumbnail Cache 디렉토리에 360px sRGB JPEG가 생성되어야 한다.
  3. 이벤트 루프 블로킹 없이 `GET /api/index/status` 폴링으로 진행률(0~100%)이 조회되어야 한다.

### AC 2. 비파괴적 스마트 오프라인 관리 `[To-Be]`
* **Given:** 외장 드라이브의 사진이 인덱싱된 상태에서,
* **When:** 외장 드라이브가 언마운트된 후 동기화(`/api/index/sync`)가 실행되면,
* **Then:**
  1. DB에서 레코드가 삭제되지 않고 `images.is_offline = True`로 갱신되어야 한다.
  2. 갤러리에서 캐시된 360px 썸네일이 유지되며 `[Offline]` 배지가 표시되어야 한다.

### AC 3. SHA-256 기반 파일 이동·이름 변경 자동 재연결 (`Relocation`) `[To-Be]`
* **Given:** 즐겨찾기(`is_favorite=True`)와 AI 비평(`critique`)이 저장된 사진 파일을 Finder에서 이름을 변경하거나 하위 폴더로 이동했을 때,
* **When:** 폴더 동기화(`/api/index/sync`)가 실행되면,
* **Then:**
  1. 동일 SHA-256 해시를 감지하여 AI 재추론 없이 `file_path`, `parent_dir`, `file_name`만 새 경로로 In-place 업데이트되어야 한다.
  2. 기존 즐겨찾기, 수동 편집 태그(`is_user_edited`), AI 비평 데이터가 유실 없이 100% 보존되어야 한다.

### AC 4. 2-Pass 점진적 인덱싱 (Fast Preview ➔ AI Enrichment) `[To-Be]`
* **Given:** 사용자가 신규 사진 폴더를 등록했을 때,
* **When:** 인덱싱이 시작되면,
* **Then:**
  1. **Pass 1 (`fast_preview`)**에서 해시·EXIF·360px 썸네일이 먼저 커밋되어 AI 추론 완료 전에도 갤러리 열람 및 EXIF 필터링이 즉시 가능해야 한다.
  2. 이어서 **Pass 2 (`ai_enrichment`)**가 백그라운드에서 순차적으로 SigLIP 2 임베딩과 Gemma 4 캡션/태그를 채워 넣어야 한다.

---

## 🧪 2. 테스트 시나리오 매트릭스 (Test Matrix)

| 구분 | 테스트 ID | 시나리오 설명 | 입력 / 조작 조건 | 기대 결과 | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Happy** | `TC-IDX-01` | 대용량 폴더 1단계 인덱싱 | 500장 폴더 등록 | 해시/EXIF/360px 캐시 및 임베딩 저장 | `PASS` |
| **Boundary**| `TC-IDX-02` | 동시 RAW 디코딩 부하 제어 | 10개 원본 RAW 동시 요청 | 세마포어(3) 동작하여 OOM 방지 | `PASS` |
| **Negative**| `TC-IDX-03` | 손상된 RAW 파일 스캔 | 0바이트 손상 ARW 파일 | 파이프라인 중단 없이 스킵/폴백 | `PASS` |
| **Negative**| `TC-IDX-04` | 외장 드라이브 언마운트 (`[To-Be]`) | 인덱싱된 볼륨 분리 후 동기화 | 레코드 유지 + `is_offline=True` 배지 | `⏳ Pending` |
| **Happy** | `TC-IDX-05` | 파일 이름 변경/이동 재연결 (`[To-Be]`) | 파일 이동 후 `/api/index/sync` | AI 재추론 없이 경로 갱신 및 비평 보존 | `⏳ Pending` |
| **Happy** | `TC-IDX-06` | 2-Pass 점진적 인덱싱 (`[To-Be]`) | 신규 폴더 등록 직후 갤러리 조회 | Pass 1 직후 썸네일/EXIF 즉시 노출 | `⏳ Pending` |
| **Boundary**| `TC-IDX-07` | ChromaDB 임베딩 조회 ndarray 불리언 예외 방지 | `get_embedding_by_id` 호출 | ndarray 불리언 평가 에러 없이 list 반환 | `PASS (Fixed in DEFECT-01)` |
| **Boundary**| `TC-IDX-08` | ChromaDB 삭제 실패 시 보상 트랜잭션 롤백 | `delete_and_commit` 시 Chroma 에러 | SQLite 삭제 취소 및 예외 재전파 | `PASS (Fixed in DEFECT-02)` |
| **Boundary**| `TC-IDX-09` | 인덱싱/동기화 동시 호출 시 TOCTOU 방지 | `start` + `sync` 동시 호출 | 단일 태스크만 시작되고 벡터 소실 차단 | `PASS (Fixed in DEFECT-03)` |
| **Negative**| `TC-IDX-10` | 배치 커밋 실패 시 에러 전파 및 거짓 완료 차단 | `_commit_batch_with_retry` 3회 실패 | 예외 raise 및 status="error" 전이 | `PASS (Fixed in DEFECT-04)` |
| **Boundary**| `TC-IDX-11` | 수정 파일 재인덱싱 중단 시 기존 레코드 보존 | 재인덱싱 중 취소/실패 주입 | 신규 커밋 전 구 레코드 조기 삭제 차단 | `PASS (Fixed in DEFECT-05)` |
| **Boundary**| `TC-IDX-12` | macOS NFD/NFC 한글 폴더 사진 오삭제 방지 | 한글 폴더 NFD/NFC 동기화 | 좀비 오판 차단 및 사진 보존 | `PASS (Fixed in DEFECT-06)` |
| **Negative**| `TC-IDX-13` | ExifRead 빈 리스트(`values=[]`) 파싱 안정성 | 손상/초과 IFD 태그 파싱 | IndexError 방지 및 나머지 EXIF 보존 | `PASS (Fixed in DEFECT-07)` |
| **Boundary**| `TC-IDX-14` | 비동기 미디어 라우트 내 동기 DB I/O 격리 | 썸네일/원본/내보내기 동시 요청 | 메인 비동기 이벤트 루프 동결 방지 | `PASS (Fixed in DEFECT-08)` |
| **Boundary**| `TC-IDX-15` | IndexingStateManager 크로스 스레드 루프 바인딩 | 백그라운드 스레드 pause/resume | call_soon_threadsafe 안전 전달 | `PASS (Fixed in DEFECT-09)` |
| **Negative**| `TC-IDX-16` | 사진 내보내기 실패 시 에러 보존 및 UI 피드백 | 0장 내보내기 에러 응답 수신 | 허위 녹색 완료 차단 및 실패 안내 | `PASS (Fixed in DEFECT-10)` |
| **Security**| `TC-IDX-17` | 폴더 삭제 시 미등록 상위 경로 재귀 삭제 차단 | DELETE /api/folders?path=/ | 미등록 상위 경로 요청 거부 및 데이터 보호 | `PASS (Fixed in DEFECT-11)` |

---

## 🚨 3. 결함 리포트 (Defect Logs)

### [DEFECT-01] `VectorRepository.get_embedding_by_id`의 NumPy array 불리언 평가로 인한 100% `ValueError` 크래시
- **현재 상태**: 🟢 RESOLVED — Guard Clause 및 `.tolist()` 변환으로 ndarray 불리언 크래시 해소 (`TC-IDX-07`) | 회귀: PASS (133 passed)

### [DEFECT-02] `VectorRepository.delete`의 예외 삼킴으로 인한 보상 트랜잭션 무력화 및 좀비 벡터 영구 잔류
- **현재 상태**: 🟢 RESOLVED — `collection.delete` 실패 시 `logger.error` 후 `raise` 재전파로 보상 트랜잭션 롤백 보장 (`TC-IDX-08`) | 회귀: PASS (134 passed)

### [DEFECT-03] `start_indexing` / `sync_database` TOCTOU 동시성 레이스로 인한 중복 인덱서 실행 및 ChromaDB 벡터 영구 소실
- **현재 상태**: 🟢 RESOLVED — `IndexingStateManager.try_start_indexing()` 원자적 상태 선점 및 `initialize_background_run()` 적용 (`TC-IDX-09`) | 회귀: PASS (135 passed)

### [DEFECT-04] `_commit_batch_with_retry` 3회 실패 시 예외 삼킴으로 인한 대규모 사진 유실 및 거짓 정상 완료 위장
- **현재 상태**: 🟢 RESOLVED — 배치 커밋 예외 재전파, `run_id` 세대 격리, `status="error"` 전이 및 Tauri/UI 에러 전용 표시 연동 (`TC-IDX-10`) | 회귀: PASS (136 passed)

### [DEFECT-05] `index_single_file_sync`의 선행 삭제(Delete-Before-Commit)로 인한 수정 파일 재인덱싱 취소/실패 시 데이터 영구 증발
- **현재 상태**: 🟢 RESOLVED — 선행 삭제 제거 후 `_save_photos_atomic_internal` 내 미커밋 선삭제+`flush` 및 post-commit 아티팩트 격리 정리 (`TC-IDX-11`) | 회귀: PASS (137 passed)

### [DEFECT-06] macOS 유니코드 정규화(NFD vs NFC) 불일치로 인한 `_identify_zombie_photo_ids`의 한글 폴더 사진 전량 오삭제
- **현재 상태**: 🟢 RESOLVED — `_normalize_path_for_comparison`·`_to_folder_prefix_pair`·`_belongs_to_any_folder` NFC 일원화 (`TC-IDX-12`) | 회귀: PASS (138 passed)

### [DEFECT-07] `_get_tag_val`의 `tag.values == []` 빈 리스트 `IndexError`로 인한 EXIF 메타데이터 파싱 전면 중단
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🟠 P1 High (Partial Metadata Loss)
- **해결 내역**:
  - **수정 파일**: [`backend/app/utils/image.py`](../../../backend/app/utils/image.py#L99-L125), [`backend/app/utils/image.py#L239-L312`](../../../backend/app/utils/image.py#L239-L312), [`backend/tests/test_backend_hardening.py`](../../../backend/tests/test_backend_hardening.py#L1014-L1129)
  - **원인 및 조치**: ExifRead가 `count=0` 또는 `count>=1000` 초과·손상 IFD 태그에 대해 `values=[]`를 반환할 때 `_get_tag_val`이 `tag.values[0]`에 직접 접근하여 `IndexError`를 발생시키고 `_parse_exif_tags_dict`의 나머지 모든 EXIF 파싱을 중단시키던 결함을 해소함. `_unwrap_tag_values` 헬퍼를 도입해 빈 리스트/튜플(`[]`, `()`), 공백 문자열, 빈 바이트 및 `None`을 필터링하되 숫자 `0`은 보존하고 `_get_tag_val`이 후속 대체 키(`EXIF ISOSpeed`, `Image LensModel`, `Image DateTime` 등)를 계속 탐색하도록 교정함. 또한 `_parse_positive_float`, `_parse_int`, `_extract_tags_dict`를 분리해 손상된 `Ratio(n, 0)`(`ZeroDivisionError`) 및 비정형 튜플(`TypeError`)이 후속 EXIF 필드를 중단하지 않도록 방어함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_backend_hardening.py -k test_tc_idx_13 -v` (`PASS`), `./venv/bin/pytest backend/tests/ -v` (`139 passed`)

### [DEFECT-08] `photos.py` 비동기 엔드포인트 내 동기 DB I/O 호출로 인한 FastAPI 단일 비동기 이벤트 루프 동결
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🟠 P1 High (Event Loop Freeze / Denial of Service)
- **해결 내역**:
  - **수정 파일**: [`backend/app/api/photos.py`](../../../backend/app/api/photos.py#L25-L264), [`backend/tests/test_backend_hardening.py`](../../../backend/tests/test_backend_hardening.py#L1132-L1455)
  - **원인 및 조치**: Devil's Advocate 자문 교차 검증을 통해 `get_photo_thumbnail`, `get_photo_original`, `export_photos`의 동기 DB 조회(`get_by_id`, `get_by_ids`) 및 동기 파일시스템 I/O(`get_photo_original` 비-RAW 분기의 `os.path.exists`, `export_photos`의 `os.path.exists`/`os.path.isdir`) 직접 실행뿐 아니라, `from database import SessionLocal` 값 바인딩으로 인한 테스트 격리 누락, `Depends(get_db)` 세션을 워커 스레드로 넘길 때의 `StaticPool`/커넥션 풀 고갈 위험, 전역 `_decode_semaphore`의 다중 이벤트 루프 바인딩 충돌, `except Exception`의 `HTTPException(404/422)` 삼킴까지 일괄 해소함. `_fetch_photo_media_record_sync`, `_read_cached_thumbnail_sync`, `_stat_regular_file_sync`, `_decode_raw_original`, `_prepare_export_items_sync`를 분리하여 모든 DB·파일시스템 I/O를 `await asyncio.to_thread(...)` 내부로 격리하고 워커 스레드에서 `database.SessionLocal()`을 열고 닫은 뒤 평문 값(tuple/dict)만 반환하도록 개편함. 또한 `get_decode_semaphore()`를 `WeakKeyDictionary[AbstractEventLoop, Semaphore]` 기반으로 루프별 격리하고 비-RAW `FileResponse`에 `stat_result` 및 `S_ISREG` 검증과 `except HTTPException: raise` 가드를 추가함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_backend_hardening.py -k test_tc_idx_14 -v` (`3 passed`), `./venv/bin/pytest backend/tests/ -v` (`142 passed`)

### [DEFECT-09] `IndexingStateManager._pause_loop` 영구 `None` 고착으로 인한 크로스 스레드 `call_soon_threadsafe` 누락 및 이벤트 루프 블로킹
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🟠 P1 High (Concurrency Hang)
- **해결 내역**:
  - **수정 파일**: [`backend/app/services/indexing_state.py`](../../../backend/app/services/indexing_state.py#L15-L530), [`backend/app/services/indexing_service.py`](../../../backend/app/services/indexing_service.py#L38-L48), [`backend/app/services/indexing_service.py#L573-L674`](../../../backend/app/services/indexing_service.py#L573-L674), [`backend/app/api/indexing.py`](../../../backend/app/api/indexing.py#L79-L96), [`backend/tests/test_backend_hardening.py`](../../../backend/tests/test_backend_hardening.py#L1456-L1725)
  - **원인 및 조치**: 2-Way 경쟁 가설 추적 및 2회 Devil's Advocate 검증을 통해, sync FastAPI 라우트(`start_indexing`/`sync_database`) AnyIO 워커 스레드의 `try_start_indexing()` 선행 호출로 `_pause_loop`가 `None`에 영구 고착되는 문제뿐 아니라 다중 이벤트 루프(`loop_1` vs `TestClient` 포탈 루프 `loop_2`) 전환 시 대기자 고아화·`cancel->start->pause` 기상 펄스 유실·스레드 간 stale 읽기·닫힌 루프 `RuntimeError`·시작 전 일시정지 무시 레이스까지 일괄 해소함. `threading.RLock` 기반 `_ThreadSafeAsyncEvent(asyncio.Event)`를 도입해 각 대기자의 `(waiter_loop, waiter_future)`를 직접 추적하고 락 해제 후 루프별 `call_soon_threadsafe`로 안전 기상시키도록 개편함. 또한 원자적 `wait_if_paused(run_id)`와 `initialize_background_run`의 선점 일시정지 보존, `finalize_run("idle")` 이벤트 복구, `run_indexing_background` 스캔/좀비 정리 전 대기 가드, `api/indexing.py` 제어 라우트 원자적 반환(`bool`) 검사를 연동함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_backend_hardening.py -k test_tc_idx_15 -v` (`4 passed`), `./venv/bin/pytest backend/tests/ -v` (`146 passed`)

### [DEFECT-10] `ActionBar.tsx`의 사진 내보내기 실패 시 "0장 완료" 녹색 체크 허위 표시 및 선택 강제 해제
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🟠 P1 High (False Success UI Masking)
- **해결 내역**:
  - **수정 파일**: [`backend/app/api/photos.py`](../../../backend/app/api/photos.py#L86-L105), [`backend/app/api/photos.py`](../../../backend/app/api/photos.py#L232-L331), [`src/utils/exportStream.ts`](../../../src/utils/exportStream.ts#L1-L285), [`src/services/api.ts`](../../../src/services/api.ts#L111-L136), [`src/store/useAppStore.ts`](../../../src/store/useAppStore.ts#L197-L210), [`src/components/ActionBar.tsx`](../../../src/components/ActionBar.tsx#L1-L357), [`backend/tests/test_backend_hardening.py`](../../../backend/tests/test_backend_hardening.py#L1729-L1909)
  - **원인 및 조치**: 2-Way 경쟁 가설 추적 및 Devil's Advocate 적대적 검증을 통해 다계층 내보내기 계약·SSE 파서·UI 수명주기 결함을 일괄 해소함. 백엔드 `_prepare_export_items_sync`/`_stream_export_events`는 요청 중복 ID 제거·부분 DB 누락 항목 `errors` 포함·`failed`/`partial`/`success` 상태와 `failed_count`/`total_count`/`exported_ids`/`failed_ids`·예기치 않은 스트림 오류 `event: error`를 명시 발행하도록 개선함. 프론트엔드 `src/utils/exportStream.ts`는 WHATWG 스펙 준수 라인 파서(CRLF/청크 경계 `\r` 보류·EOF 잔여 버퍼 및 `TextDecoder` 플러시·멀티라인 `data:`·주석/접두어 충돌 방어·`event: error` 예외 전파)와 `evaluateExportOutcome`을 구현했고 `api.ts`는 `AbortSignal` 전달 및 사전 중복 제거를 적용함. `useAppStore.ts`의 원자적 `deselectPhotoIds`와 `ActionBar.tsx` 상태 머신을 연동해 실패(`error`)·부분실패(`partial`) 시 붉은색/호박색 경고 배너(`AlertTriangle`)·선택 상태 유지(부분실패 시 실패 ID만 잔류)·`[다시 시도]`/`[닫기]`·`StrictMode`/타이머/중복 클릭/`AbortError` 세대 가드를 구현함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_backend_hardening.py -k test_tc_idx_16 -v` (`2 passed`), `./venv/bin/pytest backend/tests/ -v` (`148 passed`), `npx tsc --noEmit && npm run build` (`PASS`), Node `node --test` 순수 SSE/스토어/API 단위 검증 (`9 passed`)

### [DEFECT-11] `DELETE /api/folders`의 등록 여부 미검증으로 인한 상위 경로 전달 시 전체 사진/폴더 재귀적 강제 삭제
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🟠 P1 High (Arbitrary Mass Deletion)
- **해결 내역**:
  - **수정 파일**: [`backend/app/api/folders.py`](../../../backend/app/api/folders.py#L1-L52), [`backend/app/services/indexing_service.py`](../../../backend/app/services/indexing_service.py#L135-L382), [`src/store/useAppStore.ts`](../../../src/store/useAppStore.ts#L261-L286), [`src/components/sidebar/FolderList.tsx`](../../../src/components/sidebar/FolderList.tsx#L10-L166), [`src/components/Sidebar.tsx`](../../../src/components/Sidebar.tsx#L339-L347), [`backend/tests/test_api_folders.py`](../../../backend/tests/test_api_folders.py#L71-L97), [`backend/tests/test_concurrency_hardening.py`](../../../backend/tests/test_concurrency_hardening.py#L324-L346), [`backend/tests/test_backend_hardening.py`](../../../backend/tests/test_backend_hardening.py#L2150-L2413)
  - **원인 및 조치**: 1차 적대적 Devil's Advocate 검증을 통해 API·서비스 무검증 접두어 삭제뿐 아니라 빈/공백 문자열의 `os.path.realpath("") == CWD` 우회, 리프 심볼릭 링크를 통한 상위 디렉터리 확장(`[F3]`), 교차 폴더 파일 심볼릭 링크 연쇄 삭제(`[F4]`), `remove_folder_data` 예외 삼킴(`200 OK` 위장), `IndexingStateManager` 활성 인덱싱 중 동시 삭제 레이스(`[F2]`), 프론트엔드 `useAppStore.removeFolder`/`FolderList.tsx` 실패 무묵인 및 허위 선택 해제(`[F1]`)까지 일괄 해소함. `indexing_service.py`에 `_resolve_path_without_leaf_symlink`·`_normalize_folder_deletion_path`·`_validate_folder_deletion_pair`·`_find_matching_indexed_folders`·`_belongs_to_deletion_target`·`_execute_folder_deletion`을 도입해 비어 있지 않은 절대 경로만 허용하고, NFC/NFD 및 말단 슬래시를 통합 정규화한 뒤 등록된 `IndexedFolder`와 **정확히 일치**하는 경우에만 삭제를 승인(`FolderNotRegisteredError` -> 404, 잘못된 경로 `ValueError` -> 400, 활성 인덱싱 중 삭제 `FolderDeletionConflictError` -> 409, DB/Chroma 오류 롤백 후 재전파 -> 500)하도록 교정함(하위 중첩 등록 폴더는 함께 정리하고 형제 접두어 폴더 및 교차 파일 심볼릭 링크는 보존). 프론트엔드 `useAppStore.ts`는 `!response.ok` 시 에러를 전파(404 시 폴더 목록 동기화)하고, `FolderList.tsx`는 `isIndexing` 중 삭제 버튼을 비활성화하며 실패 시 쿼리 무효화·선택 해제를 차단하고 오류 알림을 노출하도록 보완함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_backend_hardening.py -k test_tc_idx_17 -v` (`2 passed`), `./venv/bin/pytest backend/tests/test_api_folders.py -v` (`5 passed`), `./venv/bin/pytest backend/tests/ -q` (`151 passed`), `npx tsc --noEmit && npm run build` (`PASS`)

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `PhotoMetadata` 프론트엔드 타입 필드 불일치 해소, 라우터 직접 DB 쿼리 캡슐화 및 캐시 예외 로깅
- **현재 상태**: 🟢 RESOLVED — `PhotoMetadata` 필드 통일, `PhotoRepository` 캡슐화, 썸네일 캐시 명시적 예외 처리 및 로깅 적용 완료 | 회귀: PASS (99 passed)

### [REFACTOR-02] `indexing_service.py`(819줄) 책임별 모듈 분리, `ActionBar.tsx`·`Sidebar.tsx` 300줄 이하 경량화 및 빈 `catch`/`any` 정리
- **심각도**: 🟡 Should Fix (권장 조치)
- **위치**: `backend/app/services/indexing_service.py#L135-L381, #L601-L797`, `backend/app/api/photos.py#L286-L322`, `src/components/ActionBar.tsx#L1-L357`, `src/components/Sidebar.tsx#L1-L359`, `src/components/sidebar/IndexingProgressCard.tsx#L101,L115,L130`, `src/utils/exportStream.ts#L69`
- **위반 규칙**: Rule 4.1 (단일 책임 SRP, 함수 <= 30줄, 단일 UI 파일 <= 300줄), Rule 4.3 (빈 `catch` 금지)
- **발견된 문제**:
  - `DEFECT-01~11` 하드닝 패치 누적으로 `indexing_service.py`가 819줄(경로/유니코드 정규화, 좀비 정리, 폴더 삭제 검증/실행, 단건 인덱싱, 배치 워커 혼재)로 비대화되었으며, `_commit_batch_with_retry`(36줄)·`run_indexing_background`(48줄) 및 `photos.py`의 `_stream_export_events`(37줄)가 30줄 가이드를 초과함.
  - 프론트엔드 `ActionBar.tsx`(357줄)와 `Sidebar.tsx`(359줄)가 단일 UI 파일 300줄 상한을 초과하며, `IndexingProgressCard.tsx`의 `catch (e: any)`(`L101, L115, L130`)와 `exportStream.ts#L69`의 주석만 있는 빈 `catch`가 잔존함.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - `indexing_service.py`에서 경로 정규화·좀비 정리·폴더 삭제 도메인 로직(L135-L381)을 `backend/app/services/folder_manager.py`로 분리해 500줄 이하로 경량화하고 장문 함수 헬퍼 추출
  - `ActionBar.tsx` 내보내기 배너 및 `Sidebar.tsx` 하위 섹션을 분리해 300줄 이하로 축소하고, `exportStream.ts` 빈 `catch`에 `console.debug` 추가 및 `IndexingProgressCard.tsx` 예외 타입 `unknown` 정리
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)
