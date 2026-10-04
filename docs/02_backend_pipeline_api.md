# [Doc 2] 백엔드 파이프라인 및 API / AI 프롬프트 명세

이 문서는 사진 등록(인덱싱), 전처리, AI 추론으로 이어지는 백엔드 파이프라인 흐름과 외부 노출 API, 서비스 계층 구조, 그리고 Gemma 4 (12B-it-8bit)의 프롬프트 체계를 정의합니다.

---

## 1. Indexing Service 워크플로우

새로운 사진 폴더가 등록되면 `IndexingPipeline` 및 백그라운드 인덱싱 서비스(`services/indexing_service.py`, `services/indexing_state.py`)를 통해 다음과 같은 순서로 작업이 수행됩니다.

```
[디렉토리 스캔 (scan_directory)] ──> [중복 검사 & 변경 감지] ──> [EXIF 추출 & 썸네일 생성]
                                                                        │
                                                                        ▼
[VectorRepository / SQLite] <── [원자적 보상 트랜잭션] <── [AI 추론 (SigLIP 2 & Gemma 4)]
```

1. **디렉토리 스캔 및 변경 감지 (`services/indexing_service.py`):**
   * 사용자가 지정한 폴더 내의 모든 지원 파일(.jpg, .jpeg, .png, .webp, .arw, .cr2, .cr3, .nef, .dng 등)을 탐색합니다.
   * 각 파일에 대해 파일 시스템 상의 `mtime`(최종 수정 시간) 및 `file_size`를 SQLite의 `images` 테이블 데이터와 비교합니다.
   * 기존 DB 레코드와 수정 시각 및 파일 크기가 완벽히 일치하는 경우 SHA-256 해시 생성 및 분석 단계를 완전 스킵합니다.
   * 신규 파일이거나 `mtime`/`file_size`가 변경된 파일에 한하여 `calculate_sha256()` 함수로 해시를 생성하고 인덱싱 작업 큐에 등록합니다.
2. **파이프라인 패턴 전처리 (`services/pipeline.py`):**
   * `IndexingPipeline`은 4단계 `PipelineStep`으로 구동됩니다:
     1. `HashStep`: SHA-256 해시값(Primary Key) 계산.
     2. `ThumbnailStep`: 가로 360px JPEG 썸네일 원자적 캐싱.
     3. `EXIFExtractStep`: 카메라/렌즈, 조리개, ISO, 35mm 환산 화각 등 EXIF 파싱.
     4. `AIInferenceStep`: SigLIP 2 임베딩 및 Gemma 4 캡션/태그 추론.
3. **AI 추론 (백그라운드 스레드 분리 및 세마포어 제어):**
   * **동시성 제어:** 백그라운드 인덱싱 시 4개 동시 작업 세마포어(`asyncio.Semaphore(4)`), 이미지 디코딩 시 3개 동시 세마포어(`MAX_CONCURRENT_DECODES = 3`)를 통해 VRAM/시스템 메모리 OOM을 차단합니다.
   * **SigLIP 2**: 준비된 이미지 텐서로부터 768차원 시각 임베딩 벡터 및 Zero-shot 키워드를 추출합니다.
   * **Gemma 4 (12B-it-8bit)**: MLX Metal C++ 가속을 통해 감각적인 상세 묘사와 키워드를 추출합니다. 작업 완료 후에도 **60초간 Keep-alive 타이머 버퍼**를 두어 메모리에 대기시킨 뒤 해제합니다.
4. **원자적 커밋 및 보상 트랜잭션 (`services/indexing_service.py` / `repositories/vector_repository.py`):**
   * SQLite 트랜잭션을 수립하고 `images`, `image_metadata`, `ai_analysis` 테이블 데이터 쓰기 준비를 마칩니다.
   * `VectorRepository`를 통해 ChromaDB에 임베딩 및 필터용 메타데이터를 `upsert`합니다.
   * ChromaDB `upsert` 성공 후 SQLite 트랜잭션을 `commit`합니다.
   * 만약 SQLite `commit`이 실패하는 경우, SQLite는 자동 `rollback`되나 ChromaDB는 롤백을 지원하지 않으므로 백엔드 `except` 블록에서 `VectorRepository.delete`를 명시적으로 호출하여 두 데이터베이스 간 동기화를 강제로 보장합니다.

---

## 2. API 엔드포인트 명세 및 서비스 계층

사이드카(Sidecar)로 구동되는 Python FastAPI 서버는 프론트엔드와 루프백 인터페이스를 통해 통신합니다.
유지보수와 확장을 위해 라우터(Router), 서비스(Service), 레포지토리(Repository) 3계층이 완전 캡슐화되어 있습니다.

