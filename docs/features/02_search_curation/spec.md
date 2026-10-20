# [Spec & Contracts] 02. Hybrid Search, K-NN Curation & Smart Albums

---

## 💾 1. 데이터 모델 및 하이브리드 랭킹 수식 명세

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

### 1.2. `[To-Be]` 코사인 거리 임계값 절삭 및 RRF 하이브리드 랭킹 수식
1. **SQLite 다중 텍스트 후보 추출 (`PhotoRepository.search_by_text`)**:
   - 검색 대상: `AIAnalysis.caption`, `AIAnalysis.tags`, **`AIAnalysis.aesthetic_tags`** (`ILIKE '%query%'`)
2. **ChromaDB 코사인 거리 임계값 절삭 (`VectorRepository.query_similar_by_embedding`)**:
   - `collection.query(..., include=["distances"])`로 코사인 거리 $d = 1 - \cos(\theta)$를 조회하여 **절대 임계값($d \le 0.88$)**을 초과하는 무관한 이미지는 결과에서 즉시 배제합니다.
3. **Reciprocal Rank Fusion (RRF, $k=60$) 정렬**:
   $$\text{RRF\_Score}(id) = \frac{1.2}{60 + \text{rank}_{\text{text}}(id)} + \frac{1.0}{60 + \text{rank}_{\text{vec}}(id)}$$
   - 텍스트 일치와 시각 임베딩 유사도를 동시에 만족하는 사진이 최상단에 배치됩니다.

---

## 🌐 2. 백엔드 REST API 계약

### 2.1. 하이브리드 검색 및 유사 사진 API (`/api/search`)
* `POST /api/search`
  - **Request Body:**
    ```json
    {
      "query": "비 내리는 밤거리 시네마틱",
      "filters": {
        "is_favorite": true,
        "camera_model": "ILCE-7RM5",
        "lens_model": "FE 85mm F1.4 GM",
        "iso_min": 100, "iso_max": 6400,
        "f_number_min": 1.4, "f_number_max": 2.8,
        "focal_length_min": 35.0, "focal_length_max": 85.0,
        "use_35mm_equivalent": true,
        "min_overall_score": 80.0,
        "min_iaa_score": 85.0,
        "date_from": "2024-01-01T00:00:00Z", "date_to": "2024-12-31T23:59:59Z"
      },
      "limit": 50, "offset": 0
    }
    ```
  - **35mm 환산 화각 필터링 규칙 (`[To-Be]`)**: `use_35mm_equivalent = true`(기본값)일 때 `COALESCE(image_metadata.focal_length_35mm, image_metadata.focal_length)`를 기준으로 화각 범위를 필터링하여 크롭(APS-C) 바디와 풀프레임 바디 사진을 동일한 시야각 기준으로 통합 검색합니다.
  - **Response 200:** `PhotoListResponse[]`
* `POST /api/search/similar` `[As-Is]`
  - **Request Body:** `{ "photo_id": "sha256...", "filters": null, "limit": 50, "offset": 0 }`
  - **Response 200:** `PhotoListResponse[]` (자기 자신을 제외한 코사인 유사도 상위 결과)

### 2.2. 스마트 앨범 API (`/api/smart-albums`) `[To-Be 신규]`
* `GET /api/smart-albums` ➔ `200 OK: SmartAlbumResponse[]` (생성일 역순 정렬)
* `POST /api/smart-albums`
  - **Request:** `{ "name": "85mm 미학 85점+ 인물", "query_text": "인물", "filters": SearchFilter }`
  - **Response 201:** `SmartAlbumResponse` / **422:** 이름이 공백/100자 초과이거나 검색어·필터가 모두 비어 있을 때
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
  use_35mm_equivalent?: boolean; // [To-Be] 기본값 true (35mm 환산 화각 기준 필터링)
  min_overall_score?: number;    // [To-Be] AI 종합 평점 하한 (0~100)
  min_iaa_score?: number;        // [To-Be] AI 미학(IAA) 평점 하한 (0~100)
  date_from?: string;
  date_to?: string;
}

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

1. **프리셋 활성화 동기화**: 사이드바에서 스마트 앨범 클릭 시 `searchQuery`와 `searchFilters`가 즉시 해당 프리셋 값으로 교체되며 갤러리가 재검색됩니다. 이후 검색어나 필터를 수동 변경하면 `activeSmartAlbumId` 하이라이트가 자동 해제됩니다.
2. **빈 조건 저장 방지**: 검색어(`query_text`)와 활성화된 `filters`가 모두 비어 있는 상태에서는 `[+ 스마트 앨범 저장]` 버튼이 비활성화(Disabled)됩니다.
