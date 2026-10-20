# [Decisions (ADR)] 02. Hybrid Search, K-NN Curation & Smart Albums

---

### [ADR-01] SQLite 텍스트/캡션 매칭 + ChromaDB 벡터 유사도 + EXIF 교집합 하이브리드 파이프라인
- **배경**: ChromaDB 단독 벡터 검색만으로는 정확한 태그/키워드 매칭이나 복잡한 날짜 범위 및 다중 EXIF 조건 처리에 한계가 있음.
- **결정**: `SearchService`에서 (1) SQLite `AIAnalysis`의 `caption`/`tags`/`aesthetic_tags` 텍스트 매칭(`ILIKE`) 후보와 (2) SigLIP 2 텍스트 임베딩 기반 ChromaDB 코사인 유사도 상위 후보를 병합한 뒤, (3) SQLite 인덱스를 활용한 EXIF 및 비평 점수 조건으로 최종 교집합 필터링을 수행함.
- **영향**: 키워드 정확도와 시각적 의미 유사도를 동시에 만족하면서 복합 EXIF 필터 응답 속도를 보장함.

### [ADR-02] 코사인 거리 임계값 절삭(`d <= 0.88`) 및 RRF($k=60$) 랭킹 융합
- **배경**: ChromaDB `collection.query(n_results=N)`는 거리 점수를 검사하지 않으면 라이브러리에 없는 주제를 검색해도 무조건 $N$개의 무관한 사진을 반환하며, 텍스트 매칭과 벡터 매칭을 단순 리스트 결합하면 두 영역 모두에서 우수한 사진이 상위권에서 밀려남.
- **결정**: ChromaDB 질의 시 `include=["distances"]`로 코사인 거리 $d > 0.88$인 후보를 절삭하고, 텍스트 순위와 벡터 순위를 Reciprocal Rank Fusion($\text{Score} = \frac{1.2}{60 + r_t} + \frac{1.0}{60 + r_v}$)으로 통합 정렬함.
- **영향**: 무관한 거짓 양성(False Positive) 결과를 차단하고 다중 모달(텍스트 캡션 + 시각 임베딩) 일치 사진의 최상단 노출 보장.

### [ADR-03] `COALESCE(focal_length_35mm, focal_length)` 기반 통합 화각 필터링
- **배경**: 풀프레임과 크롭 바디(APS-C, MFT)를 함께 사용하는 사진작가가 화각(예: 35mm, 85mm)으로 필터링할 때 물리 초점거리(`focal_length`)만 비교하면 크롭 바디 사진(예: 23mm, 56mm)이 누락됨.
- **결정**: `SearchFilter.use_35mm_equivalent`(기본값 `True`) 활성화 시 `COALESCE(focal_length_35mm, focal_length)`로 비교하여 센서 포맷에 구애받지 않는 실질 시야각 기준 검색을 기본 제공함.
- **영향**: 통계 대시보드(`04_studio_ui_analytics`)의 35mm 환산 화각 차트와 검색 필터 간 완벽한 데이터 일관성 확보.
