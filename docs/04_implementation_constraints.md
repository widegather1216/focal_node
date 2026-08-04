# [Doc 4] 에이전트 구현 제약사항 명세 (Implementation Constraints)

데스크탑 앱 환경에서 발생하기 쉬운 오동작(포트 충돌, DB 데드락, 메모리 누수, UI 프리징, 좀비 프로세스)을 차단하기 위한 필수 구현 규격입니다. 백엔드 및 프론트엔드 개발 시 아래 사항들을 반드시 준수해야 합니다.

---

## 1. FastAPI 동적 포트 할당 및 Tauri 포트 주입

로컬 환경에 이미 설치된 다른 프로그램들과의 포트 충돌 및 동일한 앱이 다중 실행될 때의 사이드카 백엔드 충돌을 차단하기 위한 통신 규칙입니다.

### 1.1. Python 백엔드 규칙
* uvicorn을 사용하여 FastAPI 서버를 구동할 때 `8000` 등 고정 포트를 절대 사용하지 마십시오.
* 포트를 `0`으로 지정하여 OS로부터 유휴 가용 포트를 무작위로 자동 할당받아야 합니다.
* uvicorn 구동 성공 직후, 할당받은 실제 포트 번호를 stdout(표준 출력)으로 특정 포맷팅(`PORT: {port_number}`)을 적용하여 단 한번 출력해야 합니다.
  * 예: `[Sidecar] PORT: 54932`

### 1.2. Tauri (`lib.rs`) 및 프론트엔드 기동 규칙
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
# [구현 코드 지침]
from sqlalchemy import create_engine, event

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()
```

### 2.2. SQLite와 ChromaDB의 데이터 정합성 보장 (보상 트랜잭션)
* ChromaDB는 ACID 트랜잭션 및 롤백이 불가능합니다.
* 인덱싱 파이프라인 및 `cleaner.py` 삭제 로직에서 두 DB 간의 적재 상태를 동기화하기 위해, **ChromaDB upsert를 먼저 시도하고 SQLite commit을 수행**해야 합니다.
* 만약 SQLite `commit` 과정에서 장애가 발생하여 SQLite 트랜잭션이 롤백되는 경우, `except` 블록에서 `VectorRepository.delete`를 통해 ChromaDB에 이미 upsert된 데이터 ID를 수동으로 `delete`하여 동기화 상태를 강제 정비해야 합니다.

```python
# [구현 코드 지침]
try:
    vector_repo.upsert(ids=[image_id], embeddings=[vector], metadatas=[meta])
    db.commit()
except Exception as e:
    db.rollback()
    vector_repo.delete([image_id]) # 보상 트랜잭션
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

---

## 4. CPU-Bound 추론 작업의 이벤트 루프 블로킹 차단

FastAPI는 비동기 싱글 스레드 이벤트 루프를 사용합니다. 이미지 전처리, 디코딩, SigLIP 2 및 Gemma 4 E4B-it 로드와 추론(MLX) 로직은 리소스를 극도로 점유하는 **대표적인 CPU Bound(연산 집약적) 작업**입니다.

### 4.1. 비차단(Non-blocking) 비동기 처리
* 이미지 분석 및 추론 함수를 비동기 루프에서 호출할 때는 반드시 **`asyncio.to_thread()`**를 사용하여 백엔드 내부의 별도 워커(Worker) 스레드 풀에서 동작하도록 격리해야 합니다.

```python
# [구현 코드 지침]
import asyncio

async def index_file_endpoint(file_path: str):
    # 이벤트 루프 차단 없이 스레드 풀에서 무거운 AI 연산 수행
    result = await asyncio.to_thread(worker.index_single_file_sync, file_path)
    return result
```

### 4.2. Gemma 4 및 UniPercept 8B 메모리 관리 규칙
* Gemma 4 E4B-it: **60초간 대기하는 타이머 기반 Keep-alive 전략**을 적용합니다.
* UniPercept 8B: 16GB VRAM 점유를 최소화하기 위해 사진 비평 생성이 완료된 직후 즉시 `UniPerceptAdapter.unload_model()` (`mx.clear_cache()`)을 실행해 메모리를 반환해야 합니다.

### 4.3. 비동기 인덱싱 동시성 세마포어 제약 [NEW]
* 백그라운드 인덱싱 조율 워커(`worker.py`)에서 수천 장의 사진을 비동기 처리할 때, 시스템 메모리/VRAM OOM을 방지하기 위해 **최대 4개 동시 작업 세마포어(`asyncio.Semaphore(4)`)** 제약을 강제합니다.

---

## 5. 프로덕션 패키징 및 백엔드 부팅 속도 최적화 규격

* **PyInstaller 디렉터리 빌드(`--onedir`) 권장:** 부팅 속도 최적화 및 macOS Gatekeeper 서명 검사 간소화를 위해 디렉터리 모드로 패키징합니다.
* **Heavy 모듈 지연 임포트 (Lazy Import):** 백엔드가 유휴 포트를 할당받아 `[Sidecar] PORT: {port}`를 출력할 때까지 Eager Import로 인한 지연을 최소화합니다.

---

## 6. 개발 vs 프로덕션 데이터 환경 격리 및 스키마 마이그레이션 제약

* `config.py`에서 `sys.frozen` 여부에 따라 개발 환경(`~/.config/focal_node_dev`)과 실사용 환경(`~/.config/focal_node`)의 DB/캐시 경로를 엄격히 구분합니다.
* SQLite 스키마 변경 시 기존 사용자 인덱스가 날아가지 않도록 `database.py`의 `run_migrations()`를 통한 Defensive `ALTER TABLE` 구문을 적용합니다.

---

## 7. 백엔드 3계층 아키텍처 및 레포지토리 캡슐화 제약

* **API 라우터 계층 제약:** 라우터(`api/*.py`)에서 ORM 직렬 쿼리나 ChromaDB collection 조작을 직접 수행하지 말고, 반드시 `PhotoRepository`, `VectorRepository`, `SearchService`, `ChatService`에 비즈니스 및 데이터 액세스를 위임해야 합니다.
* **ChromaDB 접근 통일:** ChromaDB 임베딩 조작 시 개별 raw collection 호출을 금지하고 `VectorRepository` 메쏘드를 통해서만 조작하여 캡슐화를 유지해야 합니다.

---

## 8. 사이드카 부모 프로세스 데드락 감시 (Parent Watcher) [NEW]

* Tauri 데스크탑 앱이 사용자에 의해 종료되거나 강제 종료될 때 자식 프로세스로 구동 중인 Python 백엔드가 OS에 좀비 프로세스로 남지 않도록 해야 합니다.
* `utils/process.py`에 `watch_parent` 감시 스레드를 구동하여 부모 프로세스(ppid)의 생존 여부(ppid == 1 인지)를 체크하고, 부모 프로세스 사망 감지 시 Python 프로세스를 `sys.exit(0)`으로 즉시 안전 자진 종료하도록 강제합니다.
