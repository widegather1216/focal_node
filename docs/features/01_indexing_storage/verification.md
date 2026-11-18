# 🧪 [01_indexing_storage] Verification & Ticket Logs

- **검증 상태**: `🩹 Debugging (DEFECT-14~17 해결 대기)`
- **인수 조건 통과율**: `1 / 4 (Baseline 100%)`
- **미해결 티켓**: `🚨 DEFECT: 4건` | `🧐 REFACTOR: 0건`

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
| **Boundary**| `TC-IDX-18` | 인덱싱 취소 직후 폴더 삭제 및 재시작 동시성 격리 | 워커 스레드 실행 중 cancel ➔ delete/start | 인플라이트 워커 종료 전 삭제/재시작 차단 및 좀비 방지 | `PASS (Fixed in DEFECT-12)` |
| **Happy** | `TC-IDX-19` | 폴더 필터 조회 시 하위 디렉터리 및 NFD/NFC 정규화 | 하위 폴더/한글 NFD 포함 폴더 선택 | 하위 디렉터리 및 NFD/NFC 사진 정상 조회 | `PASS (Fixed in DEFECT-13)` |
| **Boundary**| `TC-IDX-20` | 단일 사진 재분석 캐시 동기화 및 사진 전환 격리 | 상세 재분석 중 타 사진 선택 또는 완료 대기 | `photoDetail` 캐시 즉시 갱신 및 전환 후 버퍼 오염 차단 | `FAIL (DEFECT-14)` |
| **Boundary**| `TC-IDX-21` | 상세 패널/갤러리 즐겨찾기 토글 양방향 캐시 동기화 | 폴더 선택 중 상세 패널 하트 토글 | `photos` 및 `photoDetail` 캐시 모두 서버 상태와 일치 | `FAIL (DEFECT-15)` |
| **Boundary**| `TC-IDX-22` | 내보내기 중 전체 선택 해제 시 피드백 누수 차단 | SSE 내보내기 진행 중 선택 해제 후 새 사진 선택 | 진행 중 요청 중단 및 이전 실패/완료 배너 잔류 차단 | `FAIL (DEFECT-16)` |
| **Boundary**| `TC-IDX-23` | 초장축 세로 파노라마 썸네일 JPEG 65,500px 상한 방어 | 10x5000 또는 100x20000 이미지 썸네일 생성 | libjpeg 65,500px 초과 OSError 없이 썸네일 생성 | `FAIL (DEFECT-17)` |

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
- **현재 상태**: 🟢 RESOLVED — `_unwrap_tag_values`/`_parse_positive_float`/`_parse_int` 도입으로 빈 IFD·0분모 방어 (`TC-IDX-13`) | 회귀: PASS (139 passed)

### [DEFECT-08] `photos.py` 비동기 엔드포인트 내 동기 DB I/O 호출로 인한 FastAPI 단일 비동기 이벤트 루프 동결
- **현재 상태**: 🟢 RESOLVED — `asyncio.to_thread` 독립 세션 격리 및 `WeakKeyDictionary` 루프별 세마포어 적용 (`TC-IDX-14`) | 회귀: PASS (142 passed)

### [DEFECT-09] `IndexingStateManager._pause_loop` 영구 `None` 고착으로 인한 크로스 스레드 `call_soon_threadsafe` 누락 및 이벤트 루프 블로킹
- **현재 상태**: 🟢 RESOLVED — `RLock` 기반 `_ThreadSafeAsyncEvent` 및 다중 루프 `(waiter_loop, waiter_future)` 안전 기상 도입 (`TC-IDX-15`) | 회귀: PASS (146 passed)

### [DEFECT-10] `ActionBar.tsx`의 사진 내보내기 실패 시 "0장 완료" 녹색 체크 허위 표시 및 선택 강제 해제
- **현재 상태**: 🟢 RESOLVED — 백엔드 `failed`/`partial`/`error` SSE 계약 및 `exportStream.ts`·`ActionBar` 상태 머신 연동 (`TC-IDX-16`) | 회귀: PASS (148 passed)

### [DEFECT-11] `DELETE /api/folders`의 등록 여부 미검증으로 인한 상위 경로 전달 시 전체 사진/폴더 재귀적 강제 삭제
- **현재 상태**: 🟢 RESOLVED — 등록 폴더 정확 일치·리프 심볼릭 링크 비확장·활성 인덱싱 409 차단 및 UI 에러 전파 (`TC-IDX-17`) | 회귀: PASS (151 passed)

