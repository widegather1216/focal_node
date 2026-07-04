# [Doc 4] 에이전트 구현 제약사항 명세 (Implementation Constraints)

데스크탑 앱 환경에서 발생하기 쉬운 오동작(포트 충돌, DB 데드락, 메모리 누수, UI 프리징)을 차단하기 위한 필수 구현 규격입니다. 백엔드 및 프론트엔드 연동 시 아래 사항들을 반드시 준수해야 합니다.

---

## 1. FastAPI 동적 포트 할당 및 Tauri 포트 주입

로컬 환경에 이미 설치된 다른 프로그램들과의 포트 충돌 및 동일한 앱이 다중 실행될 때의 사이드카 백엔드 충돌을 차단하기 위한 통신 규칙입니다.

### 1.1. Python 백엔드 규칙
* uvicorn을 사용하여 FastAPI 서버를 구동할 때 `8000` 등 고정 포트를 절대 사용하지 마십시오.
* 포트를 `0`으로 지정하여 OS로부터 유휴 가용 포트를 무작위로 자동 할당받아야 합니다.
* uvicorn 구동 성공 직후, 할당받은 실제 포트 번호를 stdout(표준 출력)으로 특정 포맷팅(`PORT: {port_number}`)을 적용하여 단 한번 출력해야 합니다.
  * 예: `[Sidecar] PORT: 54932`

### 1.2. Tauri (`main.rs`) 및 프론트엔드 기동 규칙
* Sidecar 프로세스를 생성 및 모니터링할 때, 사이드카의 stdout 스트림을 실시간 감시합니다.
* 위 특정 포맷팅(`PORT: {port_number}`)을 정규식 등으로 파싱하여 포트 번호를 동적으로 획득합니다.
* **경쟁 상태(Race Condition) 방지:** Tauri가 백엔드를 구동하는 속도와 프론트엔드 React가 기동되어 첫 API 조회를 날리는 시점 간의 경쟁 상태를 방지해야 합니다. React 앱은 로드 직후 즉시 API를 호출하지 않고, Tauri의 Custom Command인 `invoke("get_api_port")`를 호출하여 백엔드가 정상 기동되어 포트가 반환될 때까지 대기(Await)한 후, 해당 포트 기반으로 Axios/Fetch 클라이언트를 설정 및 첫 조회를 시작하도록 기동 시퀀스를 통제해야 합니다.

---

## 2. 데이터베이스 동시성 보장 (SQLite WAL & FK)

로컬 인덱싱 서비스가 대량의 사진 데이터를 데이터베이스에 Write하는 동안, 사용자는 동시에 갤러리 탐색 및 검색(Read)을 시도합니다. SQLite의 기본 락 메커니즘으로 인한 `database is locked` 오류를 사전에 완벽히 방지해야 합니다.

### 2.1. 설정 지침 (SQLAlchemy)
* SQLAlchemy `create_engine` 실행 직후 엔진의 **연결(connection) 수립 시점(on connect) 리스너**를 바인딩하여 다음 두 가지 PRAGMA 쿼리를 무조건 실행해야 합니다.
  * **`PRAGMA journal_mode=WAL;`**: Write-Ahead Logging 모드를 활성화하여 독자와 기록자 간의 동시성(Lock-free Read)을 전격 보장합니다.
  * **`PRAGMA foreign_keys=ON;`**: SQLite는 기본적으로 외래 키 제약 조건 검사가 비활성화되어 있으므로 수동으로 활성화하여 무결성을 보호합니다.

```python
# [예시 구현]
from sqlalchemy import create_engine, event

engine = create_engine("sqlite:///focal_node.db")

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()
```

### 2.2. SQLite와 ChromaDB의 데이터 정합성 보장 (보상 트랜잭션)
* ChromaDB는 ACID 트랜잭션 및 롤백이 불가능합니다.
* 인덱싱 파이프라인에서 두 DB 간의 적재 상태를 동기화하기 위해, **ChromaDB upsert를 먼저 시도하고 SQLite commit을 수행**해야 합니다.
* 만약 SQLite `commit` 과정에서 장애가 발생하여 SQLite 트랜잭션이 롤백되는 경우, `except` 블록에서 ChromaDB에 이미 upsert된 데이터 ID를 수동으로 `delete`하여 동기화 상태를 강제 정비해야 합니다.

