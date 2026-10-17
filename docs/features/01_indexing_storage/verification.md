# 🧪 [01_indexing_storage] Verification & Ticket Logs

- **검증 상태**: `🩹 Open Issues (Baseline AC 검증 완료 / To-Be 1건 대기 / REFACTOR 1건 대기)`
- **인수 조건 통과율**: `1 / 2 (Baseline 100%)`
- **미해결 티켓**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 1건`

---

## 🎯 1. Given-When-Then 인수 조건 (Acceptance Criteria)

### AC 1. 폴더 연동 및 1단계 백그라운드 인덱싱 `[As-Is]`
* **Given:** 사용자가 JPEG 및 RAW(ARW, CR3, NEF)가 포함된 로컬 폴더를 등록했을 때,
* **When:** 백그라운드 인덱싱 파이프라인이 실행되면,
* **Then:**
  1. 각 파일의 SHA-256 해시가 SQLite `images.id`와 ChromaDB `photo_embeddings` ID로 원자적으로 등록되어야 한다.
  2. Thumbnail Cache 디렉토리에 360px sRGB JPEG가 생성되어야 한다.
  3. 이벤트 루프 블로킹 없이 `GET /api/index/status` 폴링 및 Tauri 이벤트로 진행률(0~100%)이 조회되어야 한다.

### AC 2. 비파괴적 스마트 오프라인 관리 `[To-Be]`
* **Given:** 외장 드라이브의 사진이 인덱싱된 상태에서,
* **When:** 외장 드라이브가 언마운트된 후 동기화(`/api/index/sync`)가 실행되면,
* **Then:**
  1. DB에서 레코드가 삭제되지 않고 `images.is_offline = True`로 갱신되어야 한다.
  2. 갤러리에서 캐시된 360px 썸네일이 유지되며 `[Offline]` 배지가 표시되어야 한다.

---

## 🧪 2. 테스트 시나리오 매트릭스 (Test Matrix)

| 구분 | 테스트 ID | 시나리오 설명 | 입력 / 조작 조건 | 기대 결과 | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Happy** | `TC-IDX-01` | 대용량 폴더 1단계 인덱싱 | 500장 폴더 등록 | 해시/EXIF/360px 캐시 및 임베딩 저장 | `PASS` |
| **Boundary**| `TC-IDX-02` | 동시 RAW 디코딩 부하 제어 | 10개 원본 RAW 동시 요청 | 세마포어(3) 동작하여 OOM 방지 | `PASS` |
| **Negative**| `TC-IDX-03` | 손상된 RAW 파일 스캔 | 0바이트 손상 ARW 파일 | 파이프라인 중단 없이 스킵/폴백 | `PASS` |
| **Negative**| `TC-IDX-04` | 외장 드라이브 언마운트 (`[To-Be]`) | 인덱싱된 볼륨 분리 후 동기화 | 레코드 유지 + `is_offline=True` 배지 | `⏳ Pending` |

---

## 🚨 3. 결함 리포트 (Defect Logs)

*(현재 등록된 OPEN 결함 없음)*

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `PhotoMetadata` 프론트엔드 타입 필드 불일치 해소 및 라우터 직접 DB 쿼리 캡슐화
- **심각도**: 🟡 Should Fix (권장 조치)
- **위치**: `src/types/photo.ts#L15-L32`, `src/components/gallery/PhotoCard.tsx#L35-L39`, `backend/app/api/folders.py#L15`, `backend/app/api/indexing.py#L37,L54`, `backend/app/services/indexing_service.py#L105-L122`
- **위반 규칙**: Spec-Code Type Consistency & Repository 계층 캡슐화 (Rule 2.2)
- **발견된 문제**:
  - `src/types/photo.ts`의 `PhotoMetadata`가 레거시 필드명(`focal_length_in_35mm`, `exposure_time`)을 사용하여 백엔드 `PhotoMetadataSchema`(`focal_length_35mm`, `shutter_speed`) 및 `usePhotoDetail.ts`의 `PhotoDetail` 타입과 이원화되어 있음.
  - `api/folders.py` 및 `api/indexing.py`에서 `PhotoRepository`를 거치지 않고 `db.query(IndexedFolder)`를 직접 호출함.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - src/types/photo.ts의 PhotoMetadata 필드를 백엔드 PhotoMetadataSchema(focal_length_35mm, shutter_speed)로 통일하고 PhotoCard.tsx 참조 수정
  - IndexedFolder 조회/생성 메서드를 PhotoRepository로 이전
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)
