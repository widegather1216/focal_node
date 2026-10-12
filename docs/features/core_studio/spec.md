# [Specification & Contracts] 올인원 로컬 포토 스튜디오

본 문서는 **Focal Node: Core Photo Studio**의 정규화 데이터베이스 스키마, 런타임 제약사항을 반영한 지능형 2단계 파이프라인, 실제 코드베이스와 100% 동기화된 REST API 계약 및 엣지 케이스 정책을 정의합니다.

---

## 💾 1. 데이터 모델 및 영속성 명세

SQLite(관계형 메타데이터)와 ChromaDB(벡터 임베딩)는 파일의 **SHA-256 해시값 (`id`)**을 공통 Primary Key로 사용하여 동기화됩니다.

### 1.1. SQLite 3계층 정규화 스키마 (`photos.db`)

#### 1) `images` 테이블 (기본 파일 정보 및 상태)
```sql
CREATE TABLE images (
    id VARCHAR(64) PRIMARY KEY,              -- SHA-256 해시값 (ChromaDB ID와 일치)
    parent_dir VARCHAR(1024) NOT NULL,       -- 부모 디렉터리 경로 (인덱스)
    file_path VARCHAR(1024) NOT NULL UNIQUE, -- 원본 파일 절대 경로
    file_name VARCHAR(256) NOT NULL,         -- 파일 이름 (확장자 포함)
    file_size INTEGER NOT NULL,              -- 바이트 단위 파일 크기
    file_mtime FLOAT NOT NULL,               -- 파일 최종 수정 타임스탬프
    mime_type VARCHAR(50) NOT NULL,          -- MIME 타입 (image/jpeg, image/x-sony-arw 등)
    is_favorite BOOLEAN DEFAULT 0 NOT NULL,  -- 즐겨찾기 플래그 (인덱스)
    is_offline BOOLEAN DEFAULT 0 NOT NULL,   -- 외장 드라이브 분리 등 오프라인 상태 (인덱스)
    created_at DATETIME NOT NULL,            -- 레코드 생성 일시 (UTC)
    updated_at DATETIME NOT NULL             -- 레코드 수정 일시 (UTC)
);

CREATE INDEX idx_images_parent_dir ON images(parent_dir);
CREATE INDEX idx_images_is_favorite ON images(is_favorite);
CREATE INDEX idx_images_is_offline ON images(is_offline);
```

#### 2) `image_metadata` 테이블 (EXIF 촬영 메타데이터)
```sql
CREATE TABLE image_metadata (
    image_id VARCHAR(64) PRIMARY KEY,        -- FK -> images.id (ON DELETE CASCADE)
    width INTEGER,                           -- 이미지 가로 해상도
    height INTEGER,                          -- 이미지 세로 해상도
    color_space VARCHAR(30) DEFAULT 'sRGB',  -- 색공간 (sRGB, Adobe RGB 등)
    camera_make VARCHAR(100),                -- 카메라 제조사 (예: SONY)
    camera_model VARCHAR(100),               -- 카메라 모델 (예: ILCE-7RM5, 인덱스)
    lens_model VARCHAR(100),                 -- 렌즈 모델 (예: FE 24-70mm F2.8 GM II, 인덱스)
    f_number FLOAT,                          -- 조리개 수치 (F-값, 인덱스)
    focal_length FLOAT,                      -- 물리적 초점거리 (mm, 인덱스)
    focal_length_35mm FLOAT,                 -- 35mm 환산 초점거리 (mm)
    crop_factor FLOAT,                       -- 센서 크롭 팩터
    sensor_format VARCHAR(50),               -- 센서 규격 (Full Frame, APS-C)
    shutter_speed VARCHAR(30),               -- 셔터스피드 (예: "1/500")
    iso INTEGER,                             -- ISO 감도 (인덱스)
    capture_date DATETIME,                   -- 실제 촬영 일시 (인덱스)
    FOREIGN KEY(image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE INDEX idx_meta_camera ON image_metadata(camera_model);
CREATE INDEX idx_meta_lens ON image_metadata(lens_model);
CREATE INDEX idx_meta_f_number ON image_metadata(f_number);
CREATE INDEX idx_meta_focal_length ON image_metadata(focal_length);
CREATE INDEX idx_meta_iso ON image_metadata(iso);
CREATE INDEX idx_meta_capture_date ON image_metadata(capture_date);
```