### [DEFECT-12] 인덱싱 취소(`cancel()`) 직후 인플라이트 워커 스레드 종료 전 조기 상태 해제로 인한 좀비 사진 잔류 및 중복 인덱서 실행
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정 파일**: [`backend/app/services/indexing_state.py`](../../../backend/app/services/indexing_state.py), [`backend/app/services/indexing_service.py`](../../../backend/app/services/indexing_service.py), [`backend/app/services/folder_manager.py`](../../../backend/app/services/folder_manager.py), [`backend/app/services/pipeline.py`](../../../backend/app/services/pipeline.py), [`backend/app/api/indexing.py`](../../../backend/app/api/indexing.py), [`src/types/system.ts`](../../../src/types/system.ts), [`src/store/useAppStore.ts`](../../../src/store/useAppStore.ts), [`src/hooks/useIndexingStatus.ts`](../../../src/hooks/useIndexingStatus.ts), [`src/hooks/useTauriEvents.ts`](../../../src/hooks/useTauriEvents.ts), [`src/components/sidebar/IndexingProgressCard.tsx`](../../../src/components/sidebar/IndexingProgressCard.tsx)
  - **원인 및 조치**: Devil's Advocate 검증을 거쳐 `IndexingStateManager`에 `_in_flight_run_id`·`active_run_in_flight`·`_active_folder_deletions` 상호 배제 슬롯·`rollback_preempted_start`를 도입하고, `run_indexing_background`가 `initialize_background_run(..., track_execution=True)`로 진입한 뒤 `cancel()` 호출 시 워커 종료 전까지 `"cancelling"` 드레인 상태를 유지(2연타 멱등 `True`, 미실행 상태에서는 즉시 `"cancelled"` 호환 유지)하며 `finalize_run` 종료 시점에만 `"cancelled"` 및 `active_run_in_flight=False`로 해제하도록 교정함. 또한 `folder_manager.execute_folder_deletion` ↔ `try_start_indexing` 원자적 상호 배제(`409`/`400`), `IndexingPipeline.run` 스텝별 취소 가드(고아 썸네일/VLM 지연 차단), `_commit_batch_with_retry` 재시도 취소 중단, 프론트엔드 `'cancelling'` 잠금 유지(`isIndexing=true`, 500ms 폴링) 및 `terminalEventSeq` 기반 Tauri↔Polling 상태 역전 차단을 적용함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_backend_hardening.py -k test_tc_idx_18 -v` (`3 passed`), `./venv/bin/pytest backend/tests/ -k "not test_base_keep_alive_model_lifecycle" -q` (`168 passed, 1 deselected`), `npx tsc --noEmit && npm run build` (`PASS`, `0 Errors`)

