# [Decisions (ADR)] 01. Indexing Pipeline, Storage & RAW Media

---

### [ADR-01] SHA-256 기반 Dual-DB 보상 트랜잭션 (Compensating Transaction)
- **배경**: SQLite와 ChromaDB는 이기종 스토리지이므로 단일 2PC(Two-Phase Commit) 트랜잭션을 지원하지 않음.
- **결정**: 파일의 SHA-256 해시를 공통 PK로 사용하고, `CompensatingTransactionManager`에서 ChromaDB `upsert` 후 SQLite `commit` 실패 시 `vector_repo.delete([image_id])`를 호출하여 롤백함.
- **영향**: 인덱싱 강제 종료 시에도 고아 임베딩이나 메타데이터 불일치가 발생하지 않음.

### [ADR-02] 360px sRGB 썸네일 사전 디스크 캐싱
- **배경**: 50MB 이상 고해상도 RAW 파일을 갤러리 스크롤마다 실시간 디코딩하면 심각한 프레임 드랍 발생.
- **결정**: 인덱싱 시점에 가로 360px sRGB JPEG 썸네일을 생성하여 `~/.config/focal_node/thumbnails/{sha256}.jpg`에 캐싱하고 즉시 서빙함.
- **영향**: 수만 장의 RAW 라이브러리에서도 60fps 가상 스크롤 탐색 달성.
