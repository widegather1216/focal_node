# 🧪 [01_indexing_storage] Verification & Ticket Logs

- **검증 상태**: `🩹 Debugging (딥버그 헌팅 DEFECT 11건 발권 / Baseline AC 재검증 대기)`
- **인수 조건 통과율**: `1 / 4 (Baseline 100%)`
- **미해결 티켓**: `🚨 DEFECT: 11건` | `🧐 REFACTOR: 0건`

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
| **Boundary**| `TC-IDX-07` | ChromaDB 임베딩 조회 ndarray 불리언 예외 방지 | `get_embedding_by_id` 호출 | ndarray 불리언 평가 에러 없이 list 반환 | `FAIL (DEFECT-01)` |
| **Boundary**| `TC-IDX-08` | ChromaDB 삭제 실패 시 보상 트랜잭션 롤백 | `delete_and_commit` 시 Chroma 에러 | SQLite 삭제 취소 및 예외 재전파 | `FAIL (DEFECT-02)` |
| **Boundary**| `TC-IDX-09` | 인덱싱/동기화 동시 호출 시 TOCTOU 방지 | `start` + `sync` 동시 호출 | 단일 태스크만 시작되고 벡터 소실 차단 | `FAIL (DEFECT-03)` |
| **Negative**| `TC-IDX-10` | 배치 커밋 실패 시 에러 전파 및 거짓 완료 차단 | `_commit_batch_with_retry` 3회 실패 | 예외 raise 및 status="error" 전이 | `FAIL (DEFECT-04)` |
| **Boundary**| `TC-IDX-11` | 수정 파일 재인덱싱 중단 시 기존 레코드 보존 | 재인덱싱 중 취소/실패 주입 | 신규 커밋 전 구 레코드 조기 삭제 차단 | `FAIL (DEFECT-05)` |
| **Boundary**| `TC-IDX-12` | macOS NFD/NFC 한글 폴더 사진 오삭제 방지 | 한글 폴더 NFD/NFC 동기화 | 좀비 오판 차단 및 사진 보존 | `FAIL (DEFECT-06)` |
| **Negative**| `TC-IDX-13` | ExifRead 빈 리스트(`values=[]`) 파싱 안정성 | 손상/초과 IFD 태그 파싱 | IndexError 방지 및 나머지 EXIF 보존 | `FAIL (DEFECT-07)` |
| **Boundary**| `TC-IDX-14` | 비동기 미디어 라우트 내 동기 DB I/O 격리 | 썸네일/원본/내보내기 동시 요청 | 메인 비동기 이벤트 루프 동결 방지 | `FAIL (DEFECT-08)` |
| **Boundary**| `TC-IDX-15` | IndexingStateManager 크로스 스레드 루프 바인딩 | 백그라운드 스레드 pause/resume | call_soon_threadsafe 안전 전달 | `FAIL (DEFECT-09)` |
| **Negative**| `TC-IDX-16` | 사진 내보내기 실패 시 에러 보존 및 UI 피드백 | 0장 내보내기 에러 응답 수신 | 허위 녹색 완료 차단 및 실패 안내 | `FAIL (DEFECT-10)` |
| **Security**| `TC-IDX-17` | 폴더 삭제 시 미등록 상위 경로 재귀 삭제 차단 | DELETE /api/folders?path=/ | 미등록 상위 경로 요청 거부 및 데이터 보호 | `FAIL (DEFECT-11)` |

---

## 🚨 3. 결함 리포트 (Defect Logs)

