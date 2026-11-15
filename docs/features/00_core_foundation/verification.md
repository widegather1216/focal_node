# 🧪 [00_core_foundation] Verification & Ticket Logs

- **검증 상태**: `🩹 Debugging (3-Lens 딥버그 헌팅 완료 — DEFECT-05~11 7건 발견)`
- **인수 조건 통과율**: `1 / 5 (20%)`
- **미해결 티켓**: `🚨 DEFECT: 7건` | `🧐 REFACTOR: 0건`

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
| **Boundary**| `TC-CF-05` | 다운로드 재시도 시 동시성 및 파일 락 정합성 | 다운로드 중 POST /download | 중복 스레드 및 락 삭제 충돌 방지 | `PASS (Fixed in DEFECT-04)` |
| **Negative**| `TC-CF-06` | 비쓰기 macOS 릴리즈 `.app` 번들 사이드카 부팅 | `0o555` 읽기전용 `.app` 실행 | 심볼릭 링크 없이 `_internal` 정상 기동 | `FAIL (DEFECT-05)` |
| **Negative**| `TC-CF-07` | 부분 다운로드 스냅샷(`tokenizer.json` > 5MB) 검증 | 가중치 없이 `tokenizer.json`만 존재 | `is_snapshot_weights_valid() == False` 반환 | `FAIL (DEFECT-06)` |
| **Boundary**| `TC-CF-08` | 활성 VLM 요청 중 동시 비평 취소/언로드 경합 | `active_requests == 1` 중 `unload_model` | 활성 추론 보호 및 `NoneType` 크래시 방지 | `FAIL (DEFECT-07)` |
| **Negative**| `TC-CF-09` | `huggingface_hub==1.21.0` 손상 인덱스/샤드 재복구 | 손상된 `index.json` 로컬 캐시 잔존 | `force_download=True`로 정상 덮어쓰기 복구 | `FAIL (DEFECT-08)` |
| **Negative**| `TC-CF-10` | ChromaDB Self-Healing 복구 및 벡터 재동기화 | 손상된 `chroma.sqlite3` 주입 후 기동/sync | 크래시 없이 초기화 및 누락 벡터 재임베딩 | `FAIL (DEFECT-09)` |
| **Negative**| `TC-CF-11` | `GemmaAdapter` 추론 예외 시 파이프라인 전파 | MLX OOM/`RuntimeError` 발생 | 빈 메타데이터 커밋 차단 및 오류 격리 | `FAIL (DEFECT-10)` |
| **Security**| `TC-CF-12` | Tauri `save_binary_file` IPC 경로/CSP 경계 검증 | 임의 시스템 경로 쓰기 요청 | 허용 경로/확장자 외 차단 및 CSP 적용 | `FAIL (DEFECT-11)` |

---

## 🚨 3. 결함 리포트 (Defect Logs)

