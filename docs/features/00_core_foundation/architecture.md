# [Architecture] 00. Core Foundation & System Blueprint

본 문서는 프로젝트 전역 시스템 구조, 단방향 계층 의존성 규칙, 그리고 모든 도메인이 반드시 준수해야 할 **엔지니어링 5대 제약사항**을 정의합니다.

---

## 🏛️ 1. 전역 시스템 데이터 및 제어 흐름

```mermaid
flowchart TD
    subgraph DesktopClient["데스크탑 클라이언트 (Tauri v2 + React 19)"]
        UI["Domain Views (src/components/*)"]
        Store["Zustand Global Store (src/store/useAppStore.ts)"]
        ApiClient["HTTP API Client (src/services/api.ts)"]
        TauriHost["Tauri Rust Host (src-tauri/src/lib.rs)"]
        
        UI --> Store
        UI --> ApiClient
        ApiClient --> Store
        UI -.->|IPC: reveal_in_finder, save_binary_file| TauriHost
        TauriHost -.->|포트 조회(get_api_port) & Native Events| UI
    end

    subgraph BackendSidecar["백엔드 사이드카 (FastAPI 3-Tier)"]
        APILayer["API Routers (backend/app/api/*)"]
        ServiceLayer["Services (backend/app/services/*)"]
        RepoLayer["Repositories & Adapters (backend/app/repositories/*)"]
        GPULock["GPU_LOCK (threading.RLock: Metal 직렬화)"]
        
        APILayer --> ServiceLayer --> RepoLayer --> GPULock
    end

    subgraph Storage["로컬 스토리지 & Apple Silicon"]
        SQLiteDB[("SQLite WAL (focal_node.db)")]
        ChromaStore[("ChromaDB (photo_embeddings)")]
        ThumbCache[("Thumbnail Cache (360px JPEG)")]
        AppleSilicon["Unified Memory (MLX: Gemma 4 / MPS: SigLIP 2, UniPercept)"]
    end

    ApiClient -->|Direct HTTP| APILayer
    RepoLayer --> SQLiteDB
    RepoLayer --> ChromaStore
    ServiceLayer --> ThumbCache
    GPULock --> AppleSilicon
```

---

## 🏗️ 2. 코어 인프라 파일 트리 (단일 책임)

```text
focal_node/
├── src-tauri/src/
│   ├── main.rs                        # [기존] Tauri 엔트리포인트 (focal_node_lib::run 호출)
│   └── lib.rs                         # [기존] 사이드카 스폰, [Sidecar] PORT 파싱, IPC(get_api_port, reveal_in_finder, save_binary_file) 및 Tauri 이벤트 발행
├── src/
│   ├── App.tsx                        # [기존] 앱 루트 레이아웃, 초기 포트 바인딩, 탭 라우팅 및 멀티윈도우 팝아웃 분기
│   ├── services/api.ts                # [기존] 백엔드 동적 포트 기반 Direct HTTP 통신 클라이언트
│   ├── hooks/
│   │   ├── useBackendInit.ts          # [기존] get_api_port 대기, /api/health 초기 확인 및 5초 주기 헬스체크
│   │   ├── useTauriEvents.ts          # [기존] 사이드카 stdout 기반 Tauri 네이티브 이벤트 리스너
│   │   └── useModelDownloadStatus.ts  # [기존] AI 모델 다운로드 진행 상태 Polling 커스텀 훅
│   └── components/
│       ├── ModelDownloadModal.tsx     # [기존] AI 모델 다운로드 진행률/재시도 모달
│       └── common/
│           ├── AppSplash.tsx          # [기존] 백엔드 기동 대기 스플래시 화면
│           ├── ErrorBoundary.tsx      # [기존] 전역 React 에러 바운더리
│           └── LoadingSpinner.tsx     # [기존] 공통 로딩 스피너 컴포넌트
└── backend/app/
    ├── main.py                        # [기존] port=0 바인딩, CORS, /api/health, /api/system/models/* 라우트
    ├── config.py                      # [기존] IS_PROD 기반 ~/.config/focal_node(_dev) 경로 격리
    ├── database.py                    # [기존] SQLAlchemy 엔진, SQLite WAL & foreign_keys=ON 리스너, run_migrations()
    ├── chroma.py                      # [기존] ChromaDB 클라이언트 및 Self-Healing 초기화
    ├── core/ports.py                  # [기존] AI 추론 어댑터 추상 포트 인터페이스
    ├── utils/process.py               # [기존] 부모 프로세스(Tauri) 종료 감지 시 사이드카 자동 종료 데몬(watch_parent)
    └── services/
        ├── base_model.py              # [기존] GPU_LOCK(RLock) 및 BaseKeepAliveModel 추상 베이스 클래스
        ├── ai_factory.py              # [기존] SigLIP2Adapter / GemmaAdapter 싱글턴 팩토리
        └── model_downloader.py        # [기존] HuggingFace 스냅샷 백그라운드 다운로더 및 진행률 트래커
```

