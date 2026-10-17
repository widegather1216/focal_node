# [Spec & Contracts] 01. Indexing Pipeline, Storage & RAW Media

---

## 💾 1. 데이터베이스 스키마 명세 (`backend/app/models.py`)

### 1.1. `[As-Is 기구현]` SQLite 테이블 (`images`, `image_metadata`, `indexed_folders`)
```sql
CREATE TABLE images (
    id VARCHAR(64) PRIMARY KEY,              -- SHA-256 해시값 (ChromaDB ID와 동일)
    parent_dir VARCHAR(1024) NOT NULL,       -- 부모 디렉터리 경로 (인덱스)
    file_path VARCHAR(1024) NOT NULL UNIQUE, -- 원본 파일 절대 경로
    file_name VARCHAR(256) NOT NULL,
    file_size INTEGER NOT NULL,
    file_mtime FLOAT NOT NULL,
    mime_type VARCHAR(50) NOT NULL,
    is_favorite BOOLEAN DEFAULT 0 NOT NULL,  -- 즐겨찾기 여부 (인덱스)
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE image_metadata (
    image_id VARCHAR(64) PRIMARY KEY REFERENCES images(id) ON DELETE CASCADE,
    width INTEGER, height INTEGER,
    color_space VARCHAR(30) DEFAULT 'sRGB',
    camera_model VARCHAR(100),               -- 인덱스
    lens_model VARCHAR(100),                 -- 인덱스
    f_number FLOAT,                          -- 인덱스
    focal_length FLOAT,                      -- 물리 초점거리 (인덱스)
    focal_length_35mm FLOAT,                 -- 35mm 환산 초점거리
    crop_factor FLOAT,
    sensor_format VARCHAR(50),
    shutter_speed VARCHAR(30),
    iso INTEGER,                             -- 인덱스
    capture_date DATETIME                    -- 실제 촬영 일시 (인덱스)
);

CREATE TABLE indexed_folders (
    path VARCHAR(1024) PRIMARY KEY,
    created_at DATETIME NOT NULL
);
```

### 1.2. `[To-Be / Migration Required]` 스마트 오프라인 컬럼 추가
* **대상 테이블**: `images`
* **추가 컬럼**: `is_offline BOOLEAN DEFAULT 0 NOT NULL` (`idx_images_is_offline` 인덱스 포함)
* **마이그레이션 규칙**: 앱 기동 시 `ALTER TABLE images ADD COLUMN is_offline BOOLEAN DEFAULT 0 NOT NULL` 안전 체크 적용.

### 1.3. `[As-Is 기구현]` ChromaDB 컬렉션 (`photo_embeddings`)
* **메트릭**: `hnsw:space = "cosine"` | **차원**: 768차원 (`SigLIP 2`) | **PK**: `images.id` (SHA-256)

---

## 🌐 2. 백엔드 REST API 계약

### 2.1. 사진 및 미디어 API (`/api/photos`) `[As-Is 기구현]`
* `GET /api/photos?limit=50&offset=0&parent_dir=...` ➔ `200 OK: PhotoListResponse[]`
* `GET /api/photos/{id}` ➔ `200 OK: PhotoDetailResponse` (`metadata`, `ai_analysis` 포함) / `404 Not Found`
* `POST /api/photos/{id}/favorite` ➔ `200 OK: { "id": str, "is_favorite": bool }`
* `PATCH /api/photos/{id}/metadata` (`{ "caption"?: str, "tags"?: str[] }`) ➔ `200 OK: { "status": "success", "id": str, "ai_analysis": AIAnalysisSchema }`
* `POST /api/photos/{id}/reindex` ➔ `200 OK: PhotoDetailResponse` (단일 사진 썸네일/EXIF/SigLIP 2/Gemma 4 강제 재분석)
* `GET /api/photos/{id}/thumbnail` ➔ `200 OK: image/jpeg` (360px sRGB 캐시 우선 서빙, 미스 시 `MAX_CONCURRENT_DECODES=3` 생성 후 캐싱)
* `GET /api/photos/{id}/original?raw=true` ➔ `200 OK: image/jpeg` (RAW 포맷은 `MAX_CONCURRENT_DECODES=3` 세마포어 내 `rawpy` 인메모리 JPEG 디코딩 스트리밍, 일반 이미지는 `FileResponse` 직접 서빙)
* `POST /api/photos/export` (`{ "photo_ids": str[], "destination_folder": str }`) ➔ `200 OK: text/event-stream` (SSE 진행률)

### 2.2. 폴더 및 인덱싱 제어 API (`/api/folders`, `/api/index`) `[As-Is 기구현]`
* `GET /api/folders` ➔ `200 OK: string[]` (등록된 인덱싱 폴더 경로 목록)
* `DELETE /api/folders?path=...` ➔ `202 Accepted` (폴더 등록 해제 및 하위 사진/썸네일/벡터 백그라운드 정리)
* `POST /api/index/start` (`{ "folder_paths": str[] }`) ➔ `202 Accepted` (신규 폴더 DB 등록 및 백그라운드 인덱싱 시작)
* `POST /api/index/sync` ➔ `202 Accepted` (전체 등록 폴더 재스캔 및 삭제 파일 동기화)
* `POST /api/index/pause` | `POST /api/index/resume` | `POST /api/index/cancel` ➔ `200 OK`
* `GET /api/index/status` ➔ `200 OK: IndexingStatusResponse` (JSON Polling 방식 진행률 조회)

---

## 💻 3. 프론트엔드 타입 및 상태 계약 (`src/types/photo.ts`, `src/hooks/usePhotoDetail.ts`)

```typescript
export interface Photo {
  id: string;
  file_path: string;
  file_name: string;
  file_size: number;
  created_at: string;
  caption?: string | null;
  tags?: string | null;
  is_favorite: boolean;
  is_offline?: boolean; // [To-Be] 오프라인 상태 배지용
  metadata?: PhotoMetadata | null;
}
```

---

## 🛡️ 4. 예외 처리 및 엣지 케이스 정책

1. **고속 RAW 디코딩 및 손상 파일 방어 (`utils/image.py`, `services/photo.py`)**: `decode_raw_to_pil`은 속도를 위해 내장 EXIF 썸네일(`raw.extract_thumb()`) 추출을 1차로 시도하고 실패 시 `raw.postprocess()`로 폴백합니다. 파일 손상으로 디코딩이 불가능할 경우 API는 `422 Unprocessable Entity`를 반환하며, 백그라운드 인덱싱 파이프라인은 해당 파일만 에러 로깅 후 스킵하여 전체 배치 루프 중단을 방지합니다.
2. **외장 드라이브 분리 시 비파괴적 보존 (`[To-Be]`)**: 파일 접근 불가(`os.path.exists == False`) 시 레코드를 자동 삭제하지 않고 `is_offline = True`로 전환하여 기존 AI 비평과 썸네일 캐시를 보존합니다.
