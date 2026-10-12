# [Architecture Blueprint] 올인원 로컬 포토 스튜디오

본 문서는 **Focal Node: Core Photo Studio**의 시스템 구조, 실제 데이터 통신 경로, 컴포넌트 계층 분리 및 Apple Silicon 하드웨어 제약사항을 정의합니다.

---

## 🏛️ 1. 시스템 아키텍처 및 데이터 흐름

```mermaid
flowchart TD
    subgraph DesktopClient["데스크탑 클라이언트 (Tauri v2 + React 19)"]
        UI["Studio Gallery / Viewer / Analytics / Critique UI (src/components)"]
        Store["통합 전역 상태 (src/store/useAppStore.ts)"]
        ApiClient["HTTP API Client (src/services/api.ts)"]
        TauriHost["Tauri Rust Host (src-tauri/src/lib.rs)"]
        
        UI --> Store
        UI --> ApiClient
        Store --> ApiClient
        UI -.->|IPC: Finder 열기| TauriHost
        TauriHost -.->|포트 1회 주입: get_api_port| ApiClient
    end

    subgraph BackendSidecar["백엔드 사이드카 (FastAPI 3-Tier 아키텍처)"]
        direction TB
        
        subgraph APILayer["API Routers (backend/app/api)"]
            RouterPhotos["/photos (목록/상세/스트리밍/즐겨찾기)"]
            RouterSearch["/search (하이브리드/유사검색)"]
            RouterChat["/chat (비평/상태조회/요약)"]
            RouterFolders["/folders (폴더 등록/조회/삭제)"]
            RouterIndex["/indexing (인덱싱 제어/상태)"]
            RouterAnalytics["/analytics (장비 통계)"]
            RouterSystem["/system (AI 모델 다운로드 - main.py)"]
        end

        subgraph ServiceLayer["Service Layer (비즈니스 로직)"]
            IndexSvc["IndexingService & indexing_state.py (스캔/해싱/추출)"]
            SearchSvc["SearchService (하이브리드 가중치 & K-NN)"]
            ChatSvc["ChatService & critique_status.py (비평 파이프라인)"]
            PhotoSvc["PhotoService (썸네일/캐시 비즈니스)"]
            ModelDownloader["ModelDownloader (HF 백그라운드 설치)"]
        end

        subgraph RepoLayer["Repository, Adapter & Synchronization"]
            PhotoRepo["PhotoRepository (SQLite WAL 메타데이터 CRUD)"]
            VectorRepo["VectorRepository (ChromaDB 코사인 유사도)"]
            TxManager["CompensatingTransactionManager (원자적 보상 롤백)"]
            ImageDecoder["ImageDecoder (rawpy + 세마포어=3 메모리 디코딩)"]
            GPULock["GPU_LOCK (threading.RLock: Metal 컨텍스트 동기화)"]
            AIEngines["Apple Silicon AI Engines\n• MLX: Gemma 4 (60s Keep-alive)\n• PyTorch MPS: SigLIP 2, UniPercept 8B (즉시 언로드)"]
        end

        APILayer --> ServiceLayer
        ServiceLayer --> RepoLayer
        RepoLayer --> GPULock
    end

    subgraph Storage["로컬 스토리지 & 하드웨어 (100% On-Device)"]
        SQLiteDB[("SQLite WAL (~/.config/focal_node/photos.db)")]
        ChromaStore[("ChromaDB (~/.config/focal_node/chroma)")]
        ThumbCache[("Thumbnail Cache (360px sRGB JPEG)")]
        AppleSilicon["Apple Silicon Unified Memory (M-Series GPU / NPU)"]
    end

    ApiClient -->|Direct HTTP (포트 동적 바인딩)| APILayer
    PhotoRepo --> SQLiteDB
    VectorRepo --> ChromaStore
    IndexSvc --> ThumbCache
    AIEngines --> AppleSilicon
```

