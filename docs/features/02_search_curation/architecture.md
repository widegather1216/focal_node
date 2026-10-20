# [Architecture] 02. Hybrid Search, K-NN Curation & Smart Albums

---

## 🏛️ 1. RRF 하이브리드 검색 및 스마트 앨범 흐름도

```mermaid
flowchart TD
    UI_Filter["SearchFilterMenu / Sidebar SmartAlbums / Analytics Drill-down\n(query + EXIF & Score SearchFilters)"] --> Store["useAppStore.ts\n(searchQuery, searchFilters, activeSmartAlbumId)"]
    Store --> Api["src/services/api.ts\n(/api/search, /api/smart-albums)"]
    
    Api --> SearchRouter["backend/app/api/search.py"]
    Api --> AlbumRouter["backend/app/api/smart_albums.py [신규]"]
    
    SearchRouter --> SearchSvc["SearchService\n(RRF k=60 랭킹 결합)"]
    AlbumRouter --> PhotoRepo["PhotoRepository\n(repositories/photo_repository.py)"]
    
    SearchSvc -->|1. 텍스트 임베딩 + 거리 임계값(d<=0.88) 절삭| VectorRepo["VectorRepository (ChromaDB)"]
    SearchSvc -->|2. caption + tags + aesthetic_tags 매칭| PhotoRepo
    SearchSvc -->|3. EXIF(35mm 환산) & 비평 점수 교집합 필터링| PhotoRepo
```

---

## 🏗️ 2. 도메인 파일 트리 및 단일 책임 (SRP)

```text
backend/app/
├── models.py                          # [수정대상] SmartAlbum ORM 모델 추가
├── schemas.py                         # [수정대상] SearchRequest, SearchFilter(use_35mm_equivalent, min_*_score), SmartAlbumSchema
├── api/
│   ├── search.py                      # [기존] POST /api/search, POST /api/search/similar
│   └── smart_albums.py                # [신규] GET/POST/DELETE /api/smart-albums 라우터
├── services/search_service.py         # [수정대상] RRF(k=60) 하이브리드 랭킹 결합 및 SigLIP 예외 시 SQLite 폴백
└── repositories/
    ├── vector_repository.py           # [수정대상] query_similar_by_embedding에 코사인 거리 임계값(max_distance) 절삭 추가
    └── photo_repository.py            # [수정대상] aesthetic_tags 검색, 35mm 환산 화각/비평 점수 필터 및 SmartAlbum CRUD

src/
├── types/photo.ts                     # [수정대상] SearchFilters(use_35mm_equivalent, min_*_score), SmartAlbum 타입 정의
├── services/api.ts                    # [수정대상] searchPhotos, getSmartAlbums, createSmartAlbum, deleteSmartAlbum
├── store/useAppStore.ts               # [수정대상] 검색 필터 상태, 차트 드릴다운 및 스마트 앨범 원클릭 적용 액션
├── hooks/useDebounce.ts               # [기존] 검색어 입력 500ms 디바운스 훅
└── components/
    ├── SearchFilterMenu.tsx           # [수정대상] 기종/렌즈/ISO/조리개/35mm화각/점수 필터 및 스마트 앨범 저장 트리거
    ├── Sidebar.tsx                    # [수정대상] Smart Albums 섹션 리스트 및 삭제 버튼
    └── filter/FilterRangeInput.tsx    # [기존] 최소/최대 수치 범위 입력 서브컴포넌트
```

---

## 🤝 3. 타 도메인 참조 및 경계 계약 (Cross-Domain Dependencies)

* **참조하는 외부 도메인 (Inbound/Read)**:
  - `00_core_foundation`: `ai_factory.get_siglip_adapter()`를 통해 텍스트 질의어 768차원 임베딩 추출.
  - `01_indexing_storage`: `PhotoRepository`(`search_by_text`, `filter_and_paginate`) 및 `VectorRepository`(`query_similar_by_embedding`, `get_embedding_by_id`) 참조.
  - `03_ai_critique`: `ai_analysis` 테이블에 정규화된 `overall_score`, `iaa_score`, `iqa_score`, `ista_score` 컬럼을 참조하여 최소 평점 필터링 수행.
* **외부 도메인에 노출하는 계약 (Outbound/Expose)**:
  - `04_studio_ui_analytics`: `useAppStore`의 `searchQuery`, `searchFilters`, `applyChartFilter()`를 통해 `PhotoGallery.tsx` 뷰포트 갱신 및 통계 차트 클릭 드릴다운을 지원합니다.

---

## 🔒 4. 도메인 아키텍처 제약 규칙

1. **검색 상태 일원화**: `SearchFilterMenu`, `Sidebar`(스마트 앨범), `AnalyticsView`(차트 클릭 드릴다운)에서의 모든 필터 조작은 반드시 `useAppStore`의 `searchQuery` 및 `searchFilters` 상태를 전이시켜 갤러리 쿼리가 단일 경로로 갱신되도록 합니다.
2. **코사인 거리 컷오프 및 RRF 랭킹 결합 (`SearchService`)**:
   - ChromaDB 벡터 질의 시 무관한 사진이 하위 순위로 딸려 오는 현상을 막기 위해 코사인 거리 임계값(`d <= 0.88`) 및 최고 유사도 대비 급락 구간 필터링을 적용합니다.
   - SQLite(`caption`, `tags`, `aesthetic_tags`) 순위 $r_{\text{text}}$와 ChromaDB 벡터 순위 $r_{\text{vec}}$를 **RRF 수식**($\text{Score}(p) = \frac{w_t}{60 + r_{\text{text}}(p)} + \frac{w_v}{60 + r_{\text{vec}}(p)}$)으로 통합 정렬한 뒤 EXIF/점수 교집합을 적용합니다.
