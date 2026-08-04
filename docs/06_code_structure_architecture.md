# 06. Focal Node Code Structure & Architecture

본 문서는 **Focal Node (AI 기반 로컬 프라이버시 사진 검색 앱)**의 전체 애플리케이션 아키텍처와 주요 코드 디렉토리 구조, 그리고 핵심 모듈들의 역할을 정리합니다.

---

## 1. 하이브리드 애플리케이션 아키텍처

Focal Node는 프론트엔드와 백엔드가 완전히 분리되어 OS 프로세스 간 통신을 수행하는 하이브리드 형태(Tauri Sidecar 아키텍처)를 취하고 있습니다.

*   **Tauri (Rust) - 프론트엔드 호스트:**
    *   Vite + React.js 기반의 사용자 인터페이스를 웹뷰(Webview)로 렌더링합니다.
    *   OS의 파일 시스템 직접 접근을 담당하며, Python 백엔드 프로세스를 **Sidecar** 형태로 자식 프로세스로 띄우고 라이프사이클을 함께 관리합니다.
*   **FastAPI (Python) - 백그라운드 인덱싱 및 AI 엔진:**
    *   MLX 가속(Apple Silicon)을 사용하여 대용량 VLM(Vision-Language Model) 모델의 추론을 담당합니다.
    *   인덱싱 큐, 로컬 DB 동기화, 사진 메타데이터 추출 등 무거운 CPU/GPU Bound 작업을 전담하여 UI의 멈춤 현상(Freezing)을 방지합니다.
    *   **3계층 아키텍처 (Router - Service - Repository):** 단일 책임 원칙(SRP)과 높은 유지보수성을 확보하기 위해 API 라우터, 비즈니스 서비스, DB 레포지토리 레이어가 완전히 분리되어 있습니다.

---

## 2. 전체 디렉토리 및 파일 구조

```text
focal_node/
├── src-tauri/               # Tauri(Rust) 백엔드 및 앱 패키징 로직
│   ├── tauri.conf.json      # Tauri 앱 설정 및 Sidecar 바이너리 매핑 설정
│   └── src/lib.rs           # Sidecar 기동, 포트 파싱 및 이벤트 브로드캐스팅
├── src/                     # React/Vite 프론트엔드 코드
├── backend/                 # Python FastAPI 백엔드 (AI 추론 / DB 관리)
│   ├── app/
│   │   ├── api/             # 슬림화된 FastAPI 라우터 모듈 모음
│   │   │   ├── analytics.py # 장비 통계 및 분석 API
│   │   │   ├── chat.py      # 포트폴리오 비평 및 AI 요약 API
│   │   │   ├── folders.py   # 폴더 관리(조회, 삭제) API
│   │   │   ├── indexing.py  # 백그라운드 인덱싱 제어(시작, 동기화, 파우즈, 캔슬) API
│   │   │   ├── photos.py    # 갤러리 목록, 메타데이터, 썸네일/원본 스트리밍 API
│   │   │   └── search.py    # 시맨틱 하이브리드 검색 및 유사도 쿼리 API
│   │   ├── core/
│   │   │   └── ports.py     # AI 모듈 인터페이스 (ImageEmbeddingPort, ImageCaptioningPort 등)
│   │   ├── repositories/    # 데이터 액세스 계층 (Data Access Layer)
│   │   │   ├── photo_repository.py  # SQLite ORM 쿼리, EXIF 필터링, 검색 조건 조합
│   │   │   └── vector_repository.py # ChromaDB Persistent 벡터 조작 및 캡슐화
│   │   ├── services/        # 비즈니스 로직 처리 계층 (Business Logic Layer)
│   │   │   ├── indexer/     # 모듈화된 인덱서 서브 패키지 [NEW]
│   │   │   │   ├── status.py   # 인덱싱 상태, pause/cancel 이벤트 및 글로벌 상태 관리
│   │   │   │   ├── scanner.py  # 디렉터리 스캔, 지원 확장자, SHA-256 해시 계산
│   │   │   │   ├── cleaner.py  # 좀비 레코드 청소, 폴더 삭제, SQLite-ChromaDB 보상 트랜잭션
│   │   │   │   └── worker.py   # 단일/배치 파일 인덱싱 워커, 비동기 조율 루프, 인플레이스 재인덱싱
│   │   │   ├── indexing_service.py # services/indexer 서브모듈을 하위 호환 재노출하는 Facade
│   │   │   ├── pipeline.py         # 파이프라인 패턴 기반 인덱싱 단계(Step) 조율
│   │   │   ├── photo.py            # 원본/썸네일 생성 및 캐싱, 원자적 레코드 저장
│   │   │   ├── search_service.py   # 하이브리드 검색(텍스트+SigLIP 2+EXIF 필터) 비즈니스 로직 [NEW]
│   │   │   ├── chat_service.py     # VLM 사진 비평 생성, UniPercept/Gemma 메모리 교체, 요약 [NEW]
│   │   │   ├── model_downloader.py # Hugging Face 모델 백그라운드 다운로더 [NEW]
│   │   │   ├── mlx_adapters.py     # SigLIP 2 및 Gemma 4 MLX 모델 로딩, 60s Keep-alive 캐시
│   │   │   ├── unipercept_adapter.py # UniPercept 8B 비평 전문 모델 어댑터 및 메모리 언로드
│   │   │   ├── ai_factory.py       # AI 어댑터 싱글톤 팩토리
│   │   │   └── taxonomy.py         # Zero-shot 비주얼 키워드 분류체계
│   │   ├── utils/
│   │   │   ├── image.py            # RAW 디코딩, EXIF 메타데이터 파싱
│   │   │   └── process.py          # 부모 프로세스 데드락 감시 (watch_parent) [NEW]
│   │   ├── config.py               # 개발/운영 환경 판별 및 데이터 경로 설정
│   │   ├── database.py             # SQLAlchemy 접속(WAL 모드, FK 강제) 및 스키마 마이그레이션 (run_migrations)
│   │   ├── models.py               # SQLite ORM 스키마 (Image, ImageMetadata, AIAnalysis, IndexedFolder 등)
│   │   ├── chroma.py               # ChromaDB 로컬 Persistent 설정 및 셀프 힐링
│   │   ├── schemas.py              # Pydantic API 요청/응답 스키마
│   │   └── main.py                 # FastAPI 진입점 (슬림화된 엔트리포인트, uvicorn 동적 포트 서빙)
│   └── requirements.txt            # Python 의존성
├── docs/                    # 프로젝트 공식 기획 및 명세 문서 모음
└── ~/.config/focal_node/    # 운영 데이터 폴더 (~/.config/focal_node_dev 개발용)
    ├── focal_node.db        # 로컬 SQLite 데이터베이스
    ├── chroma/              # 벡터 데이터베이스 스토리지
    └── thumbnails/          # 고속 갤러리 로딩용 캐시 썸네일
```