---

## 🏗️ 2. 소스 코드 청사진 및 디렉터리 구조

실제 코드베이스의 파일 배치와 일치하도록 정돈된 청사진입니다.

```text
focal_node/
├── src-tauri/                     # 데스크탑 호스트 (Rust)
│   ├── src/lib.rs                 # 사이드카 기동, [Sidecar] PORT 감지/주입 및 Finder 연동
│   ├── src/main.rs                # 진입점 래퍼
│   └── tauri.conf.json            # 창 설정 및 네이티브 번들링 설정
│
├── src/                           # 프론트엔드 (React 19 + TypeScript + Tailwind)
│   ├── components/
│   │   ├── gallery/               # PhotoGallery, PhotoCard, VirtualScroll
│   │   ├── viewer/                # FullscreenViewer, FullscreenMetadataOverlay
│   │   ├── critique/              # CritiqueView, CritiqueCard, CritiqueDocumentModal
│   │   ├── analytics/             # AnalyticsView, GearDonutCharts, ExifBarCharts
│   │   ├── sidebar/               # Sidebar, FolderList, IndexingProgressCard
│   │   └── common/                # SearchFilterMenu, ModelDownloadModal
│   ├── services/api.ts            # 백엔드 직접 HTTP 통신 전담 클라이언트
│   ├── store/useAppStore.ts       # Zustand 단일 통합 전역 상태
│   ├── hooks/                     # useIndexingStatus, usePhotoDetail, useSearch 등
│   └── types/                     # photo.ts, critique.ts 등 엄격한 타입 정의
│
└── backend/app/                   # 백엔드 사이드카 (FastAPI 3-Tier)
    ├── api/                       # 계층 1: API 라우터 (요청 검증 & 직렬화)
    │   ├── photos.py              # 사진 목록, 스트리밍, EXIF, 즐겨찾기, 파일 내보내기
    │   ├── search.py              # 자연어 하이브리드 검색 및 K-NN 유사 검색
    │   ├── chat.py                # AI 비평 생성, 상태 Polling, 취소, 요약
    │   ├── folders.py             # 등록 폴더 관리
    │   ├── indexing.py            # 인덱싱 시작/동기화/일시정지/상태
    │   └── analytics.py           # 장비 및 촬영 통계
    ├── services/                  # 계층 2: 비즈니스 서비스
    │   ├── indexing_service.py    # 1단계 인덱싱 파이프라인 (스캔/해싱/추출)
    │   ├── indexing_state.py      # 인덱싱 진행 상태 관리
    │   ├── search_service.py      # 하이브리드 가중치 결합 및 K-NN
    │   ├── chat_service.py        # 온디맨드 비평 생성 및 요약
    │   ├── photo.py               # 썸네일 캐시 확인/생성 및 스트리밍 비즈니스
    │   ├── model_downloader.py    # HF 스냅샷 백그라운드 다운로더
    │   ├── mlx_adapters.py        # Gemma 4 MLX 로더 및 60초 Keep-alive 데몬
    │   └── unipercept_adapter.py  # UniPercept 8B PyTorch MPS 어댑터 (즉시 언로드)
    ├── repositories/              # 계층 3: 영속성 및 동기화 어댑터
    │   ├── photo_repository.py    # SQLite CRUD 캡슐화
    │   ├── vector_repository.py   # ChromaDB 임베딩 upsert/query
    │   └── atomic_transaction.py  # CompensatingTransactionManager (원자적 보상 롤백)
    ├── core/ports.py              # AI 모델 및 리포지토리 인터페이스 포트
    ├── utils/image.py             # rawpy 디코딩, EXIF 추출 유틸리티
    ├── models.py                  # SQLAlchemy 모델 (images, image_metadata, ai_analysis 등)
    ├── schemas.py                 # Pydantic 요청/응답 스키마
    └── main.py                    # 동적 포트(0) 바인딩, 모델 다운로더 라우트 및 라이프사이클
```

