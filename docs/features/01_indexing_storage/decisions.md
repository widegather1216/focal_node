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

### [ADR-03] SHA-256 Content-Addressable 파일 이동 재연결 (`Relocation`)
- **배경**: 사용자가 Finder에서 파일명을 변경하거나 하위 폴더로 이동할 때 구 경로 레코드를 먼저 삭제하거나 단순 해시 중복(`skipped_duplicate_hash`)으로 처리하면, 고비용 AI 비평(`critique`)과 수동 편집 데이터가 소실되거나 새 경로가 영구 누락됨.
- **결정**: 동일 SHA-256 해시(`existing_by_id`) 발견 시 구 경로 파일이 디스크에 없거나 `is_offline == True`이면 파일 이동(`Relocated`)으로 판정하여 경로 메타데이터만 In-place 갱신함.
- **영향**: 불필요한 AI 재추론 비용을 제거하고 파일 정리/이동 후에도 사용자의 큐레이션 및 비평 자산을 100% 보존함.

### [ADR-04] 2-Pass 점진적 인덱싱 (Fast Preview ➔ Background AI Enrichment)
- **배경**: 1단계 인덱싱에서 Gemma 4 VLM 캡션 생성까지 단일 패스로 묶으면, 첫 100장 청크의 AI 추론이 끝날 때까지 수 분간 갤러리에 사진이 한 장도 표시되지 않는 초기 체감 지연이 발생함.
- **결정**: Pass 1에서 고속으로 `SHA-256 + 360px 썸네일 + EXIF`만 먼저 DB에 커밋하여 갤러리 탐색을 즉시 활성화하고, Pass 2에서 백그라운드로 `SigLIP 2 + Gemma 4` 분석을 비동기 보강함.
- **영향**: 폴더 추가 직후 체감 대기 시간을 수 분에서 수 초 이내로 단축함.
