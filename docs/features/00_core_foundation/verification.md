# 🧪 [00_core_foundation] Verification & Ticket Logs

- **검증 상태**: `🩹 Debugging (DEFECT 1건 해결 대기)`
- **인수 조건 통과율**: `4 / 5 (80%)`
- **미해결 티켓**: `🚨 DEFECT: 1건` | `🧐 REFACTOR: 0건`

---

## 🎯 1. Given-When-Then 인수 조건 (Acceptance Criteria)

### AC 1. 동적 포트 바인딩 및 즉시 기동
* **Given:** 사용자가 데스크탑 앱을 실행했을 때,
* **When:** Python FastAPI 사이드카가 기동되면,
* **Then:** OS 유휴 포트(`port=0`)를 할당받아 `[Sidecar] PORT: {port}`를 stdout에 1회 출력하고, 프론트엔드가 `get_api_port` IPC로 포트를 수신하여 `/api/health` 통신에 성공해야 한다.

### AC 2. Metal GPU 동시성 직렬화 (`GPU_LOCK`)
* **Given:** 백그라운드 1단계 인덱싱(SigLIP 2 MPS)이 실행 중인 상태에서,
* **When:** 사용자가 온디맨드 AI 비평(Gemma 4 MLX 또는 UniPercept MPS)을 동시에 요청하면,
* **Then:** `GPU_LOCK`을 통해 Metal 컨텍스트 접근이 직렬화되어 프로세스 크래시 없이 순차 처리되어야 한다.

---

## 🧪 2. 테스트 시나리오 매트릭스 (Test Matrix)

| 구분 | 테스트 ID | 시나리오 설명 | 입력 / 조작 조건 | 기대 결과 | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Happy** | `TC-CF-01` | 동적 포트 사이드카 연결 | 앱 콜드 스타트 | `[Sidecar] PORT` 감지 및 갤러리 진입 | `PASS` |
| **Boundary**| `TC-CF-02` | 모델 60초 Keep-alive 언로드 | Gemma 4 추론 후 60초 유휴 | 60초 후 가중치 메모리 해제 확인 | `PASS` |
| **Negative**| `TC-CF-03` | 모델 미다운로드 상태 기동 | 로컬 HF 캐시 미존재 | `ModelDownloadModal` 노출 및 진행률 표시 | `PASS (Fixed in DEFECT-03)` |
| **Boundary**| `TC-CF-04` | 모델 인덱스 손상 시 가중치 무결성 검증 | 손상된 index.json 주입 | 정상 가중치 오판 차단 및 재다운로드 유도 | `PASS (Fixed in DEFECT-01)` |
| **Boundary**| `TC-CF-05` | 다운로드 재시도 시 동시성 및 파일 락 정합성 | 다운로드 중 POST /download | 중복 스레드 및 락 삭제 충돌 방지 | `FAIL (DEFECT-04)` |

---

## 🚨 3. 결함 리포트 (Defect Logs)