```python
# [예시 구현]
try:
    # 1. SQLite 세션 생성 후 insert문 예약
    # 2. ChromaDB 벡터 upsert
    chroma_collection.upsert(ids=[image_id], embeddings=[vector], metadatas=[meta])
    # 3. SQLite 최종 커밋
    db_session.commit()
except Exception as e:
    db_session.rollback()
    # 보상 트랜잭션: ChromaDB 데이터 삭제
    chroma_collection.delete(ids=[image_id])
    raise e
```

---

## 3. In-Memory RAW 이미지 스트리밍 규칙

고용량 RAW 사진 파일은 수십 MB에서 백여 MB에 달하므로 디스크에 임시 JPG 파일을 복사하거나 생성하면 SSD 수명 갉아먹기 및 불필요한 디스크 I/O 병목이 초래됩니다.

### 3.1. 스트리밍 구현 규칙
* 원본 이미지 서빙 엔드포인트 `/api/photos/{id}/original` 요청 시, 원본 파일이 RAW 포맷인 경우에는 디스크에 어떠한 임시 파일도 작성해선 안 되며, 메모리 상에서 직접 디코딩하여 JPEG/WebP `StreamingResponse`로 반환해야 합니다.
* **썸네일 캐시 예외:** 단, 갤러리 탐색 시 매번 무거운 RAW 파일 디코딩을 시도하면 심각한 CPU 점유와 UI 렉을 유발합니다. 썸네일 엔드포인트 `/api/photos/{id}/thumbnail`은 **정식 썸네일 캐시 디렉토리**를 거쳐야 합니다.
  * 인덱싱 시점에 1회 썸네일을 생성하여 캐시 폴더에 저장하고, 썸네일 조회 시 캐시 폴더에서 파일을 즉시 서빙합니다.
  * 캐시 미스(Cache Miss)가 발생한 경우에 한해, 메모리 상에서 `rawpy`로 원본 RAW를 파싱 후 크기를 줄여 응답하고 동시에 캐시 폴더에 쓰기를 실행합니다.
  * 썸네일 캐시 파일은 지정된 어플리케이션 숨김 캐시 폴더(예: `~/.config/focal_node/cache/`)에만 저장되어 임시 파일 난립을 예방합니다.

---

## 4. CPU-Bound 추론 작업의 이벤트 루프 블로킹 차단

FastAPI는 비동기 싱글 스레드 이벤트 루프를 사용합니다. 이미지 전처리, 디코딩, SigLIP 2 및 Gemma 4 E4B-it 로드와 추론(MLX) 로직은 리소스를 극도로 점유하는 **대표적인 CPU Bound(연산 집약적) 작업**입니다.

### 4.1. 비차단(Non-blocking) 비동기 처리
* FastAPI 엔드포인트(`async def`) 내에서 MLX 추론을 직접 호출하면 이벤트 루프 자체가 통째로 멈추게 되어 다른 모든 HTTP 요청(예: 현재 인덱싱 상태 조회, 썸네일 로딩 등)이 일시정지(Freeze)됩니다.
* 따라서 이미지 분석 서비스(`indexing_service.py`) 등 무거운 연산을 처리하는 함수를 비동기 루프에서 호출할 때는 반드시 **`asyncio.to_thread()`**를 사용하여 백엔드 내부의 별도 워커(Worker) 스레드 풀에서 동작하도록 격리해야 합니다.
* 더 무거운 멀티프로세싱 처리가 필요할 시 `ProcessPoolExecutor`를 활용할 수도 있습니다.

```python
# [예시 구현]
import asyncio

async def handle_inference_endpoint(image_id: str):
    # 이벤트 루프를 차단하지 않고 별도 스레드에서 무거운 AI 연산 수행
    analysis_result = await asyncio.to_thread(run_cpu_heavy_mlx_inference, image_id)
    return analysis_result
```

### 4.2. Gemma 4 E4B-it 모델 Keep-alive 버퍼 관리
* Gemma 4 E4B-it 모델은 용량이 커 로드(RAM/VRAM 적재)하는 데에 수 초의 딜레이가 발생합니다.
* 인덱싱 프로세스 내에서 이미지가 큐에 계속 들어올 때 매번 로드/해제를 반복하지 않도록, 작업이 끝난 후에도 **60초간 대기하는 타이머 기반 Keep-alive 전략**을 적용해야 합니다.
* 타이머가 만료되기 전 새로운 인덱싱 요청이 들어오면 가중치가 로드된 상태에서 즉시 추론을 계속하고, 60초간 무풍 상태(Idle)가 지속될 때만 가중치 데이터를 메모리에서 해제(Garbage Collection 실행)해야 합니다.

