# [Spec & Contracts] 00. Core Foundation

본 문서는 코어 부트스트래핑, 환경 격리 및 AI 모델 관리 시스템의 풀스택 계약을 정의합니다.

---

## ⚙️ 1. 런타임 부트스트래핑, 환경 격리 및 AI 모델 명세 `[As-Is 기구현]`

| 항목 | 개발 환경 (`IS_PROD = False`) | 프로덕션 환경 (`IS_PROD = True`, PyInstaller `--onedir`) |
| :--- | :--- | :--- |
| **데이터 루트 경로 (`CONFIG_DIR`)** | `~/.config/focal_node_dev/` | `~/.config/focal_node/` |
| **SQLite DB 경로 (`DATABASE_URL`)** | `~/.config/focal_node_dev/focal_node.db` | `~/.config/focal_node/focal_node.db` |
| **ChromaDB 경로 (`CHROMA_DB_DIR`)** | `~/.config/focal_node_dev/chroma/` | `~/.config/focal_node/chroma/` |
| **썸네일 캐시 경로 (`THUMBNAIL_CACHE_DIR`)** | `~/.config/focal_node_dev/thumbnails/` | `~/.config/focal_node/thumbnails/` |
| **Metal 셰이더 캐시 (`METAL_CACHE_DIR`)** | `~/.config/focal_node_dev/metal_cache/` | `~/.config/focal_node/metal_cache/` |

* **로컬 구동 AI 모델 (`KNOWN_MODEL_SIZES`, HuggingFace Hub 캐시 `~/.cache/huggingface/hub/`)**:
  - `google/siglip2-base-patch16-224` (~1.54 GB, PyTorch MPS, 메모리 상주)
  - `mlx-community/gemma-4-12B-it-8bit` (~12.75 GB, Apple MLX, 60초 Keep-alive)
  - `widegather/unipercept-mirror` (~24.95 GB, PyTorch MPS `bfloat16`, 추론 직후 즉시 언로드)
* **Heavy AI 모듈 지연 임포트 (Lazy Import)**: `torch`, `mlx`, `mlx_vlm`, `transformers`는 앱 기동 시점에 상단 Eager Import 하지 않고 백그라운드 워커 또는 최초 추론 시점에 지연 로드합니다.

---

## 🌐 2. 백엔드 시스템 API 계약 (`/api/health`, `/api/system`) `[As-Is 기구현]`

### 2.1. 헬스체크 및 모델 상태 조회
* `GET /api/health`
  - **Response 200:** `{ "status": "ok" }`
* `GET /api/system/models/status`
  - **Response 200:**
    ```json
    {
      "statuses": {
        "google/siglip2-base-patch16-224": {
          "repo_id": "google/siglip2-base-patch16-224",
          "label": "SigLIP 2 (시각/텍스트 검색 엔진)",
          "status": "cached",
          "downloaded_bytes": 1539458338,
          "total_bytes": 1539458338,
          "progress": 100,
          "error_message": null,
          "updated_at": 1729160000.0
        },
        "mlx-community/gemma-4-12B-it-8bit": { "..." : "..." },
        "widegather/unipercept-mirror": { "..." : "..." }
      },
      "overall": {
        "progress": 100,
        "downloaded_bytes": 39240231646,
        "total_bytes": 39240231646,
        "current_label": "모든 AI 모델 준비 완료",
        "is_all_done": true
      }
    }
    ```
* `POST /api/system/models/download`
  - **Request Body:** 없음 (미설치/오류 상태인 전체 모델 백그라운드 다운로드 재시작 `force=True`)
  - **Response 200:** `{ "started": true, "statuses": { ... }, "overall": { ... } }`

---

## 💻 3. 프론트엔드 타입, IPC 및 이벤트 계약 `[As-Is 기구현]`

### 3.1. Tauri Rust IPC Commands (`src-tauri/src/lib.rs`)
* `invoke<number>('get_api_port')`: 사이드카가 할당받은 로컬호스트 포트 번호 반환 (할당 완료 시까지 Rust 내부 100ms 대기 루프 수행).
* `invoke<void>('reveal_in_finder', { path: string })`: macOS Finder에서 해당 파일 선택 및 노출 (`open -R`).
* `invoke<void>('save_binary_file', { path: string, data: number[] })`: 내보내기 모달에서 생성된 Markdown/PDF 바이트 배열을 지정한 로컬 경로에 저장.

### 3.2. Tauri Native Events (`src-tauri/src/lib.rs` ➔ `src/hooks/useTauriEvents.ts`)
* **모델 다운로드 이벤트**: `model-download-started`, `model-download-progress`, `model-download-completed`
* **인덱싱/동기화 이벤트**: `indexing-progress`, `indexing-completed`, `indexing-paused`, `indexing-resumed`, `indexing-cancelled`, `sync-completed`

---

## 🛡️ 4. 예외 처리 및 엣지 케이스 정책

1. **사이드카 기동 확인 및 주기적 헬스체크 (`useBackendInit.ts`)**: 초기 마운트 시 `get_api_port` IPC 응답 후 `/api/health`를 검증하여 `AppSplash`에서 메인 화면으로 전환하며, 이후 5초 주기로 `/api/health`를 폴링하여 연속 3회(`MAX_FAILURES = 3`) 실패 시 연결 오류 상태를 표시합니다.
2. **부모 프로세스 종료 시 좀비 방지 (`utils/process.py`)**: 백엔드 기동 시 `start_parent_watcher()` 데몬 스레드가 부모(Tauri) PID를 감시하여, 호스트 앱 강제 종료 시 사이드카 프로세스를 스스로 종료(`os.kill(os.getpid(), signal.SIGTERM)`)합니다.
