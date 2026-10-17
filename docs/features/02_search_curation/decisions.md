# [Decisions (ADR)] 02. Hybrid Search, K-NN Curation & Smart Albums

---

### [ADR-01] SQLite 텍스트/캡션 매칭 + ChromaDB 벡터 유사도 + EXIF 교집합 하이브리드 파이프라인
- **배경**: ChromaDB 단독 벡터 검색만으로는 정확한 태그/키워드 매칭이나 복잡한 날짜 범위 및 다중 EXIF 조건 처리에 한계가 있음.
- **결정**: `SearchService.execute_hybrid_search`에서 (1) SQLite `AIAnalysis`의 `caption`/`tags` 텍스트 매칭(`ILIKE`) 후보와 (2) SigLIP 2 텍스트 임베딩 기반 ChromaDB 코사인 유사도 상위 후보를 순서대로 병합한 뒤, (3) SQLite 인덱스를 활용한 EXIF 조건(`camera_model`, `lens_model`, `f_number`, `iso`, `focal_length`, `capture_date`)으로 최종 교집합 필터링을 수행하고 랭킹 순서를 유지함.
- **영향**: 키워드 정확도와 시각적 의미 유사도를 동시에 만족하면서 복합 EXIF 필터 응답 속도를 보장함.
