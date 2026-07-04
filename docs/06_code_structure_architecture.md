# 06. Focal Node Code Structure & Architecture

본 문서는 **Focal Node (AI 기반 로컬 프라이버시 사진 검색 앱)**의 전체 애플리케이션 아키텍처와 주요 코드 디렉토리 구조, 그리고 핵심 모듈들의 역할을 정리합니다.

---

## 1. 하이브리드 애플리케이션 아키텍처

Focal Node는 프론트엔드와 백엔드가 완전히 분리되어 OS 프로세스 간 통신을 수행하는 하이브리드 형태(Tauri Sidecar 아키텍처)를 취하고 있습니다.

*   **Tauri (Rust) - 프론트엔드 호스트:**
    *   Vite + React.js(예정) 기반의 사용자 인터페이스를 웹뷰(Webview)로 렌더링합니다.
    *   OS의 파일 시스템 직접 접근을 담당하며, Python 백엔드 프로세스를 **Sidecar** 형태로 자식 프로세스로 띄우고 라이프사이클을 함께 관리합니다.
*   **FastAPI (Python) - 백그라운드 인덱싱 및 AI 엔진:**
    *   MLX 가속(Apple Silicon)을 사용하여 대용량 VLM(Vision-Language Model) 모델의 추론을 담당합니다.
    *   인덱싱 큐, 로컬 DB 동기화, 사진 메타데이터 추출 등 무거운 CPU/GPU Bound 작업을 전담하여 UI의 멈춤 현상(Freezing)을 방지합니다.

---

## 2. 전체 디렉토리 및 파일 구조

```text
focal_node/
├── src-tauri/               # Tauri(Rust) 백엔드 및 앱 패키징 로직 (Phase 4 구현 예정)
│   ├── tauri.conf.json      # Tauri 앱 설정 및 Sidecar 바이너리 매핑 설정
│   └── src/main.rs          # Python 사이드카 프로세스 기동 및 포트 파싱 로직
├── src/                     # React/Vite 프론트엔드 코드 (Phase 4 구현 예정)
├── backend/                 # Python FastAPI 백엔드 (AI 추론 / DB 관리)
│   ├── app/
│   │   ├── core/
│   │   │   └── ports.py     # AI 모듈 및 외부 종속성 역전을 위한 포트 인터페이스
│   │   ├── services/
│   │   │   ├── indexing_service.py # 백그라운드 증분 파일 스캔 및 트랜잭션 처리
│   │   │   ├── mlx_adapters.py     # SigLIP2 및 Gemma4 MLX 모델 로딩, 60s Keep-alive 캐시 전략
│   │   │   └── photo.py            # SQLite 메타데이터 및 ChromaDB 트랜잭션 CRUD
│   │   ├── utils/
│   │   │   ├── exif.py             # EXIF 데이터 추출 유틸
│   │   │   └── image.py            # RAW 확장자(ARW 등) PIL 디코딩 (rawpy 활용)
│   │   ├── database.py             # SQLAlchemy 접속(WAL 모드, FK 강제) 엔진
│   │   ├── models.py               # SQLite ORM 스키마 (images, ai_analysis)
│   │   ├── chroma.py               # ChromaDB 로컬 Persistent 설정
│   │   └── main.py                 # FastAPI 라우팅 엔드포인트 및 동적 포트(port=0) 할당 진입점
│   └── requirements.txt            # Python 의존성 (mlx-vlm, rawpy 등 포함)
├── docs/                    # 프로젝트 공식 기획 및 명세 문서 모음
│   ├── 01_system_architecture_db.md
│   ├── ...
│   └── 06_code_structure_architecture.md
└── focal_node.db            # SQLite 데이터베이스 (인덱싱 완료 시 생성됨)
└── chroma_db/               # Chroma 벡터 데이터베이스 스토리지 (인덱싱 완료 시 생성됨)
```

---

## 3. 백엔드 주요 핵심 모듈 상세 설명

### 3.1. `main.py` (진입점)
*   **동적 포트 할당:** `uvicorn.run(port=0)`으로 실행되어 OS 유휴 포트를 부여받고, 해당 포트를 `[Sidecar] PORT: {port}` 규격으로 stdout에 출력합니다.
*   **비동기 라우터:** `/api/index/start`, `/api/index/status`, `/api/photos` 등 외부 통신 엔드포인트를 노출합니다.

### 3.2. `core/ports.py` 및 `services/mlx_adapters.py` (AI 계층)
*   객체 지향 설계 원칙을 준수하여 `ports.py`에 정의된 추상화 인터페이스를 `mlx_adapters.py`가 구현합니다.
*   **SigLIP2Adapter:** 텐서 추출의 MPS 최적화와 Pooling 처리를 구현하여 768차원 벡터를 반환합니다.
*   **GemmaAdapter:** `strict=False`를 활용한 4-bit 모델의 Lazy Loading을 수행합니다. 내부에 백그라운드 스레드를 두어 모델을 **60초 동안만 상주**시키고, 활동이 없으면 `mx.clear_cache()`를 호출해 VRAM을 자진 반환하는 데몬 모니터링 로직이 핵심입니다.

### 3.3. `services/indexing_service.py` (비동기 인덱서)
*   **이벤트 루프 비차단:** 파일 시스템의 해시 생성 및 MLX 기반 모델 추론처럼 연산 집약적인 함수들을 `asyncio.to_thread`를 사용하여 별도의 스레드 풀로 넘깁니다. 이 덕분에 사진 수만 장을 인덱싱할 때도 FastAPI의 본래 비동기 루프는 블로킹되지 않고 API 상태 요청에 즉시 응답할 수 있습니다.
*   **데이터 정합성 (보상 트랜잭션):** SQLite와 ChromaDB 양쪽에 동시 삽입이 일어날 때, SQLite `commit`이 실패하거나 Unique Key 제약조건에 걸릴 경우 `try-except` 블록 내에서 방금 삽입한 ChromaDB의 벡터를 즉시 삭제(Rollback)하여 고아(Orphan) 임베딩 생성을 방지합니다.

### 3.4. `database.py` 및 `models.py` (DB 계층)
*   SQLite 연결 시마다 이벤트 리스너를 발동하여 `PRAGMA journal_mode=WAL` (Write-Ahead Logging)과 `PRAGMA foreign_keys=ON`을 강제합니다. 이는 백그라운드 인덱서의 쓰기 작업 중에도 갤러리 뷰 읽기 작업의 동시성을 보장하여 데드락(`database is locked`)을 예방합니다.

---

## 4. 향후 프론트엔드 연동 흐름 (Phase 4)
Tauri 백엔드(`main.rs`)는 구동 시 Python 백엔드 실행 스크립트를 `Command::new`로 실행한 후, 파이프 라인을 통해 stdout 스트림을 읽습니다. 여기서 정규식을 이용해 `[Sidecar] PORT: 65308`과 같은 포트 문구를 캡처하고, 이를 `http://127.0.0.1:65308` 포맷의 베이스 URL로 변환하여 React 프론트엔드의 전역 컨텍스트 혹은 상태 관리자에 주입하게 됩니다. 프론트엔드는 이 주소를 기반으로 모든 검색과 사진 메타데이터 질의를 수행합니다.