### [DEFECT-01] `VectorRepository.get_embedding_by_id`의 NumPy array 불리언 평가로 인한 100% `ValueError` 크래시
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🔴 P0 Critical (Runtime Crash / 100% Reproducible)
- **위치**: [`backend/app/repositories/vector_repository.py#L56-L62`](../../../backend/app/repositories/vector_repository.py#L56-L62)
- **실증 여부**: `✅ Empirical Probe Reproduced`
- **근본 원인 분석**: `VectorRepository.get_embedding_by_id`에서 `collection.get(..., include=["embeddings"])`가 반환하는 `embeddings` 필드는 Python 리스트가 아닌 `numpy.ndarray`임. `if target_data.get('embeddings'):` 불리언 평가 시 `ValueError: The truth value of an array with more than one element is ambiguous.`가 발생하여 단일 사진 재인덱싱(`POST /api/photos/{id}/reindex`) 및 유사도 검색이 100% 크래시함. Mock 테스트로 인해 은폐되어 있었음.
- **수정 설계 방향**: `emb = target_data.get('embeddings')` 추출 후 불리언 평가 대신 `emb is not None and len(emb) > 0` 검사 및 `.tolist()` 변환 반환.

### [DEFECT-02] `VectorRepository.delete`의 예외 삼킴으로 인한 보상 트랜잭션 무력화 및 좀비 벡터 영구 잔류
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🔴 P0 Critical (Multi-Store Consistency & Zombie Vectors)
- **위치**: [`backend/app/repositories/vector_repository.py#L33-L37`](../../../backend/app/repositories/vector_repository.py#L33-L37), [`backend/app/repositories/atomic_transaction.py#L62-L82`](../../../backend/app/repositories/atomic_transaction.py#L62-L82)
- **실증 여부**: `✅ Empirical Probe Reproduced`
- **근본 원인 분석**: `VectorRepository.delete`가 ChromaDB 삭제 실패 시 `except Exception as chroma_err:`에서 로그만 출력하고 예외를 삼킴. `CompensatingTransactionManager.delete_and_commit`은 삭제 성공으로 오판하여 SQLite 커밋을 강행함. SQLite 레코드만 삭제되고 ChromaDB에 좀비 벡터가 영구 잔류하여 유사도 검색 및 페이징이 붕괴됨.
- **수정 설계 방향**: `VectorRepository.delete`에서 예외 발생 시 로깅 후 `raise`로 재전파하여 `delete_and_commit`이 SQLite 롤백을 수행하도록 보장.

### [DEFECT-03] `start_indexing` / `sync_database` TOCTOU 동시성 레이스로 인한 중복 인덱서 실행 및 ChromaDB 벡터 영구 소실
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🔴 P0 Critical (Concurrency Race & Data Desync)
- **위치**: [`backend/app/api/indexing.py#L20-L45`](../../../backend/app/api/indexing.py#L20-L45), [`L50-L71`](../../../backend/app/api/indexing.py#L50-L71), [`backend/app/repositories/atomic_transaction.py#L49-L60`](../../../backend/app/repositories/atomic_transaction.py#L49-L60)
- **실증 여부**: `✅ Deterministic Trace Verified`
- **근본 원인 분석**: 상태 검사(`status in [...]`) 후 락 없이 `add_folder`, `db.commit()`을 거친 뒤 `status="processing"`을 설정함. 동시 호출 시 두 개의 `run_indexing_background`가 병렬 구동되어 동일 배치를 커밋 시도함. Run 1이 정상 저장한 후 Run 2가 커밋 시도 시 SQLite UNIQUE constraint 에러가 발생하며, Run 2의 `CompensatingTransactionManager`가 `vector_repo.delete(image_ids)`를 실행하여 Run 1이 저장한 정상 ChromaDB 벡터를 소실시킴.
- **수정 설계 방향**: 상태 확인 및 "processing" 전이를 원자적 락(`threading.Lock`) 하에서 수행하고, 인덱싱 시작 즉시 `status = "processing"`을 선점.

### [DEFECT-04] `_commit_batch_with_retry` 3회 실패 시 예외 삼킴으로 인한 대규모 사진 유실 및 거짓 정상 완료 위장
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🔴 P0 Critical (Silent Degradation & Cross-Layer Data Loss)
- **위치**: [`backend/app/services/indexing_service.py#L435-L453`](../../../backend/app/services/indexing_service.py#L435-L453), [`L542-L553`](../../../backend/app/services/indexing_service.py#L542-L553)
- **실증 여부**: `✅ Empirical Probe Reproduced`
- **근본 원인 분석**: 배치 커밋 3회 실패 시 `traceback.print_exc()`만 찍고 아무런 예외도 raise하지 않고 `None` 반환. 상위 비동기 루프는 실패를 인지하지 못해 에러 카운터 증가나 에러 상태 전이 없이 다음 청크로 넘어가고, 최종적으로 `status="idle"`로 완료를 선언함. UI는 100% 완료로 표시하나 수백 장의 사진 데이터가 영구 유실됨.
- **수정 설계 방향**: 3회 실패 시 최종 예외를 `raise`하여 상위 루프가 실패를 인지하고 `indexing_state_manager.status = "error"`로 전이하도록 처리.

### [DEFECT-05] `index_single_file_sync`의 선행 삭제(Delete-Before-Commit)로 인한 수정 파일 재인덱싱 취소/실패 시 데이터 영구 증발
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🔴 P0 Critical (Data Loss on Interrupted Reindexing)
- **위치**: [`backend/app/services/indexing_service.py#L278-L281`](../../../backend/app/services/indexing_service.py#L278-L281), [`L303-L310`](../../../backend/app/services/indexing_service.py#L303-L310)
- **실증 여부**: `✅ Deterministic Trace Verified`
- **근본 원인 분석**: 수정된 파일 재인덱싱 시 신규 배치 커밋 전에 구 해시 레코드를 `delete_photo_atomic_sync`로 즉시 커밋 삭제함. 신규 배치가 커밋되기 전에 취소되거나 에러 발생 시 구 데이터는 이미 삭제되었고 신규 데이터는 커밋되지 않아 사진이 완전히 증발함.
- **수정 설계 방향**: 구 레코드 삭제를 파이프라인 즉시 커밋하지 않고, 신규 배치가 성공적으로 커밋된 후에 정리하도록 순서 조정.

### [DEFECT-06] macOS 유니코드 정규화(NFD vs NFC) 불일치로 인한 `_identify_zombie_photo_ids`의 한글 폴더 사진 전량 오삭제
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🔴 P0 Critical (False-Positive Data Purge)
- **위치**: [`backend/app/services/indexing_service.py#L132-L147`](../../../backend/app/services/indexing_service.py#L132-L147)
- **실증 여부**: `✅ Empirical Probe Reproduced`
- **근본 원인 분석**: UI/Tauri에서 전달된 폴더 경로(NFC)와 macOS APFS 파일시스템 경로(NFD)의 바이트 시퀀스가 달라 `unicodedata.normalize` 없는 `startswith()` 비교가 `False`를 반환함. 파일이 실제 디스크에 존재함에도 좀비로 오인되어 다음 동기화 시 정상 한글 사진들이 전량 오삭제됨.
- **수정 설계 방향**: 경로 정규화 시 `unicodedata.normalize("NFC", ...)`를 적용하여 NFD/NFC 정규화 차이로 인한 비교 실패 차단.

### [DEFECT-07] `_get_tag_val`의 `tag.values == []` 빈 리스트 `IndexError`로 인한 EXIF 메타데이터 파싱 전면 중단
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🟠 P1 High (Partial Metadata Loss)
- **위치**: [`backend/app/utils/image.py#L102`](../../../backend/app/utils/image.py#L102)
- **실증 여부**: `✅ Empirical Probe Reproduced`
- **근본 원인 분석**: ExifRead가 비정상/손상 필드에 대해 `values = []`를 반환할 때, `tag.values[0]` 접근 시 `IndexError`가 발생하여 전체 EXIF 파싱이 중단되고 모든 메타데이터가 누락됨.
- **수정 설계 방향**: `isinstance(tag.values, list) and len(tag.values) > 0` 검사 후 `tag.values[0]` 접근.

### [DEFECT-08] `photos.py` 비동기 엔드포인트 내 동기 DB I/O 호출로 인한 FastAPI 단일 비동기 이벤트 루프 동결
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🟠 P1 High (Event Loop Freeze / Denial of Service)
- **위치**: [`backend/app/api/photos.py#L52-L58`](../../../backend/app/api/photos.py#L52-L58), [`L90-L97`](../../../backend/app/api/photos.py#L90-L97), [`L205-L210`](../../../backend/app/api/photos.py#L205-L210)
- **실증 여부**: `✅ Deterministic Trace Verified`
- **근본 원인 분석**: `get_photo_thumbnail`, `get_photo_original`, `export_photos`가 `async def`로 선언되었으나 `photo_repo.get_by_id` 및 `photo_repo.get_by_ids` 동기 쿼리를 `asyncio.to_thread` 없이 직접 실행함. 백그라운드 인덱싱 DB 쓰기 락 경합 시 메인 비동기 루프가 동결됨.
- **수정 설계 방향**: DB 세션 쿼리 호출부를 `await asyncio.to_thread(...)`로 오프로딩.

### [DEFECT-09] `IndexingStateManager._pause_loop` 영구 `None` 고착으로 인한 크로스 스레드 `call_soon_threadsafe` 누락 및 이벤트 루프 블로킹
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🟠 P1 High (Concurrency Hang)
- **위치**: [`backend/app/services/indexing_state.py#L40-L47`](../../../backend/app/services/indexing_state.py#L40-L47), [`L58-L81`](../../../backend/app/services/indexing_state.py#L58-L81)
- **실증 여부**: `✅ Empirical Probe Reproduced`
- **근본 원인 분석**: 루프 재바인딩 조건문 `self._pause_loop is not None and self._pause_loop != current_loop` 오류로 인해 최초 `None`일 때 영원히 `None`으로 유지됨. `_set_event_safe`가 `call_soon_threadsafe`를 호출하지 못하고 크로스 스레드에서 직접 `set()`/`clear()`를 호출하여 메인 이벤트 루프 셀프 파이프를 깨우지 못함.
- **수정 설계 방향**: `if current_loop is not None and (self._pause_loop is None or self._pause_loop != current_loop):`로 조건 수정.

### [DEFECT-10] `ActionBar.tsx`의 사진 내보내기 실패 시 "0장 완료" 녹색 체크 허위 표시 및 선택 강제 해제
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🟠 P1 High (False Success UI Masking)
- **위치**: [`src/components/ActionBar.tsx#L33-L43`](../../../src/components/ActionBar.tsx#L33-L43), [`src/services/api.ts#L109-L154`](../../../src/services/api.ts#L109-L154)
- **실증 여부**: `✅ Deterministic Trace Verified`
- **근본 원인 분석**: `POST /api/photos/export`가 에러로 인해 `status="failed"` 및 0장을 반환해도 `ActionBar.tsx`가 `data.status`를 무시하고 "0장의 사진 내보내기 완료"를 녹색 체크로 띄우며 선택을 해제함.
- **수정 설계 방향**: `data.status === "failed"` 또는 에러 존재 시 실패 알림 붉은색 배너 표시 및 선택 상태 유지.

### [DEFECT-11] `DELETE /api/folders`의 등록 여부 미검증으로 인한 상위 경로 전달 시 전체 사진/폴더 재귀적 강제 삭제
- **현재 상태**: `🟡 OPEN`
- **심각도**: 🟠 P1 High (Arbitrary Mass Deletion)
- **위치**: [`backend/app/api/folders.py#L19-L30`](../../../backend/app/api/folders.py#L19-L30), [`backend/app/services/indexing_service.py#L213-L241`](../../../backend/app/services/indexing_service.py#L213-L241)
- **실증 여부**: `✅ Empirical Probe Reproduced`
- **근본 원인 분석**: `DELETE /api/folders?path=...`가 등록된 `IndexedFolder`인지 검증하지 않고 `remove_folder_data`를 호출하여, 상위 디렉터리(`/` 또는 `/Users/name`) 입력 시 하위의 모든 개별 등록 폴더와 사진을 재귀적으로 일괄 삭제함.
- **수정 설계 방향**: 요청된 경로가 `IndexedFolder`에 등록된 폴더인지 확인 후 일치하는 폴더에 대해서만 삭제 수행.

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `PhotoMetadata` 프론트엔드 타입 필드 불일치 해소, 라우터 직접 DB 쿼리 캡슐화 및 캐시 예외 로깅
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🟡 Should Fix (권장 조치)
- **해결 내역**:
  - **수정 파일**: [`src/types/photo.ts`](file:///Users/kimbeomjun/focal_node/src/types/photo.ts#L15-L35), [`src/components/gallery/PhotoCard.tsx`](file:///Users/kimbeomjun/focal_node/src/components/gallery/PhotoCard.tsx#L32-L40), [`backend/app/repositories/photo_repository.py`](file:///Users/kimbeomjun/focal_node/backend/app/repositories/photo_repository.py#L234-L253), [`backend/app/api/folders.py`](file:///Users/kimbeomjun/focal_node/backend/app/api/folders.py#L13-L17), [`backend/app/api/indexing.py`](file:///Users/kimbeomjun/focal_node/backend/app/api/indexing.py#L36-L56), [`backend/app/services/indexing_service.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/indexing_service.py#L101-L128), [`backend/app/services/photo.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/photo.py#L57-L63), [`backend/app/api/photos.py`](file:///Users/kimbeomjun/focal_node/backend/app/api/photos.py#L66-L75), [`backend/tests/test_api_folders.py`](file:///Users/kimbeomjun/focal_node/backend/tests/test_api_folders.py#L48-L67)
  - **원인 및 조치**: `PhotoMetadata` 필드 통일, `PhotoRepository` 캡슐화, 썸네일 캐시 명시적 예외 처리 및 로깅 적용 완료.
  - **회귀 테스트 결과**: `npx tsc --noEmit && npm run build` (PASS), `./venv/bin/pytest backend/tests/` (99 passed)