#### 3) `ai_analysis` 테이블 (AI 캡션, 태그 및 비평)
```sql
CREATE TABLE ai_analysis (
    image_id VARCHAR(64) PRIMARY KEY,        -- FK -> images.id (ON DELETE CASCADE)
    caption TEXT,                            -- Gemma 4 생성 상세 설명
    tags TEXT,                               -- JSON 문자열 배열 ('["street", "night"]')
    aesthetic_tags TEXT,                     -- 전문 미적/스타일 태그 JSON 배열
    is_user_edited BOOLEAN DEFAULT 0,        -- 사용자가 캡션/태그를 수동 편집했는지 여부
    critique TEXT,                           -- UniPercept 8B 심층 에디토리얼 비평 전문
    critique_score FLOAT,                    -- 비평 종합 점수 (0.0 ~ 10.0)
    critique_updated_at DATETIME,            -- 비평 최종 갱신 일시
    FOREIGN KEY(image_id) REFERENCES images(id) ON DELETE CASCADE
);
```

#### 4) `indexed_folders` 테이블 (등록된 로컬 폴더)
```sql
CREATE TABLE indexed_folders (
    path VARCHAR(1024) PRIMARY KEY,          -- 인덱싱 대상 로컬 폴더 경로
    created_at DATETIME NOT NULL             -- 등록 일시
);
```

#### 5) `smart_albums` 테이블 (신규 기능: 검색 프리셋)
```sql
CREATE TABLE smart_albums (
    id VARCHAR(64) PRIMARY KEY,              -- UUID v4
    name VARCHAR(100) NOT NULL,              -- 앨범 명칭 (예: "야간 85mm F1.4 인물")
    query_text TEXT,                         -- 자연어 검색 조건 (옵션)
    filters TEXT,                            -- JSON 직렬화된 SearchFilter 규격
    created_at DATETIME NOT NULL             -- 생성 일시
);
```

##### `filters` 필드 JSON 스키마 규격
```json
{
  "is_favorite": true,
  "camera_model": "ILCE-7RM5",
  "lens_model": "FE 85mm F1.4 GM",
  "f_number_min": 1.4,
  "f_number_max": 1.8,
  "iso_min": 800,
  "iso_max": 6400,
  "focal_length_min": 85.0,
  "focal_length_max": 85.0,
  "date_from": "2024-01-01T00:00:00Z",
  "date_to": "2024-12-31T23:59:59Z"
}
```

### 1.2. ChromaDB 컬렉션 (`photo_embeddings`)
* **메트릭:** Cosine Similarity (`hnsw:space = "cosine"`)
* **ID:** `images.id` (SHA-256)
* **임베딩 차원:** 768차원 (SigLIP 2 ViT-B/16)
* **메타데이터 저장 항목:** `{ "capture_date": str, "iso": int, "camera_model": str, "lens_model": str }`

---

## ⚡ 2. 지능형 2단계 파이프라인 및 런타임 제약사항

대용량 라이브러리 구동 시 성능과 Apple Silicon 통합 메모리를 최적화하기 위해 파이프라인을 엄격히 2단계로 분리합니다.

| 단계 | 실행 트리거 | 실행 엔진 | 작업 내용 및 메모리 정책 | 캐싱 위치 |
| :--- | :--- | :--- | :--- | :--- |
| **1단계: 인덱싱 (즉시/자동)** | 폴더 연동 또는 신규 사진 감지 | CPU 멀티프로세스 + SigLIP 2 (PyTorch MPS) | SHA-256 해싱, EXIF 추출, 360px sRGB JPEG 썸네일 생성, 시각 임베딩 추출 | Thumb Cache 디렉토리, SQLite, ChromaDB |
| **2단계: 심층 분석 (온디맨드)** | 상세 뷰어 열람 또는 사용자의 [AI 비평 요청] | Gemma 4 12B-it (Apple MLX)<br>+ UniPercept 8B (PyTorch MPS) | 캡션/미적태그 생성 및 전문 에디토리얼 비평 생성<br>• **Gemma 4**: 60초 Keep-alive 버퍼 유지<br>• **UniPercept**: 28GB 점유 방지 위해 추론 직후 즉시 언로드 | SQLite `ai_analysis.critique`, `caption`에 영구 보존 |