* **`api/photos.py`**: `/api/photos` 계열 - `PhotoRepository`를 사용한 갤러리 렌더링, 원본/썸네일 스트리밍, 메타데이터 수정, 즐겨찾기 토글, 다중 내보내기, 단일 재인덱싱 엔드포인트
* **`api/indexing.py`**: `/api/index` 계열 - `services/indexing_state.py` 및 `indexing_service.py`를 활용한 백그라운드 인덱스 조율(시작, 일시정지, 재개, 취소, 동기화, 상태) 엔드포인트
* **`api/folders.py`**: `/api/folders` 계열 - 스캔 폴더 조회 및 unindex 엔드포인트
* **`api/search.py`**: `/api/search` 계열 - `SearchService` 기반의 하이브리드 검색 및 K-NN 유사도 검색 엔드포인트
* **`api/chat.py`**: `/api/chat` 계열 - `ChatService` 기반의 VLM 사진 비평 생성, 실시간 상태 조회, 비평 취소, 비평 목록/삭제 및 종합 보고서 요약 엔드포인트
* **`api/analytics.py`**: `/api/analytics` 계열 - `PhotoRepository.get_gear_analytics` 기반의 카메라 바디, 렌즈, 화각, 조리개 통계 집계 엔드포인트
* **`main.py` (시스템 라우트)**: `/api/system/models/*` - Hugging Face 모델 백그라운드 다운로드 상태 조회 및 수동 다운로드 트리거 엔드포인트

### 2.1. 인덱싱 API (`/api/index`)
* **`POST /api/index/start`**: 신규 사진 폴더 인덱싱 작업을 큐에 등록 (`folder_paths` 바디).
* **`POST /api/index/sync`**: 기존 등록된 전체 폴더들의 변경사항(신규/수정/삭제 파일)을 감지하여 동기화.
* **`GET /api/index/status`**: 현재 진행 중인 인덱싱 상태(`status`: idle, processing, paused, cancelled, completed), 진행률 및 처리 중 파일 조회.
* **`POST /api/index/pause`**: 실행 중인 인덱싱 작업 일시정지.
* **`POST /api/index/resume`**: 일시정지된 인덱싱 작업 재개.
* **`POST /api/index/cancel`**: 진행 중인 인덱싱 작업 즉시 취소.

### 2.2. 폴더 관리 API (`/api/folders`)
* **`GET /api/folders`**: 현재 인덱싱된 폴더 목록 조회.
* **`DELETE /api/folders?path=...`**: 특정 폴더의 모든 사진 레코드 및 ChromaDB 임베딩을 일괄 삭제(Unindex).

### 2.3. 사진 갤러리 & 스트리밍 API (`/api/photos`)
* **`GET /api/photos`**: 갤러리 그리드용 사진 목록 반환 (`limit`, `offset`, `parent_dir` 페이징 파라미터 지원).
* **`GET /api/photos/{id}/thumbnail`**: 360px JPEG 썸네일 반환 (캐시 우선 서빙, 미스 시 `MAX_CONCURRENT_DECODES=3` 동적 생성 및 캐싱).
* **`GET /api/photos/{id}/original`**: 원본 이미지 스트리밍 반환 (RAW 파일은 실시간 sRGB JPEG로 메모리 디코딩 스트리밍).
* **`GET /api/photos/{id}`**: 특정 사진의 상세 EXIF 메타데이터 및 AI 분석 결과 반환.
* **`PATCH /api/photos/{id}/metadata`**: 사용자 편집 캡션 및 태그 업데이트 (`is_user_edited=true`).
* **`POST /api/photos/{id}/reindex`**: 단일 사진 강제 재인덱싱.
* **`POST /api/photos/{id}/favorite`**: 즐겨찾기(`is_favorite`) 상태 토글.
* **`POST /api/photos/export`**: 선택된 다중 사진 목록 지정 폴더 복사 및 SSE 진행률 스트리밍.

### 2.4. 시맨틱 & 유사도 검색 API (`/api/search`)
* **`POST /api/search`**: `SearchService` 기반 텍스트 자연어 검색 + SigLIP 2 벡터 검색 가중 합성 및 다차원 EXIF 메타데이터 필터링 하이브리드 검색.
* **`POST /api/search/similar`**: `VectorRepository` 저장 임베딩 기반 K-NN 시각 톤앤매너 유사도 검색.

### 2.5. 장비 통계 인사이트 API (`/api/analytics`)
* **`GET /api/analytics/stats`**: 카메라 바디 점유율, 렌즈 사용 분포, 실효 화각, 35mm 환산 화각 분포, 조리개(F수치) 통계 집계 데이터 반환.

