# [Spec & Contracts] 02. Hybrid Search, K-NN Curation & Smart Albums

---

## 💾 1. 데이터 모델 및 스키마 명세

### 1.1. `[To-Be / Migration Required]` `smart_albums` 테이블 (`backend/app/models.py`)
```sql
CREATE TABLE smart_albums (
    id VARCHAR(64) PRIMARY KEY,              -- UUID v4 문자열
    name VARCHAR(100) NOT NULL,              -- 앨범 이름 (1~100자, 공백만 입력 불가)
    query_text TEXT,                         -- 자연어 검색어 (옵션)
    filters TEXT NOT NULL,                   -- JSON 직렬화된 SearchFilter 객체
    created_at DATETIME NOT NULL             -- 생성 일시 (UTC)
);
```

---

## 🌐 2. 백엔드 REST API 계약

### 2.1. 하이브리드 검색 및 유사 사진 API (`/api/search`) `[As-Is 기구현]`
* `POST /api/search`
  - **Request Body:**
    ```json
    {
      "query": "비 내리는 밤거리",
      "filters": {
        "is_favorite": true,
        "camera_model": "ILCE-7RM5",
        "lens_model": "FE 85mm F1.4 GM",
        "iso_min": 100, "iso_max": 6400,
        "f_number_min": 1.4, "f_number_max": 2.8,
        "focal_length_min": 35.0, "focal_length_max": 85.0,
        "date_from": "2024-01-01T00:00:00Z", "date_to": "2024-12-31T23:59:59Z"
      },
      "limit": 50, "offset": 0
    }
    ```
  - **Response 200:** `PhotoListResponse[]`
* `POST /api/search/similar`
  - **Request Body:** `{ "photo_id": "sha256...", "filters": null, "limit": 50, "offset": 0 }`
  - **Response 200:** `PhotoListResponse[]` (자기 자신을 제외한 코사인 유사도 상위 결과)

### 2.2. 스마트 앨범 API (`/api/smart-albums`) `[To-Be 신규]`
* `GET /api/smart-albums` ➔ `200 OK: SmartAlbumResponse[]` (생성일 역순 정렬)
* `POST /api/smart-albums`
  - **Request:** `{ "name": "야간 85mm 인물", "query_text": "밤거리 인물", "filters": SearchFilter }`
  - **Response 201:** `SmartAlbumResponse`
  - **Response 422:** 이름이 공백이거나 100자 초과, 또는 검색어와 필터가 모두 비어 있을 때 반환
* `DELETE /api/smart-albums/{id}` ➔ `200 OK: { "deleted": true, "id": "..." }` / `404 Not Found`

---

## 💻 3. 프론트엔드 타입 및 상태 계약 (`src/types/photo.ts`, `useAppStore.ts`)

```typescript
export interface SearchFilters {
  is_favorite?: boolean;
  camera_model?: string;
  lens_model?: string;
  iso_min?: number;
  iso_max?: number;
  f_number_min?: number;
  f_number_max?: number;
  focal_length_min?: number;
  focal_length_max?: number;
  date_from?: string;
  date_to?: string;
}

// [To-Be] 스마트 앨범 인터페이스
export interface SmartAlbum {
  id: string;
  name: string;
  query_text: string | null;
  filters: SearchFilters;
  created_at: string;
}
```

---

## 🎨 4. UI/UX 상태 전이 및 예외 처리

1. **프리셋 활성화 동기화**: 사이드바에서 스마트 앨범 클릭 시 `searchQuery`와 `searchFilters`가 즉시 해당 프리셋 값으로 교체되며 갤러리가 재검색됩니다. 사용자가 이후 검색어나 필터를 수동 변경하면 `activeSmartAlbumId` 하이라이트가 자동 해제됩니다.
2. **빈 조건 저장 방지**: 검색어(`query_text`)와 활성화된 `filters`가 모두 비어 있는 상태에서는 `[+ 스마트 앨범 저장]` 버튼이 비활성화(Disabled)됩니다.