---

## 🌐 3. REST API 계약 명세 (실제 백엔드 규격)

### 3.1. 사진 및 미디어 API (`/api/photos`)
* `GET /api/photos`
  - **Query:** `limit: int = 50`, `offset: int = 0`, `parent_dir: Optional[str] = None`
  - **Response 200:** `PhotoListResponse[]` (평탄한 배열 반환)
    ```json
    [
      {
        "id": "sha256...",
        "file_name": "DSC01234.ARW",
        "file_path": "/Users/.../DSC01234.ARW",
        "is_favorite": false,
        "capture_date": "2024-10-01T15:30:00",
        "camera_model": "ILCE-7RM5",
        "width": 9504,
        "height": 6336
      }
    ]
    ```
* `GET /api/photos/{id}`
  - **Response 200:** `PhotoDetailResponse` (`metadata` 및 `ai_analysis` 중첩 객체 포함)
  - **Response 404:** `{ "detail": "Photo not found" }`
* `POST /api/photos/{id}/favorite`
  - **Response 200:** `{ "id": "sha256...", "is_favorite": true }`
* `PATCH /api/photos/{id}/metadata`
  - **Request:** `{ "caption": "수정된 설명", "tags": ["landscape", "sunset"] }`
  - **Response 200:** `{ "status": "success", "id": "...", "ai_analysis": AIAnalysisSchema }`
* `GET /api/photos/{id}/thumbnail`
  - **Response 200:** 사전 생성된 360px sRGB JPEG 이미지 스트리밍 (`image/jpeg`)
* `GET /api/photos/{id}/original`
  - **Response 200:** 원본 sRGB 스트리밍 (RAW인 경우 `MAX_CONCURRENT_DECODES=3` 세마포어 적용 인메모리 디코딩)
* `POST /api/photos/export`
  - **Request:** `{ "photo_ids": string[], "destination_folder": string }`
  - **Response 200:** SSE 스트리밍 (파일 복사 진행률 이벤트 전송)

### 3.2. 검색 및 큐레이션 API (`/api/search`)
* `POST /api/search`
  - **Request:**
    ```json
    {
      "query": "가을 단풍이 물든 숲길",
      "filters": {
        "is_favorite": null,
        "camera_model": "ILCE-7RM5",
        "lens_model": null,
        "iso_min": 100,
        "iso_max": 800,
        "f_number_min": 1.4,
        "f_number_max": 2.8,
        "focal_length_min": null,
        "focal_length_max": null,
        "date_from": "2024-09-01T00:00:00Z",
        "date_to": "2024-11-30T23:59:59Z"
      },
      "limit": 50,
      "offset": 0
    }
    ```
  - **Response 200:** `PhotoListResponse[]` (코사인 유사도 및 EXIF 필터 결합 랭킹 순)
* `POST /api/search/similar`
  - **Request:** `{ "photo_id": "sha256...", "filters": null, "limit": 50, "offset": 0 }`
  - **Response 200:** `PhotoListResponse[]` (톤앤매너 K-NN 유사 컷 반환)

### 3.3. 비평 및 요약 API (`/api/chat`)
* `POST /api/chat/critique`
  - **Request:** `{ "photo_id": "sha256...", "engine": "unipercept" }`
  - **Response 200:** `{ "critique": "...", "critique_updated_at": "...", "engine_used": "unipercept", "status": "completed" }`
* `GET /api/chat/critique/status/{photo_id}`
  - **설명:** 백그라운드 비평 생성 진행 상태 조회 (JSON Polling)
  - **Response 200:** `{ "photo_id": "...", "step": 2, "total_steps": 3, "message": "심층 비평 추론 중...", "progress": 66, "status": "processing" }`
