# [Architecture] 01. Indexing Pipeline, Storage & RAW Media

---

## 🏛️ 1. 1단계 인덱싱(2-Pass 점진적 파이프라인) 및 미디어 서빙 흐름도

```mermaid
flowchart LR
    Folder["로컬 사진 폴더\n(JPEG / ARW / CR3 / NEF)"] --> Pass1["Pass 1: Fast Preview [To-Be]\n(Hash ➔ Relocation 판정 ➔ 360px 썸네일 ➔ EXIF)"]
    Pass1 --> ThumbCache[("Thumbnail Cache\n(360px sRGB JPEG)")]
    Pass1 -->|즉시 커밋 (갤러리/EXIF 즉시 오픈)| SQLite[("SQLite WAL\nimages, image_metadata, ai_analysis")]
    
    SQLite -->|미분석 큐 조회| Pass2["Pass 2: AI Enrichment\n(SigLIP 2 임베딩/제로샷 + Gemma 4 캡션/태그)"]
    Pass2 --> TxMgr["CompensatingTransactionManager"]
    TxMgr -->|1. upsert| Chroma[("ChromaDB\nphoto_embeddings")]
    TxMgr -->|2. commit (실패시 1 롤백)| SQLite
```

---

## 🏗️ 2. 도메인 파일 트리 및 단일 책임 (SRP)

```text
backend/app/
├── api/
│   ├── folders.py                     # [수정대상] 인덱싱 폴더 목록 조회(GET), 삭제(DELETE) 및 오프라인 일괄 정리(POST /prune-offline)
│   ├── indexing.py                    # [기존] 인덱싱 제어(/api/index/start, sync, pause, resume, cancel, status) 라우터
│   └── photos.py                      # [기존] 사진 목록/상세/썸네일/원본 스트리밍(MAX_CONCURRENT_DECODES=3)/재분석/내보내기
├── services/
│   ├── indexing_service.py            # [수정대상] 2-Pass 스케줄러, SHA-256 Relocation 재연결 및 스마트 오프라인 상태 마킹
│   ├── indexing_state.py              # [수정대상] 인덱싱 실시간 진행률 및 현재 패스(fast_preview / ai_enrichment) 상태 객체
│   ├── pipeline.py                    # [수정대상] Pass 1(FastMetadataPipeline) 및 Pass 2(AIEnrichmentPipeline) 단계 분리
│   ├── taxonomy.py                    # [기존] SigLIP 2 제로샷 시각 태깅용 한국어 시각 개념 택소노미 사전
│   ├── ai_parser.py                   # [기존] Gemma 4 캡션/태그/미학태그 출력 파서
│   └── photo.py                       # [기존] SHA-256 계산, 360px 썸네일 생성/캐싱 및 RAW 인메모리 JPEG 변환
├── repositories/
│   ├── photo_repository.py            # [수정대상] SQLite CRUD, SHA-256 경로 Relocation 및 오프라인 마킹 캡슐화
│   ├── vector_repository.py           # [기존] ChromaDB photo_embeddings upsert/delete/query
│   └── atomic_transaction.py          # [기존] ChromaDB <-> SQLite 원자적 보상 트랜잭션 매니저
└── utils/image.py                     # [기존] rawpy 인메모리 디코딩, 35mm 환산 화각 및 EXIF 파싱

src/
├── components/
│   ├── ActionBar.tsx                  # [기존] 다중 선택 사진 일괄 내보내기(SSE 진행률) 플로팅 액션바
│   └── sidebar/
│       ├── FolderList.tsx             # [기존] 등록된 로컬 폴더 리스트 및 삭제 제어
│       └── IndexingProgressCard.tsx   # [수정대상] 2-Pass(프리뷰 스캔 / AI 분석) 진행률·일시정지·취소 위젯
└── hooks/useIndexingStatus.ts         # [기존] 인덱싱 진행 상태 Polling 커스텀 훅
```

---

## 🤝 3. 타 도메인 참조 및 경계 계약 (Cross-Domain Dependencies)

* **참조하는 외부 도메인 (Inbound/Read)**:
  - `00_core_foundation`: `ai_factory.py`(`get_siglip_adapter`, `get_gemma_adapter`), `GPU_LOCK`, `DATABASE_URL` 및 `THUMBNAIL_CACHE_DIR` 설정 참조.
* **외부 도메인에 노출하는 계약 (Outbound/Expose)**:
  - `02_search_curation`, `03_ai_critique`, `04_studio_ui_analytics` 도메인이 사용할 수 있도록 `PhotoRepository`(SQLite CRUD/필터/통계) 및 `VectorRepository`(ChromaDB 유사도 질의) 인터페이스를 제공합니다.

---

## 🔒 4. 도메인 아키텍처 제약 규칙

1. **원자적 정합성 보장**: AI 분석(Pass 2) 저장 시 반드시 `CompensatingTransactionManager`를 사용하여 ChromaDB `upsert` 후 SQLite `commit`을 수행하며, SQLite 예외 발생 시 ChromaDB 벡터를 즉시 삭제(`vector_repo.delete`)합니다.
2. **SHA-256 Relocation 우선 실행 규칙**: 폴더 동기화 시 실종 레코드 정리(`mark_offline_records`)보다 신규/변경 파일 스캔 및 SHA-256 해시 대조를 먼저 수행하여, 이름 변경이나 폴더 이동된 파일이 기존 레코드(즐겨찾기, 수동 편집 태그, AI 비평)를 잃지 않고 경로만 In-place 재연결되도록 보장합니다.
3. **RAW 디코딩 메모리 보호**: `/api/photos/{id}/original`은 RAW 파일 요청 시 디스크에 임시 파일을 생성하지 않고 `api/photos.py`의 `MAX_CONCURRENT_DECODES = 3` 세마포어(`get_decode_semaphore()`) 내부에서 `asyncio.to_thread()`로 인메모리 디코딩 스트리밍합니다.
