# 🧪 [01_indexing_storage] Verification & Ticket Logs

- **검증 상태**: `🟢 Sign-Off 대기 (Baseline AC 검증 완료 / To-Be 3건 대기 / REFACTOR 0건)`
- **인수 조건 통과율**: `1 / 4 (Baseline 100%)`
- **미해결 티켓**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 0건`

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

---

## 🚨 3. 결함 리포트 (Defect Logs)

*(현재 등록된 OPEN 결함 없음)*

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `PhotoMetadata` 프론트엔드 타입 필드 불일치 해소, 라우터 직접 DB 쿼리 캡슐화 및 캐시 예외 로깅
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🟡 Should Fix (권장 조치)
- **해결 내역**:
  - **수정 파일**: [`src/types/photo.ts`](file:///Users/kimbeomjun/focal_node/src/types/photo.ts#L15-L35), [`src/components/gallery/PhotoCard.tsx`](file:///Users/kimbeomjun/focal_node/src/components/gallery/PhotoCard.tsx#L32-L40), [`backend/app/repositories/photo_repository.py`](file:///Users/kimbeomjun/focal_node/backend/app/repositories/photo_repository.py#L234-L253), [`backend/app/api/folders.py`](file:///Users/kimbeomjun/focal_node/backend/app/api/folders.py#L13-L17), [`backend/app/api/indexing.py`](file:///Users/kimbeomjun/focal_node/backend/app/api/indexing.py#L36-L56), [`backend/app/services/indexing_service.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/indexing_service.py#L101-L128), [`backend/app/services/photo.py`](file:///Users/kimbeomjun/focal_node/backend/app/services/photo.py#L57-L63), [`backend/app/api/photos.py`](file:///Users/kimbeomjun/focal_node/backend/app/api/photos.py#L66-L75), [`backend/tests/test_api_folders.py`](file:///Users/kimbeomjun/focal_node/backend/tests/test_api_folders.py#L48-L67)
  - **원인 및 조치**:
    1. `PhotoMetadata` 필드명을 백엔드 `PhotoMetadataSchema` 및 프론트엔드 `PhotoDetail`과 일치하도록 `focal_length_35mm`, `shutter_speed`로 통일하고 `PhotoCard.tsx` 참조 갱신.
    2. `PhotoRepository`에 `list_folders()`, `get_folder_by_path()`, `add_folder()` 메서드를 추가하여 `folders.py` 및 `indexing.py`의 직접 DB 쿼리를 레포지토리 호출로 캡슐화.
    3. 썸네일 캐시 읽기/정리/삭제 시 `except Exception: pass` 묵인을 제거하고 명시적 `FileNotFoundError` 및 `OSError` 처리와 `logger.warning`/`logger.debug` 로깅 추가.
  - **회귀 테스트 결과**: `npx tsc --noEmit && npm run build` (PASS), `./venv/bin/pytest backend/tests/` (99 passed)