### [DEFECT-01] `is_snapshot_weights_valid`의 손상된 인덱스 JSON 파싱 실패 시 `valid=True` 오판 및 결함 모델 영구 캐시 오염
- **심각도**: 🔴 P0 Critical (Silent Degradation / False Validation)
- **위치**: [`backend/app/services/model_downloader.py#L120-L179`](../../../backend/app/services/model_downloader.py#L120-L179)
- **근본 원인 분석**:
  - `is_snapshot_weights_valid`는 `model.safetensors.index.json` 또는 `pytorch_model.bin.index.json` 존재 시 `len(get_missing_sharded_files(snapshot_dir)) == 0`으로 유효성을 판단함.
  - `get_missing_sharded_files`는 `json.load(f)` 실패 시 예외를 로깅만 하고 빈 리스트(`[]`)를 반환함.
  - 이로 인해 다운로드 중단 등으로 1바이트만 남은 깨진 인덱스 파일만 있고 가중치 파일이 0개인 디렉토리도 `len(missing) == 0`이 되어 `valid=True`로 통과됨.
  - `_is_model_cached()`가 이를 `status="cached"`로 오판하여 실제 가중치 다운로드를 영구 건너뛰며, 추론 시 크래시를 유발함.
- **해결 내역**:
  - **수정 파일**: [`backend/app/services/model_downloader.py`](../../../backend/app/services/model_downloader.py#L120-L179), [`backend/tests/test_model_downloader.py`](../../../backend/tests/test_model_downloader.py#L55-L82)
  - **원인 및 조치**: `get_missing_sharded_files`에서 인덱스 파일 파싱 실패(`json.load` 예외), 비딕셔너리 구조 또는 비어있는 `weight_map` 감지 시 결함 인덱스 파일 자체를 `missing` 목록에 추가하도록 교정. `is_snapshot_weights_valid`에서 인덱스 파싱 예외 발생 시 `False`를 반환하도록 안전하게 래핑하여 결함 모델의 영구 캐시 오판 및 런타임 추론 크래시를 원천 방지함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_model_downloader.py` (`PASS`, 4 passed)
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)

### [DEFECT-02] 모델 다운로더의 실패 모델 무시 및 거짓 성공 이벤트(`model-download-completed`) 조기 발행
- **심각도**: 🔴 P0 Critical (False Success / Silent Degradation)
- **위치**: [`backend/app/services/model_downloader.py#L347-L378`](../../../backend/app/services/model_downloader.py#L347-L378), [`src-tauri/src/lib.rs#L322-L324`](../../../src-tauri/src/lib.rs#L322-L324), [`src/hooks/useTauriEvents.ts#L106-L110`](../../../src/hooks/useTauriEvents.ts#L106-L110)
- **근본 원인 분석**:
  - `download_models_background()`가 `download_with_retry()`의 반환값(`bool`)을 확인하지 않고, SigLIP 2나 Gemma 4가 실패(`False`, `status="error"`)해도 무조건 다음 모델로 진행한 뒤 마지막에 `print("[Downloader] Completed all model downloads.")`를 무조건 출력함.
  - Rust 호스트(`lib.rs`)가 이를 감지하여 `model-download-completed`를 emit하고, 프론트엔드 `useTauriEvents.ts`가 `setIsDownloadingModel(false)`를 실행하여 에러를 삼키고 모달을 정상 완료 상태로 닫아버림.
- **해결 내역**:
  - **수정 파일**: [`backend/app/services/model_downloader.py`](../../../backend/app/services/model_downloader.py#L347-L378), [`src-tauri/src/lib.rs`](../../../src-tauri/src/lib.rs#L322-L324), [`src/hooks/useTauriEvents.ts`](../../../src/hooks/useTauriEvents.ts#L106-L110), [`backend/tests/test_model_downloader.py`](../../../backend/tests/test_model_downloader.py#L84-L120)
  - **원인 및 조치**: `download_models_background`에서 모델 다운로드 결과(`results`)를 취합하여 모든 모델이 성공(`True`)했을 때만 `[Downloader] Completed all model downloads.` 출력 및 `True`를 반환하도록 수정. 모델 다운로드 실패 시 `[Downloader] Download process finished with errors.`를 출력하고 `False`를 반환하여 Rust의 `model-download-completed` 조기 발행을 차단함. 추가로 Rust 호스트(`lib.rs`)의 완료 문자열 일치 조건을 엄격화하고 `useTauriEvents.ts`에서 에러 상태 시 모달을 닫지 않도록 가드를 보강함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_model_downloader.py` (`PASS`, 6 passed), `npm run build` (`PASS`)
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)

### [DEFECT-03] `ModelDownloadStatusTracker` 미초기화 및 `_calculate_overall_progress`의 모델 1종 완료 시 조기 `is_all_done: true` 반환 및 15초 폴링 블랙아웃 레이스
- **심각도**: 🟠 P1 High (Premature Completion & Polling Blackout Race)
- **위치**: [`backend/app/services/model_downloader.py#L52-L78`](../../../backend/app/services/model_downloader.py#L52-L78), [`backend/app/main.py#L91-L105`](../../../backend/app/main.py#L91-L105), [`src/hooks/useModelDownloadStatus.ts#L50-L65`](../../../src/hooks/useModelDownloadStatus.ts#L50-L65)
- **근본 원인 분석**:
  - `ModelDownloadStatusTracker`가 `self._statuses = {}`로 시작하여 `KNOWN_MODEL_SIZES`의 3개 모델이 등록되지 않은 상태로 기동됨.
  - `_calculate_overall_progress`는 `len(statuses) > 0 and all(...)`로 전체 완료를 판단하여, 1번째 모델(SigLIP 2)만 캐시 확인된 순간 `is_all_done: true`, `progress: 100`을 반환함.
  - 프론트엔드 `useModelDownloadStatus.ts`는 이를 받아 모달을 닫고 15초 슬로우 폴링으로 전환함. 그 사이 2번째 모델(Gemma 4, 12GB) 다운로드가 시작되지만 프론트엔드는 15초 동안 인지하지 못해 미완성 모델 크래시 또는 15초 뒤 모달이 재오픈되는 레이스가 발생함.
  - 또한 대기/초기화 상태에서 `scheduleNext(15000)`이 호출되어 최초 15초간 다운로드 감지가 지연됨.
- **해결 내역**:
  - **수정 파일**: [`backend/app/services/model_downloader.py`](../../../backend/app/services/model_downloader.py#L16-L78), [`backend/app/main.py`](../../../backend/app/main.py#L91-L115), [`src/hooks/useModelDownloadStatus.ts`](../../../src/hooks/useModelDownloadStatus.ts#L50-L65), [`backend/tests/test_model_downloader.py`](../../../backend/tests/test_model_downloader.py#L120-L195)
  - **원인 및 조치**: `ModelDownloadStatusTracker` 싱글톤 초기화 시 `KNOWN_MODEL_SIZES`의 3개 모델을 `status="pending"`, `progress=0`으로 사전 등록하고 `reset_statuses()`를 추가함. `_calculate_overall_progress`에서 `len(statuses) >= len(KNOWN_MODEL_SIZES)` 검사를 필수 조건으로 강제하여 모델 1종 완료 시 조기 `is_all_done: true` 반환을 원천 차단함. `useModelDownloadStatus.ts`에서 대기/초기화 상태일 때 15초가 아닌 빠른 폴링(2500ms)을 유지하고 `is_all_done`이 진성 참일 때만 15초 슬로우 폴링으로 전환하도록 교정함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_model_downloader.py` (`PASS`, 8 passed), `npm run build` (`PASS`)
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)

### [DEFECT-04] `start_background_model_downloader(force=True)` 재시도 시 고아 스레드 증식 및 HF 파일 락 삭제 레이스
- **심각도**: 🟠 P1 High (Concurrency Race & Cache Corruption)
- **위치**: [`backend/app/services/model_downloader.py#L228-L241, #L343-L351`](../../../backend/app/services/model_downloader.py#L228-L241), [`backend/app/main.py#L121-L131`](../../../backend/app/main.py#L121-L131)
- **근본 원인 분석**:
  - `POST /api/system/models/download` 호출 시 `start_background_model_downloader(force=True)`가 호출됨.
  - `force=True` 조건으로 인해 이전 스레드가 여전히 실행 중임에도 불구하고 새 스레드가 생성되어 `_downloader_thread`를 덮어쓰고 고아 스레드가 됨.
  - 2번째 스레드가 시작되며 `clear_stale_hf_locks()`를 호출해 1번째 스레드가 점유 중인 `.lock` 파일을 강제 삭제하고 동일 캐시 경로에 동시 다운로드를 실행하여 HF 세션 충돌 및 파일 손상이 발생함.
- **수정 계획**:
  - `start_background_model_downloader`에서 `_downloader_thread.is_alive()`가 `True`인 경우 `force=True`여도 중복 스레드를 띄우지 않고 기존 스레드를 재사용하도록 가드 적용.
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] 기동 시 `chromadb`/`rawpy` 상단 연쇄 임포트 분리 및 Silent Fail(`except: pass`) 제거
- **현재 상태**: 🟢 RESOLVED — `chroma.py` 지연 로딩 및 `base_model.py`/`model_downloader.py` Silent Fail 로깅 보강 완료