---

## 3. 백엔드 주요 핵심 모듈 상세 설명

### 3.1. `main.py`, `database.py` 및 `config.py` (진입점 및 기반구조)
*   **`config.py`:** `sys.frozen` 구분에 따라 개발 환경(`~/.config/focal_node_dev`)과 실사용 환경(`~/.config/focal_node`)의 DB/캐시 경로를 엄격히 분리(Data Isolation)합니다.
*   **`database.py`:** 커넥션 이벤트 시 `PRAGMA journal_mode=WAL`과 `PRAGMA foreign_keys=ON`을 적용하여 동시성을 보장하며, `run_migrations()` 함수를 통해 신규 컬럼 DDL을 자동 안전 적용합니다.
*   **`main.py`:** 슬림화된 진입점으로 FastAPI 라우터 등록 및 `uvicorn` 동적 포트 서빙(`[Sidecar] PORT: {port}`)에 집중하며, `services/model_downloader.py` 및 `utils/process.py`를 호출하여 백그라운드 태스크를 개시합니다.

### 3.2. AI 어댑터 및 팩토리 계층 (`core/ports.py`, `services/mlx_adapters.py`, `services/ai_factory.py`)
*   `ports.py`에 정의된 포트 추상 인터페이스를 기반으로 MLX 가속 어댑터를 구현합니다.
*   **SigLIP2Adapter:** 768차원 L2 정규화 벡터 생성 및 Zero-shot 시각 키워드 분류를 수행합니다.
*   **GemmaAdapter / UniPerceptAdapter:** Gemma 4 (E4B-it) 모델 및 UniPercept 모델을 통한 캡션/비평 생성. Gemma는 60초 Keep-alive 데몬으로 VRAM을 자진 반환하며, UniPercept는 16GB 메모리 절약을 위해 비평 완료 후 즉시 모델 언로드를 실행합니다.

### 3.3. 인덱서 서브 모듈 패키지 (`services/indexer/` 및 `services/indexing_service.py`)
*   **단일 책임 분리:** 547라인의 `indexing_service.py`를 `status.py`(상태 관리), `scanner.py`(파일 스캔/해시), `cleaner.py`(좀비 레코드 청소/원자적 삭제), `worker.py`(인덱싱 파이프라인 워커)로 해체하여 모듈화했습니다.
*   **Facade 패턴:** 기존 `indexing_service.py`는 `services.indexer` 모듈들을 re-export하여 100% 역방향 호환성을 유지합니다.
*   **이벤트 루프 비차단:** 무거운 연산은 `asyncio.to_thread`로 백그라운드 스레드 풀에 위임합니다.
*   **보상 트랜잭션:** SQLite `commit` 실패 시 `VectorRepository.delete`를 호출하여 ChromaDB의 벡터를 즉시 롤백합니다.

### 3.4. 비즈니스 서비스 & 레포지토리 계층 (`services/search_service.py`, `services/chat_service.py`, `repositories/`)
*   **`PhotoRepository`**: SQLite ORM 질의, EXIF 조건 결합, 페이지네이션 및 장비 분석 통계 집계 쿼리를 캡슐화합니다.
*   **`VectorRepository`**: ChromaDB CRUD 조작 및 K-NN 유사도 검색을 전담 캡슐화합니다.
*   **`SearchService`**: SQLite 텍스트 검색 결과와 SigLIP 2 벡터 검색 결과를 가중 합성하는 하이브리드 검색 비즈니스 로직을 수행합니다.
*   **`ChatService`**: VLM 모델 선택(Gemma vs UniPercept), 영-한 번역 및 비평 요약 보고서 생성 워크플로우를 처리합니다.

---

## 4. 프론트엔드 연동 흐름 (Tauri Sidecar)
Tauri 백엔드(`src-tauri/src/lib.rs`)는 구동 시 Python 백엔드 프로세스를 실행하고 stdout 스트림에서 `[Sidecar] PORT: {port}` 구문을 정규식으로 파싱하여 프론트엔드 React 앱에 API 포트를 동적으로 주입합니다. 프론트엔드는 이 동적 포트 URL을 기반으로 갤러리 조회, 백그라운드 인덱싱 제어, 검색 및 AI 비평 요청을 전송합니다.
