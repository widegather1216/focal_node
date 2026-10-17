# 🧪 [00_core_foundation] Verification & Ticket Logs

- **검증 상태**: `🩹 Open Issues (AC 검증 완료 / REFACTOR 1건 대기)`
- **인수 조건 통과율**: `2 / 2 (100%)`
- **미해결 티켓**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 1건`

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
| **Negative**| `TC-CF-03` | 모델 미다운로드 상태 기동 | 로컬 HF 캐시 미존재 | `ModelDownloadModal` 노출 및 진행률 표시 | `PASS` |

---

## 🚨 3. 결함 리포트 (Defect Logs)

*(현재 등록된 OPEN 결함 없음)*

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] 기동 시 `chromadb`/`rawpy` 상단 연쇄 임포트 분리 및 Silent Fail(`except: pass`) 제거
- **심각도**: 🟡 Should Fix (권장 조치)
- **위치**: `backend/app/main.py#L42`, `backend/app/chroma.py#L5`, `backend/app/services/base_model.py#L81-L88`, `backend/app/services/model_downloader.py#L39-L40,L167-L168,L235-L251`
- **위반 규칙**: Rule 2.5 (Heavy 모듈 지연 임포트) & Rule 4.3 (예외 묵인 `except: pass` 금지)
- **발견된 문제**:
  - `main.py` 상단에서 `api.photos` ➔ `services.photo` ➔ `repositories.vector_repository` ➔ `chroma.py`가 연쇄 임포트되면서 `[Sidecar] PORT: {port}` 출력 전에 `chromadb`, `rawpy`, `PIL`, `exifread`가 Eager Import됨.
  - `base_model.py` 및 `model_downloader.py` 내 다수의 `except Exception: pass` 블록이 예외 원인을 완전히 삼키고 있음.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - chroma.py의 import chromadb를 get_chroma_client() 함수 내부로 지연 이동
  - base_model.py 및 model_downloader.py의 빈 except 블록에 최소 디버그/경고 로깅 추가
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)