---

## 🔒 3. 계층 간 의존성 및 엔지니어링 5대 제약사항

1. **단방향 의존성 원칙**:
   `UI Components` ➔ `Custom Hooks & Store` ➔ `ApiClient (HTTP)` ➔ `FastAPI Routers` ➔ `Services` ➔ `Repositories`
   - 프론트엔드는 데이터 송수신 시 Rust IPC를 거치지 않고 FastAPI로 직접 HTTP 통신합니다(포트 조회 `get_api_port`, Finder 노출 `reveal_in_finder`, 바이너리 파일 저장 `save_binary_file` 제외).
   - FastAPI 라우터에서 복잡한 쿼리는 `PhotoRepository` 및 `VectorRepository` 계층으로 캡슐화합니다.
2. **Rule 2.1 (동적 포트 바인딩)**: `port=0`으로 유휴 포트를 할당받고 stdout에 `[Sidecar] PORT: {port}`를 단 1회 출력합니다.
3. **Rule 2.2 (SQLite WAL & 보상 트랜잭션)**: 커넥션마다 `PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;`을 강제하며, ChromaDB upsert 후 SQLite 커밋 실패 시 `CompensatingTransactionManager`로 즉시 롤백합니다.
4. **Rule 2.3 (RAW 인메모리 스트리밍 & 세마포어)**: 디스크 임시 파일 없이 `rawpy`로 메모리 디코딩하며 `MAX_CONCURRENT_DECODES = 3` 세마포어를 강제합니다.
5. **Rule 2.4 (이벤트 루프 보호 & AI 수명주기)**:
   - 무거운 작업은 `asyncio.to_thread()`로 분리하고 `GPU_LOCK`으로 Metal 충돌을 방지합니다.
   - **Gemma 4 (MLX)**: 유휴 시 **60초 Keep-alive** 후 언로드.
   - **UniPercept 8B (PyTorch MPS)**: 약 28GB 메모리 점유 방지를 위해 비평 완료 즉시 `finally`에서 **강제 언로드**합니다.

---

## 🧪 4. 표준 검증 및 실행 명령어 (Standard Verification Commands)

> 모든 개발(`clean-code-developer`), 감사(`clean-code-auditor`), QA(`user-journey-tester`), 디버깅(`systematic-debugger`) 세션은 아래 표준 명령어를 사용하여 검증합니다.

* **백엔드 전체 단위/통합 테스트**: `./venv/bin/pytest backend/tests/ -v`
* **백엔드 도메인별 핀셋 테스트**:
  - 코어/동시성/다운로더: `./venv/bin/pytest backend/tests/test_model_downloader.py backend/tests/test_backend_hardening.py backend/tests/test_concurrency_hardening.py`
  - 인덱싱/폴더/미디어: `./venv/bin/pytest backend/tests/test_api_indexing.py backend/tests/test_api_folders.py backend/tests/test_api_photos.py backend/tests/test_siglip_zero_shot.py`
  - 하이브리드 검색: `./venv/bin/pytest backend/tests/test_api_search.py`
  - AI 비평/앙상블/취소: `./venv/bin/pytest backend/tests/test_unipercept.py backend/tests/test_ensemble_math.py backend/tests/test_critique_cancellation.py backend/tests/test_critique_sleep_recovery.py`
  - 장비 통계: `./venv/bin/pytest backend/tests/test_api_analytics.py`
* **프론트엔드 타입체크 및 프로덕션 빌드 검증**: `npx tsc --noEmit && npm run build`
* **사이드카 PyInstaller `--onedir` 패키징 빌드**: `./venv/bin/python backend/build_backend.py`
* **로컬 개발 서버 실행 (Tauri + Sidecar)**: `npm run tauri dev`
* **위키 문서 무결성 헬스체크**: `python3 -B ~/.gemini/config/skills/interactive-feature-planner/scripts/check_wiki_health.py docs`