---

## 🔒 3. 계층 간 의존성 규칙 및 클린 코드 지침

1. **단방향 의존성 엄수:**
   `UI/Components` ➔ `Custom Hooks & Store` ➔ `ApiClient (HTTP)` ➔ `FastAPI Routers` ➔ `Services` ➔ `Repositories`
   * 상위 계층은 하위 계층에만 의존합니다.
   * 프론트엔드는 Tauri Rust Host를 거치지 않고 FastAPI 백엔드로 **직접 비동기 HTTP 요청**을 수행합니다.
2. **Repository 캡슐화 및 DB 직접 쿼리 금지:**
   * API 라우터(`api/folders.py`, `api/indexing.py` 등)에서 SQLAlchemy `db.query()`를 직접 실행하는 패턴을 지양하고, 모든 데이터 접근은 반드시 `PhotoRepository`를 통해 캡슐화합니다.
3. **거대 UI 컴포넌트의 단계적 SRP 모듈화:**
   * 단일 UI 파일 300라인 가이드를 준수하기 위해, `CritiqueDocumentModal.tsx`(1,700+ 라인) 등 대형 컴포넌트는 단일 책임을 가진 서브컴포넌트(`DocumentHeader`, `DocumentSection`, `PdfExporter`)로 단계적 분할을 적용합니다.

---

## ⚡ 4. 엔지니어링 제약사항 및 하드웨어 안전장치

* **Rule 2.1 (FastAPI 동적 포트 할당):** `port=0`으로 OS 유휴 포트를 바인딩하고, stdout에 `[Sidecar] PORT: {port}`를 1회 출력합니다. Tauri는 이를 읽어 프론트엔드에 `get_api_port` 커맨드로 1회 주입합니다.
* **Rule 2.2 (SQLite WAL & 보상 트랜잭션):** 커넥션 수립 시 `PRAGMA journal_mode=WAL;`과 `PRAGMA foreign_keys=ON;`을 강제합니다. ChromaDB upsert 후 SQLite 커밋이 실패할 경우 `CompensatingTransactionManager`가 ChromaDB 임베딩을 즉시 삭제하여 정합성을 보장합니다.
* **Rule 2.3 (RAW 스트리밍 & 디코딩 세마포어):** 원본 뷰어 요청 시 디스크 임시 파일 없이 메모리에서 `rawpy`로 즉시 디코딩하며, 동시 디코딩 세마포어 `MAX_CONCURRENT_DECODES=3`으로 메모리 폭증을 제어합니다.
* **Rule 2.4 (이벤트 루프 논블로킹 & 모델 수명주기):**
  * CPU/IO Bound 작업은 `asyncio.to_thread()`로 이벤트 루프를 보호합니다.
  * **Gemma 4 (12B-it-8bit MLX):** 연속 분석 요청을 위해 인덱싱/비평 완료 후 **60초 Keep-alive 버퍼**를 유지한 후 언로드합니다.
  * **UniPercept 8B (PyTorch MPS):** 14B 하이브리드 구조(약 28~30GB VRAM 점유)로 인해 OOM을 방지하고자 비평 완료 즉시 `finally` 블록에서 **강제 즉시 언로드(`unload_model()`)**를 실행합니다.
  * **GPU_LOCK (Metal Context 직렬화):** PyTorch MPS와 Apple MLX가 동시에 Metal 디바이스 컨텍스트를 호출하여 크래시가 발생하는 것을 방지하기 위해 `GPU_LOCK = threading.RLock()`으로 모델 추론 진입점을 직렬화합니다.
* **Rule 2.5 (환경 격리):** 프로덕션(`IS_PROD`) 환경은 `~/.config/focal_node`, 개발 환경은 `~/.config/focal_node_dev`로 데이터베이스 및 썸네일 캐시 경로를 격리합니다.