### [DEFECT-13] `PhotoRepository.list_photos`의 `parent_dir ==` 정확 일치 필터로 인한 하위 폴더 및 macOS NFD 경로 사진 전면 누락
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정 파일**: [`backend/app/utils/path.py`](../../../backend/app/utils/path.py), [`backend/app/repositories/photo_repository.py`](../../../backend/app/repositories/photo_repository.py), [`backend/app/services/folder_manager.py`](../../../backend/app/services/folder_manager.py)
  - **원인 및 조치**: 단방향 계층 의존성(`Services ➔ Repositories ➔ Utils`)을 준수하도록 [`backend/app/utils/path.py`](../../../backend/app/utils/path.py)를 신설해 `folder_manager.py`와 공유하는 `resolve_path_without_leaf_symlink`·`normalize_path_preserving_leaf_symlink`·`to_slash_bounded_prefix`·`is_path_within_folder`를 분리함. `PhotoRepository.list_photos`에서 `parent_dir` 지정 시 SQL `==` 정확 일치 대신 `capture_date DESC NULLS LAST, id ASC` 정렬된 `(id, parent_dir)` 경량 투영을 조회한 뒤, 디렉터리별 정규화 결과 캐시를 적용한 slash-bounded + NFC/대소문자/말단슬래시/리프 심볼릭 링크 비확장 필터(`_filter_matching_photo_ids`)로 `matching_ids`를 산출하고 `offset:offset+limit` 슬라이스 ID만 `get_by_ids`로 로드해 페이지네이션 정합성과 정렬을 보장함(공백 `parent_dir` 및 `limit<=0` 가드 포함).
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_backend_hardening.py -k test_tc_idx_19 -v` (`1 passed`), `./venv/bin/pytest backend/tests/test_api_photos.py backend/tests/test_api_folders.py backend/tests/test_api_search.py backend/tests/test_backend_hardening.py -k "not test_base_keep_alive_model_lifecycle" -v` (`55 passed, 1 deselected`), `./venv/bin/pytest backend/tests/ -k "not test_base_keep_alive_model_lifecycle" -q` (`169 passed, 1 deselected`), `npx tsc --noEmit && npm run build` (`PASS`, `0 Errors`)

### [DEFECT-14] `usePhotoDetail.handleReindex`의 React Query `photoDetail` 캐시 미갱신 및 사진 전환 시 타 사진 편집 버퍼 오염
- **현재 상태**: 🟡 OPEN
- **심각도**: 🟠 P1 High (Stale Cache & Cross-Item State Corruption)
- **발생 위치**: [`src/hooks/usePhotoDetail.ts#L246-L258`](../../../src/hooks/usePhotoDetail.ts#L246-L258), [`src/hooks/usePhotoDetailQuery.ts#L6-L18`](../../../src/hooks/usePhotoDetailQuery.ts#L6-L18)
- **증상 및 재현**: 재분석 성공 시 `['photoDetail', targetId]` 캐시(`staleTime: 5m`) 및 `['photos']`를 갱신하지 않아 구 데이터가 유지되며, 비동기 대기 중 다른 사진 선택 시 새 사진의 편집 버퍼가 덮어쓰여짐 (`✅ Deterministic Trace Verified`).