### 2.6. AI 사진 비평 & 리포트 API (`/api/chat`)
* **`POST /api/chat/critique`**: VLM(UniPercept 8B 또는 Gemma 4) 기반 심층 구도/조명/색감 비평 생성.
* **`GET /api/chat/critique/status/{photo_id}`**: 비평 생성 진행 상태(단계, 진행률, 메시지) 실시간 조회.
* **`POST /api/chat/critique/cancel/{photo_id}`**: 진행 중인 비평 생성 작업을 안전하게 취소하고 모델 메모리 반환.
* **`GET /api/chat/critiques`**: 비평이 생성된 모든 사진 목록 최신순 조회.
* **`DELETE /api/chat/critique/{photo_id}`**: 저장된 사진 비평 삭제.
* **`POST /api/chat/critique-summary`**: 다중 사진 비평 결과를 종합 분석한 LLM 큐레이션 요약 보고서 생성.

### 2.7. AI 모델 다운로드 관리 API (`/api/system/models`)
* **`GET /api/system/models/status`**: SigLIP 2, Gemma 4, UniPercept 모델별 다운로드 바이트/진행률/상태 및 전체 진행률 조회.
* **`POST /api/system/models/download`**: 백그라운드 모델 다운로더 강제/수동 재시작 트리거.

---

## 3. Gemma 4 (12B-it-8bit) 시스템 프롬프트 (System Prompt)

Gemma 4 (12B-it-8bit) 비전 언어 모델이 이미지로부터 고정밀 메타데이터를 정형화된 JSON 형태로 출력하도록 강제하기 위한 시스템 프롬프트 명세입니다.

```
당신은 사진의 분위기, 빛의 결, 찰나의 순간을 깊이 있게 읽어내는 감성 사진 도슨트이자 자연어 검색 메타데이터 전문가입니다. 사진 속 시각적 사실과 분위기를 조화롭게 조합하여 사진가의 감성을 깨우는 묘사를 작성해야 합니다.

[분석 및 묘사 지침]
1. 분위기 및 정서 추론 (Reasoning): 사진의 피사체, 빛의 온도와 방향, 구도, 카메라 세팅(EXIF)이 연출하는 전반적인 공기감과 서사적 맥락을 파악하여 'reasoning' 필드에 1~2문장으로 요약하십시오.
2. 감각적이고 서정적인 캡션 (Caption): 수사 보고서 같은 건조하고 딱딱한 기술(예: '~가 배치되어 있음', '~을 확인할 수 있음')은 절대 금지합니다. 실제 존재하는 핵심 피사체(인물, 물체, 장소 등)를 반드시 명시하되, 그 피사체가 담긴 빛의 성질, 계절감, 색감, 정서(예: 포근한, 쓸쓸한, 활기찬, 따스한)를 어우러지게 담아 1~2문장의 감각적이고 완결성 있는 한국어 문장으로 작성하십시오. 이미지를 보지 않아도 장면의 빛깔과 분위기가 감성적으로 그려져야 합니다.
3. 일반 태그 (Tags): 사진 검색에 유용한 핵심 명사(피사체, 장소, 사물)와 함께 사진의 감각/분위기를 나타내는 형용사 및 감성 키워드(예: 해질녘, 서정적인, 아늑함, 흩날리는 눈, 질감 등)를 조화롭게 7~15개 선정하십시오.
4. 전문 태그 (Aesthetic Tags): 분류 체계(구도/앵글, 조명/빛, 기법/효과, 톤/무드)를 참고하여 사진에 명확히 해당하는 미학 용어 3~8개를 선정하십시오.
5. SigLIP 2 시각 교차 검증 (Cross-Verification): [SigLIP 2 시각 벡터 매칭 후보 키워드]를 검증하여 타당한 시각 요소는 캡션 및 태그에 반영하고 오탐 키워드는 제외하십시오.
6. 예외 규칙 (Negative Prompting):
   - 지나치게 추상적이거나 허구적인 시적 미사여구로 피사체 사실 정보를 완전히 가리지 마십시오.
   - EXIF 조리개 F5.6 이상 시 '아웃포커싱'/'보케' 남발 금지.
   - 셔터스피드 1/1000s 보다 빠르면 '장노출'/'모션 블러' 사용 금지.
   - 사진에 명확히 보이지 않는 정보(특정 지명, 인물 이름) 추측 금지.

[출력 형식]
마크다운 기호(예: ```json 등)나 추가적인 텍스트 설명을 절대로 포함하지 마십시오.
오직 아래의 JSON 포맷만 순수하게 출력해야 합니다.

{"reasoning": "추론 내용", "caption": "감각적 캡션 묘사", "tags": ["키워드1", "키워드2"], "aesthetic_tags": ["전문용어1", "전문용어2"]}
```
