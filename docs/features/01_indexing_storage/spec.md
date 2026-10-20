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
* `POST /api/photos/{id}/reindex` ➔ `200 OK: PhotoDetailResponse` (단일 사진 썸네일/EXIF/SigLIP 2/Gemma 4 강제 재분석. 단, `[To-Be]` `is_user_edited == True`인 경우 수동 편집된 `caption`/`tags`는 보존하고 임베딩과 `aesthetic_tags`만 갱신)
* `GET /api/photos/{id}/thumbnail` ➔ `200 OK: image/jpeg` (360px sRGB 캐시 우선 서빙, 미스 시 `MAX_CONCURRENT_DECODES=3` 생성 후 캐싱)
* `GET /api/photos/{id}/original?raw=true` ➔ `200 OK: image/jpeg` (RAW 포맷은 `MAX_CONCURRENT_DECODES=3` 세마포어 내 `rawpy` 인메모리 JPEG 디코딩 스트리밍, 일반 이미지는 `FileResponse` 직접 서빙)
* `POST /api/photos/export` (`{ "photo_ids": str[], "destination_folder": str }`) ➔ `200 OK: text/event-stream` (SSE 진행률)

### 2.2. 폴더 및 인덱싱 제어 API (`/api/folders`, `/api/index`)
* `GET /api/folders` ➔ `200 OK: string[]` `[As-Is]`
* `DELETE /api/folders?path=...` ➔ `202 Accepted` `[As-Is]`
* `POST /api/folders/prune-offline` ➔ `200 OK: { "purged_count": int }` `[To-Be 신규]` (`is_offline = True`인 고아 레코드 및 썸네일/벡터를 사용자 명시 요청 시에만 영구 정리)
* `POST /api/index/start` (`{ "folder_paths": str[] }`) | `POST /api/index/sync` ➔ `202 Accepted` `[As-Is]`
* `POST /api/index/pause` | `POST /api/index/resume` | `POST /api/index/cancel` ➔ `200 OK` `[As-Is]`
* `GET /api/index/status` ➔ `200 OK: IndexingStatusResponse` (`[To-Be]` `phase?: "idle" | "fast_preview" | "ai_enrichment"` 필드 포함)

---

## 💻 3. 프론트엔드 타입 및 상태 계약 (`src/types/photo.ts`)

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
  is_offline?: boolean; // [To-Be] 외장 볼륨 분리/파일 실종 배지용
  has_ai_analysis?: boolean; // [To-Be] 2-Pass 중 Pass 1만 완료된 상태 식별용
  metadata?: PhotoMetadata | null;
}
```

---

## 🛡️ 4. 핵심 비즈니스 로직 및 엣지 케이스 정책

1. **SHA-256 기반 파일 이동·이름 변경 자동 재연결 (`Relocation`) `[To-Be]`**:
   - 인덱싱 중 계산된 `image_id`(SHA-256)가 이미 `images` 테이블에 존재(`existing_by_id`)하고 경로(`file_path`)가 다를 때:
     - **Case A (원본 경로 파일 실종 또는 `is_offline == True`)**: 파일 이동 또는 이름 변경(`relocated`)으로 판정하여 기존 레코드의 `file_path`, `parent_dir`, `file_name`, `file_mtime`, `file_size` 및 `is_offline = False`만 In-place 업데이트합니다. (AI 재추론 0회, 기존 `is_favorite`, `is_user_edited` 캡션/태그, `critique` 100% 보존)
     - **Case B (원본 경로 파일도 실제로 존재함)**: 물리적 중복 복사본이므로 `"skipped_duplicate_hash"`로 스킵합니다.
2. **2-Pass 점진적 인덱싱 (Fast Preview ➔ AI Enrichment) `[To-Be]`**:
   - **Pass 1 (`phase = "fast_preview"`)**: 신규 파일의 `SHA-256 해싱 + 360px 썸네일 캐싱 + EXIF 추출`만 고속 실행하여 `images`와 `image_metadata`에 즉시 커밋합니다. 사용자는 폴더 등록 수 초 내에 갤러리 탐색 및 EXIF 필터링을 사용할 수 있습니다.
   - **Pass 2 (`phase = "ai_enrichment"`)**: `ai_analysis`가 아직 생성되지 않은 사진들을 대상으로 백그라운드에서 `SigLIP 2 임베딩 + Gemma 4 캡션/태그`를 추론하고 `CompensatingTransactionManager`로 ChromaDB와 SQLite에 원자적으로 기록합니다.
3. **외장 드라이브 분리 시 비파괴적 보존 (`[To-Be]`)**: Pass 1 스캔 및 Relocation 완료 후에도 `os.path.exists(file_path) == False`인 레코드는 삭제하지 않고 `is_offline = True`로 전환하여 썸네일과 AI 비평을 보존합니다.