### [DEFECT-01] `is_snapshot_weights_valid`의 손상된 인덱스 JSON 파싱 실패 시 `valid=True` 오판 및 결함 모델 영구 캐시 오염
- **해결 요약**: `get_missing_sharded_files` 및 `is_snapshot_weights_valid`에서 손상/빈 `weight_map` 인덱스 감지 시 결함 파일 반환 및 `False` 처리 ([`model_downloader.py#L147-L206`](../../../backend/app/services/model_downloader.py#L147-L206), `pytest 4 passed`).
- **현재 상태**: 🟢 RESOLVED

### [DEFECT-02] 모델 다운로더의 실패 모델 무시 및 거짓 성공 이벤트(`model-download-completed`) 조기 발행
- **해결 요약**: `download_models_background` 전체 결과 `all(results)` 검증 및 `lib.rs`/`useTauriEvents.ts` 에러 보존 가드 적용 (`pytest 6 passed`, `npm run build` PASS).
- **현재 상태**: 🟢 RESOLVED

### [DEFECT-03] `ModelDownloadStatusTracker` 미초기화 및 모델 1종 완료 시 조기 `is_all_done: true` 반환 및 15초 폴링 블랙아웃
- **해결 요약**: `KNOWN_MODEL_SIZES` 3종 사전 등록, `_calculate_overall_progress` 전체 개수 검증, `useModelDownloadStatus.ts` 2500ms 빠른 폴링 유지 (`pytest 8 passed`, `npm run build` PASS).
- **현재 상태**: 🟢 RESOLVED

### [DEFECT-04] `start_background_model_downloader(force=True)` 재시도 시 고아 스레드 증식 및 HF 파일 락 삭제 레이스
- **해결 요약**: 활성 스레드 생존 시 `force=True` 무시 가드 절 적용으로 중복 스레드 및 락 삭제 충돌 차단 (`pytest 9 passed`, `112 passed`).
- **현재 상태**: 🟢 RESOLVED

### [DEFECT-05] macOS 릴리즈 `.app` 번들 비쓰기 환경에서 PyInstaller 사이드카 즉시 크래시
- **심각도**: 🔴 P0 Critical (`Crash / Packaging & Runtime Layout Mismatch`) | **실증**: `✅ Empirical Probe Reproduced`
- **위치**: [`src-tauri/src/lib.rs#L121-L181`](../../../src-tauri/src/lib.rs#L121-L181), [`src-tauri/tauri.conf.json#L34-L39`](../../../src-tauri/tauri.conf.json#L34-L39), [`backend/build_backend.py#L56-L65`](../../../backend/build_backend.py#L56-L65)
- **근본 원인 및 증거**: `tauri.conf.json`이 `_internal`을 `Contents/Resources/binaries/_internal/`에 배치하고 `lib.rs#L149-L170`이 런타임에 `Contents/MacOS/_internal` 및 `Contents/Frameworks` 심볼릭 링크를 생성하며 실패를 묵인(`let _ = ...`)함. `/Applications`·DMG·App Translocation·서명 번들 등 비쓰기 환경(`0o555`)에서 실바이너리(`focal_node_backend-aarch64-apple-darwin`) 실행 시 `returncode: 1`, `Fatal Python error: init_fs_encoding ... ModuleNotFoundError: No module named 'encodings'`로 즉시 종료됨.
- **최소 수정 설계**: 번들 빌드 시점에 `_internal`을 PyInstaller가 기대하는 `Contents/Frameworks`(또는 `Contents/MacOS/_internal`)에 정적 배치해 런타임 번들 변조 의존 제거.
- **현재 상태**: 🟡 OPEN

### [DEFECT-06] 부분 다운로드 스냅샷의 비가중치 파일(`tokenizer.json` > 5MB)을 가중치로 오인해 `"cached"` 거짓 성공 반환
- **심각도**: 🔴 P0 Critical (`Silent Degradation / False Validation`) | **실증**: `✅ Empirical Probe Reproduced`
- **위치**: [`backend/app/services/model_downloader.py#L187-L221`](../../../backend/app/services/model_downloader.py#L187-L221), [`model_downloader.py#L291-L305`](../../../backend/app/services/model_downloader.py#L291-L305)
- **근본 원인 및 증거**: `is_snapshot_weights_valid()` L217 폴백(`if size > 5 * 1024 * 1024: return True`)이 확장자 검증 없이 5MB 초과 파일만 존재해도 `True`를 반환함. 3종 모델 모두 `tokenizer.json`이 11~33MB이므로 가중치 파일 없이 `config.json` + 6MB `tokenizer.json`만 있는 임시 디렉토리 프로브에서 `is_snapshot_weights_valid() == True` 재현됨.
- **최소 수정 설계**: 확장자 무관 `size > 5MB` 분기 제거, 가중치 확장자(`.safetensors`/`.bin`/`.npz`/`.pth`/`.pt`)만 허용하며 샤드 파일 존재 시 `*.index.json` 누락이면 `False` 반환.
- **현재 상태**: 🟡 OPEN

### [DEFECT-07] `BaseKeepAliveModel.unload_model()`의 `active_requests` 미검사 및 `force=True` 강제 언로드로 인한 활성 추론 크래시
- **심각도**: 🔴 P0 Critical (`Concurrency Race / Crash & Silent Degradation`) | **실증**: `✅ Empirical Probe Reproduced`
- **위치**: [`backend/app/services/base_model.py#L134-L141`](../../../backend/app/services/base_model.py#L134-L141), [`chat_service.py#L45-L65`](../../../backend/app/services/chat_service.py#L45-L65), [`mlx_adapters.py#L104-L166`](../../../backend/app/services/mlx_adapters.py#L104-L166), [`unipercept_adapter.py#L131-L158`](../../../backend/app/services/unipercept_adapter.py#L131-L158)
- **근본 원인 및 증거**: `BaseKeepAliveModel.unload_model()`이 `self.active_requests == 0`을 검사하지 않고, `_unload_critique_models(force=True)`·`_run_unipercept_stage` `finally`가 타 요청의 `GPU_LOCK` 비점유 준비 구간(RAW 디코딩/프롬프트 구성) 중 모델/프로세서를 `None`으로 해제함. `active_requests == 1` 상태에서 `_unload_critique_models(force=True)` 호출 시 `adapter.model`/`processor`가 `None`으로 파괴됨을 실증함(`NoneType.apply_chat_template` 크래시 및 빈 메타데이터 저장).
- **최소 수정 설계**: `unload_model()`에 `active_requests == 0` 가드 및 지연 언로드 플래그 적용, `_run_mlx_vlm_generation()` 내 `GPU_LOCK` 획득 후 `model/processor is None` 시 재적재 가드 추가.
- **현재 상태**: 🟡 OPEN

### [DEFECT-08] `huggingface_hub==1.21.0` `force_download=False` 단락으로 인한 손상 인덱스/샤드 캐시 복구 영구 실패
- **심각도**: 🟠 P1 High (`Dependency Collision / Silent Recovery Failure`) | **실증**: `✅ Empirical Probe Reproduced`
- **위치**: [`backend/app/services/model_downloader.py#L243-L275`](../../../backend/app/services/model_downloader.py#L243-L275), [`model_downloader.py#L308-L335`](../../../backend/app/services/model_downloader.py#L308-L335)
- **근본 원인 및 증거**: `huggingface_hub==1.21.0`(`file_download.py#L1086`, `#L1225`)은 `force_download=False`일 때 로컬 포인터/블롭이 존재하면 네트워크 확인 없이 즉시 손상 파일을 반환함. 40자 `commit_hash` 스냅샷에 손상된 `model.safetensors.index.json` 배치 프로브 시 `hf_hub_download`가 손상 JSON을 그대로 반환하여 재시도 3회 모두 `RuntimeError`로 영구 실패함을 실증함.
- **최소 수정 설계**: `_download_snapshot_and_shards()`에서 누락/손상 파일 재다운로드 시 `force_download=True` 전달 및 불완전 스냅샷 재진입 시 손상 파일 선삭제/강제 재수신.
- **현재 상태**: 🟡 OPEN

### [DEFECT-09] `chroma.py` Self-Healing 시 `chromadb==1.5.9` 캐시 오염 크래시 및 SQLite-ChromaDB 재동기화 단절
- **심각도**: 🟠 P1 High (`Crash & Cross-Store Data Loss`) | **실증**: `✅ Empirical Probe Reproduced`
- **위치**: [`backend/app/chroma.py#L23-L37`](../../../backend/app/chroma.py#L23-L37), [`indexing_service.py#L148-L165`](../../../backend/app/services/indexing_service.py#L148-L165), [`search_service.py#L86-L106`](../../../backend/app/services/search_service.py#L86-L106)
- **근본 원인 및 증거**: 손상된 `chroma.sqlite3` 주입 프로브 시 `SharedSystemClient._create_system_if_not_exists`가 실패한 `System`을 `_identifier_to_system[CHROMA_DB_PATH]`에 잔류시켜, `chroma.py#L34` 재초기화가 `[ChromaDB] Fatal: Self-healing failed: bindings` (`AttributeError: bindings`)로 100% 크래시함을 실증. 또한 Self-Healing이 성공해도 `/api/index/sync`의 `_find_existing_id_or_skip()`이 SQLite `file_mtime`/`file_size`만 검사해 기존 사진을 전량 `skipped` 처리하므로 벡터 검색이 영구 불능화됨.
- **최소 수정 설계**: `chroma.py` 백업 후 재시도 전 `SharedSystemClient.clear_system_cache()`(또는 해당 키 제거) 호출 및 Self-Healing 플래그/Chroma ID 대조를 통해 누락 임베딩 재인덱싱 연결.
- **현재 상태**: 🟡 OPEN

### [DEFECT-10] `GemmaAdapter.generate_caption_and_tags` 예외 은폐로 빈 AI 메타데이터 영구 커밋 및 재인덱싱 스킵
- **심각도**: 🟠 P1 High (`Silent Degradation / Data Loss`) | **실증**: `✅ Empirical Probe Reproduced`
- **위치**: [`backend/app/services/mlx_adapters.py#L145-L166`](../../../backend/app/services/mlx_adapters.py#L145-L166), [`pipeline.py#L53-L66`](../../../backend/app/services/pipeline.py#L53-L66), [`indexing_service.py#L148-L165`](../../../backend/app/services/indexing_service.py#L148-L165)
- **근본 원인 및 증거**: `generate_caption_and_tags()`가 `RuntimeError`/일반 `Exception`을 잡아 캐시 정리 후 `{"caption": "", "tags": [], "aesthetic_tags": []}`를 정상 반환함을 프로브로 실증. 이로 인해 `AIInferenceStep`이 성공 처리되어 SQLite에 빈 캡션/태그와 최신 `file_mtime`/`file_size`가 커밋되고 이후 Sync에서도 영구 스킵됨.
- **최소 수정 설계**: 캐시 복구(`clear_mlx_cache(); gc.collect()`) 후 빈 딕셔너리 반환 대신 예외를 재전파(`raise`)하여 `AIInferenceStep`이 오류로 격리하도록 교정.
- **현재 상태**: 🟡 OPEN

### [DEFECT-11] Tauri IPC `save_binary_file` 무검증 임의 파일 덮어쓰기 및 `csp: null` 보안 경계 결함
- **심각도**: 🟠 P1 High (`Security`) | **실증**: `✅ Deterministic Trace Verified`
- **위치**: [`src-tauri/src/lib.rs#L62-L65`](../../../src-tauri/src/lib.rs#L62-L65), [`src-tauri/src/lib.rs#L82`](../../../src-tauri/src/lib.rs#L82), [`src-tauri/tauri.conf.json#L20-L22`](../../../src-tauri/tauri.conf.json#L20-L22)
- **근본 원인 및 증거**: `save_binary_file(path, data)`가 경로 정규화, 허용 확장자/디렉토리 검증, 네이티브 저장 다이얼로그 연동 검증 없이 `std::fs::write(&path, &data)`를 직접 호출하며, `tauri.conf.json`에 `"csp": null`이 설정되어 WebView 스크립트 취약점 시 OS 임의 파일 덮어쓰기 가능.
- **최소 수정 설계**: 허용 확장자(`.pdf`, `.md`)·`canonicalize()` 경계 검증 또는 Rust 측 네이티브 저장 다이얼로그 결합 및 `tauri.conf.json` CSP 정책 명시.
- **현재 상태**: 🟡 OPEN

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] 기동 시 `chromadb`/`rawpy` 상단 연쇄 임포트 분리 및 Silent Fail(`except: pass`) 제거
- **현재 상태**: 🟢 RESOLVED — `chroma.py` 지연 로딩 및 `base_model.py`/`model_downloader.py` Silent Fail 로깅 보강 완료