* `POST /api/chat/critique/cancel/{photo_id}`
  - **Response 200:** `{ "photo_id": "...", "status": "cancelled", "message": "Critique generation cancelled" }`
* `GET /api/chat/critiques`
  - **Response 200:** `CritiqueItemResponse[]` (생성된 모든 비평 목록)
* `POST /api/chat/critique-summary`
  - **Request:** `{ "photo_ids": ["sha256...", ...] }`
  - **Response 200:** `{ "summary": "선택한 사진들의 AI 종합 총평 리포트...", "total_critiques_analyzed": 5, "created_at": "..." }`
* *(참고: 비평 전문의 PDF 및 Markdown 저장은 프론트엔드 `CritiqueDocumentModal`에서 jsPDF 및 Blob을 통해 100% 클라이언트 사이드로 생성됩니다).*

### 3.4. 스마트 앨범 API (`/api/smart-albums`)
* `GET /api/smart-albums` : 저장된 스마트 앨범 목록 반환 (`200 OK: SmartAlbum[]`)
* `POST /api/smart-albums` : 신규 검색 프리셋 저장 (`201 Created: SmartAlbum`)
  - **Request:** `{ "name": "야간 인물 85mm", "query_text": "인물 포트레이트", "filters": "{ \"f_number_min\": 1.4, ... }" }`
* `DELETE /api/smart-albums/{id}` : 스마트 앨범 삭제 (`200 OK: { "deleted": true }`)

### 3.5. 통계 및 시스템 관리 API
* `GET /api/analytics/stats` : 카메라/렌즈별 점유율, 화각 분포, 조리개/ISO 히스토그램 데이터 반환
* `GET /api/system/models/status` : AI 모델별 다운로드/설치 상태 반환
* `POST /api/system/models/download` : 특정 모델 다운로드 트리거

---

## 🛡️ 4. 예외 처리 및 엣지 케이스 정책 (Edge Cases & Fallbacks)

### 4.1. 비파괴적 스마트 오프라인 관리 (Ghost Photos)
1. **외장 드라이브 연결 해제 감지:**
   - 디스크 스캔 및 파일 접근 시 `os.path.exists(file_path) == False` 감지.
   - 기존의 자동 영구 삭제(`cleanup_zombie_records`)를 방지하고 `images.is_offline = True`로 플래그 갱신.
   - UI는 캐시된 360px 썸네일과 메타데이터를 유지하되 회색조 필터 및 **`[Offline]`** 배지를 표시.
2. **라이브러리 정리(Library Prune) 분리:**
   - 영구 삭제는 사용자가 '유실 사진 정리'를 명시적으로 실행할 때만 확인 팝업을 거쳐 삭제 처리.

### 4.2. 모델 오프라인 & 미다운로드 Graceful Fallback
* SigLIP 2 모델 가중치가 없을 때: 자연어 검색 요청 시 즉각적인 500 에러 대신 HTTP 503 반환 및 파일명/EXIF/날짜 기반 키워드 검색으로 자동 폴백.
* 백그라운드 다운로더(`/api/system/models/status`)에서 진행률을 100% 모니터링 가능하도록 보장.

### 4.3. RAW 디코딩 손상 이미지 대응
* 손상되었거나 지원되지 않는 RAW 파일 접근 시 `rawpy.LibRawFileUnsupportedError` 등을 트랩.
* 내장 EXIF 썸네일 추출로 1차 폴백, 실패 시 플레이스홀더 아이콘 및 에러 배지 표시.

### 4.4. RAW 동시 디코딩 세마포어 및 메모리 백프레셔 제어
* 고해상도 RAW 파일 다중 요청 시 `MAX_CONCURRENT_DECODES = 3` 비동기 세마포어로 동시 실행 수를 제한.
* 대기 큐 초과 시 sRGB 썸네일 캐시를 임시 대체 반환하여 시스템 OOM(Out of Memory)을 원천 차단.