### [DEFECT-15] `useToggleFavoriteMutation`의 `selectedFolder=null` 하드코딩 및 `photoDetail` 캐시 미동기화로 인한 하트 상태 불일치
- **현재 상태**: 🟡 OPEN
- **심각도**: 🟠 P1 High (Query Key Mismatch / Cache Split-Brain)
- **발생 위치**: [`src/hooks/usePhotoDetail.ts#L29,L260-L267`](../../../src/hooks/usePhotoDetail.ts#L29), [`src/hooks/usePhotosQuery.ts#L8-L53`](../../../src/hooks/usePhotosQuery.ts#L8-L53), [`src/components/PhotoGallery.tsx#L100-L121`](../../../src/components/PhotoGallery.tsx#L100-L121)
- **증상 및 재현**: 상세 패널 훅이 `selectedFolder`를 `null`로 고정하고, 갤러리·상세 양쪽 모두 `['photoDetail', photoId]` 캐시를 갱신하지 않아 폴더 뷰/상세 뷰에서 하트 토글 상태가 반영되지 않음 (`✅ Empirical Probe Reproduced`).

### [DEFECT-16] 내보내기 진행 중 전체 선택 해제 시 `usePhotoExport`의 완료/실패 피드백이 이후 새 선택에 잔류
- **현재 상태**: 🟡 OPEN
- **심각도**: 🟠 P1 High (Async Lifecycle / Stale State Leak)
- **발생 위치**: [`src/hooks/usePhotoExport.ts#L64-L69,L96-L145`](../../../src/hooks/usePhotoExport.ts#L64-L69), [`src/components/ActionBar.tsx#L19,L49-L57`](../../../src/components/ActionBar.tsx#L19)
- **증상 및 재현**: `selectedPhotoIds.size === 0`일 때 진행 중이던 SSE 요청을 abort/무효화하지 않아, 뒤늦게 완료/실패한 응답이 `feedback`을 세팅하고 다음 사진 선택(`0 -> 1`) 시 이전 배너가 새 `[내보내기]` 버튼을 가림 (`✅ Deterministic Trace Verified`).

### [DEFECT-17] `_resize_image_to_jpeg_bytes`의 세로 초장축 이미지 JPEG 65,500px 한계 초과 `OSError` 크래시
- **현재 상태**: 🟡 OPEN
- **심각도**: 🟠 P1 High (Edge-Case Crash / Indexing & Thumbnail Failure)
- **발생 위치**: [`backend/app/services/photo.py#L28-L39`](../../../backend/app/services/photo.py#L28-L39)
- **증상 및 재현**: 가로폭만 `360px`로 고정하고 세로 상한을 제한하지 않아 `height/width > 181.94` 초장축 이미지(`10x5000`, `100x20000`) 저장 시 libjpeg 65,500px 한계 초과 `OSError`로 인덱싱/썸네일 서빙이 실패함 (`✅ Empirical Probe Reproduced`).

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `PhotoMetadata` 프론트엔드 타입 필드 불일치 해소, 라우터 직접 DB 쿼리 캡슐화 및 캐시 예외 로깅
- **현재 상태**: 🟢 RESOLVED — `PhotoMetadata` 필드 통일, `PhotoRepository` 캡슐화, 썸네일 캐시 명시적 예외 처리 및 로깅 적용 완료 | 회귀: PASS (99 passed)

### [REFACTOR-02] `indexing_service.py`(819줄) 책임별 모듈 분리, `ActionBar.tsx`·`Sidebar.tsx` 300줄 이하 경량화 및 빈 `catch`/`any` 정리
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🟡 Should Fix (권장 조치)
- **해결 내역**:
  - **수정 및 신설 파일**: [`backend/app/services/folder_manager.py`](../../../backend/app/services/folder_manager.py), [`backend/app/services/photo_reindex.py`](../../../backend/app/services/photo_reindex.py), [`backend/app/services/indexing_service.py`](../../../backend/app/services/indexing_service.py), [`backend/app/api/photos.py`](../../../backend/app/api/photos.py), [`src/hooks/usePhotoExport.ts`](../../../src/hooks/usePhotoExport.ts), [`src/components/actionbar/ExportActionControls.tsx`](../../../src/components/actionbar/ExportActionControls.tsx), [`src/components/ActionBar.tsx`](../../../src/components/ActionBar.tsx), [`src/components/sidebar/SidebarViewTabs.tsx`](../../../src/components/sidebar/SidebarViewTabs.tsx), [`src/components/sidebar/SidebarSearchControls.tsx`](../../../src/components/sidebar/SidebarSearchControls.tsx), [`src/components/sidebar/SidebarFolderActions.tsx`](../../../src/components/sidebar/SidebarFolderActions.tsx), [`src/components/Sidebar.tsx`](../../../src/components/Sidebar.tsx), [`src/components/sidebar/IndexingProgressCard.tsx`](../../../src/components/sidebar/IndexingProgressCard.tsx), [`src/utils/exportStream.ts`](../../../src/utils/exportStream.ts)
  - **원인 및 조치**: `indexing_service.py`(819줄)에서 경로/유니코드 정규화·좀비 정리·폴더 삭제 검증/실행 도메인 로직을 `folder_manager.py`(333줄)로, 단건 재인덱싱 로직을 `photo_reindex.py`(167줄)로 SRP 분리하고 기존 테스트/라우터의 `monkeypatch`·`patch` 호환성을 위한 위임 래퍼를 유지해 `indexing_service.py`를 494줄로 경량화함. `_commit_batch_with_retry`, `run_indexing_background`, `scan_directory`, `photos.py`의 `_stream_export_events`를 30줄·중첩 2단계 이하 헬퍼로 분할함. 프론트엔드 `ActionBar.tsx`(357줄 ➔ 62줄)는 `usePhotoExport.ts`(148줄)·`ExportActionControls.tsx`(211줄)로, `Sidebar.tsx`(359줄 ➔ 86줄)는 `SidebarViewTabs.tsx`(91줄)·`SidebarSearchControls.tsx`(98줄)·`SidebarFolderActions.tsx`(138줄)로 분할하고 `IndexingProgressCard.tsx`·`Sidebar.tsx`의 `catch (e: any)`를 `catch (err: unknown)` 및 공유 핸들러로, `exportStream.ts#L69`의 빈 `catch`에 `console.debug` 로깅을 보강함.
  - **회귀 테스트 결과**: `npx tsc --noEmit && npm run build` (`PASS`, `0 Errors`), `./venv/bin/pytest backend/tests/test_api_indexing.py backend/tests/test_api_folders.py backend/tests/test_api_photos.py backend/tests/test_concurrency_hardening.py backend/tests/test_siglip_zero_shot.py -v` (`21 passed`), `./venv/bin/pytest backend/tests/test_backend_hardening.py -k "not test_base_keep_alive_model_lifecycle" -v` (`34 passed, 1 deselected`, 헤드리스 샌드박스 MPS `torch.mps.synchronize()` segfault 테스트 제외)
