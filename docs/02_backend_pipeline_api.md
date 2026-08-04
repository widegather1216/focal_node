# [Doc 2] 백엔드 파이프라인 및 API / AI 프롬프트 명세

이 문서는 사진 등록(인덱싱), 전처리, AI 추론으로 이어지는 백엔드 파이프라인 흐름과 외부 노출 API, 서비스 계층 구조, 그리고 Gemma 4 E4B-it의 프롬프트 체계를 정의합니다.

---

## 1. Indexing Service 워크플로우

새로운 사진 폴더가 등록되면 `IndexingPipeline` 및 백그라운드 인덱서 서브모듈(`services/indexer/`)을 통해 다음과 같은 순서로 작업이 수행됩니다.

```
[디렉토리 스캔 (scanner.py)] ──> [중복 검사 & 파이프라인] ──> [EXIF 추출 & 썸네일 생성]
                                                                        │
                                                                        ▼
[VectorRepository / SQLite] <── [원자적 커밋 (cleaner.py)] <── [AI 추론 (SigLIP 2 & Gemma 4)]
```

1. **디렉토리 스캔 및 변경 감지 (`services/indexer/scanner.py`):**
   * 사용자가 지정한 폴더 내의 모든 파일을 탐색합니다.
   * 각 파일에 대해 파일 시스템 상의 `mtime`(최종 수정 시간) 및 `file_size`를 SQLite의 `images` 테이블 데이터와 비교합니다.
   * 기존 DB 레코드와 수정 시각 및 파일 크기가 완벽히 일치하는 경우 SHA-256 해시 생성 및 분석 단계를 완전 스킵합니다.
   * 신규 파일이거나 `mtime`/`file_size`가 변경된 파일에 한하여 `calculate_sha256()` 함수로 해시를 생성하고 인덱싱 작업 큐에 등록합니다.
2. **파이프라인 패턴 전처리 (`services/pipeline.py`):**
   * `IndexingPipeline`은 4단계 `PipelineStep`으로 구동됩니다:
     1. `HashStep`: SHA-256 해시값(Primary Key) 계산.
     2. `ThumbnailStep`: 가로 360px JPEG 썸네일 원자적 캐싱.
     3. `EXIFExtractStep`: 카메라/렌즈, 조리개, ISO, 35mm 환산 화각 등 EXIF 파싱.
     4. `AIInferenceStep`: SigLIP 2 임베딩 및 Gemma 4 캡션/태그 추론.
3. **AI 추론 (백그라운드 스레드 분리):**
   * **SigLIP 2**: 준비된 이미지 텐서로부터 768차원 시각 임베딩 벡터 및 Zero-shot 키워드를 추출합니다.
   * **Gemma 4 E4B-it**: VRAM/메모리에 Gemma 4 E4B-it 가중치를 연동하여 감각적인 상세 묘사와 키워드를 추출합니다. 작업 완료 후에도 **60초간 Keep-alive 타이머 버퍼**를 두어 메모리에 대기시킨 뒤 해제합니다.
4. **원자적 커밋 및 보상 트랜잭션 (`services/indexer/cleaner.py` / `repositories/vector_repository.py`):**
   * SQLite 트랜잭션을 수립하고 `images`, `image_metadata`, `ai_analysis` 테이블 데이터 쓰기 준비를 마칩니다.
   * `VectorRepository`를 통해 ChromaDB에 임베딩 및 필터용 메타데이터를 `upsert`합니다.
   * ChromaDB `upsert` 성공 후 SQLite 트랜잭션을 `commit`합니다.
   * 만약 SQLite `commit`이 실패하는 경우, SQLite는 자동 `rollback`되나 ChromaDB는 롤백을 지원하지 않으므로 백엔드 `except` 블록에서 `VectorRepository.delete`를 명시적으로 호출하여 두 데이터베이스 간 동기화를 강제로 보장합니다.

---

## 2. API 엔드포인트 명세 및 서비스 계층

사이드카(Sidecar)로 구동되는 Python FastAPI 서버는 프론트엔드와 루프백 인터페이스를 통해 통신합니다.
유지보수와 확장을 위해 라우터(Router), 서비스(Service), 레포지토리(Repository) 3계층이 완전 캡슐화되어 있습니다.

* **`api/photos.py`**: `/api/photos` 계열 - `PhotoRepository`를 사용한 갤러리 렌더링, 원본/썸네일 스트리밍, 메타데이터 수정 엔드포인트
* **`api/indexing.py`**: `/api/index` 계열 - `services/indexer/status.py` 및 `worker.py`를 활용한 백그라운드 인덱스 조율 엔드포인트
* **`api/folders.py`**: `/api/folders` 계열 - `cleaner.py`를 활용한 스캔 폴더 조회 및 unindex 엔드포인트
* **`api/search.py`**: `/api/search` 계열 - `SearchService` 기반의 하이브리드 검색 및 K-NN 유사도 검색 엔드포인트
* **`api/chat.py`**: `/api/chat` 계열 - `ChatService` 기반의 VLM 사진 비평 생성 및 종합 보고서 요약 엔드포인트

### 2.1. `POST /api/index/start`
* **설명:** 신규 사진 폴더 인덱싱 작업을 작업 큐에 등록하고 인덱싱 프로세스를 시작합니다.
* **Request Body:**
  ```json
  {
    "folder_paths": ["/Users/user/Pictures/2026_Travel"]
  }
  ```
* **Response:** `202 Accepted`

### 2.2. `GET /api/index/status`
* **설명:** 현재 진행 중인 인덱싱 작업의 상태와 진행률을 조회합니다.
* **Response:**
  ```json
  {
    "status": "processing", // idle, processing, paused, cancelled, completed, failed
    "total_files": 1240,
    "processed_files": 312,
    "current_file": "/Users/user/Pictures/2026_Travel/DSC_0124.ARW"
  }
  ```

### 2.3. `POST /api/index/pause`, `POST /api/index/resume`, `POST /api/index/cancel`
* **설명:** 실행 중인 백그라운드 인덱싱 작업을 비동기로 일시정지, 재개 또는 취소합니다.

### 2.4. `GET /api/folders` & `DELETE /api/folders`
* **설명:** 현재 인덱싱된 폴더 목록을 조회하거나 특정 폴더의 모든 사진 레코드 및 ChromaDB 임베딩을 일괄 삭제합니다.

### 2.5. `GET /api/photos`
* **설명:** 갤러리 뷰(가상 스크롤) 렌더링에 필요한 사진 목록을 반환합니다. 페이징 처리를 지원합니다.
* **Query Parameters:** `limit=50`, `offset=0`, `parent_dir=...`

### 2.6. `GET /api/photos/{id}/thumbnail`
* **설명:** 가상 그리드 뷰용 썸네일 이미지(가로 360px)를 반환합니다. (캐시 파일 우선 읽기, 미스 시 동적 생성 및 캐싱)

### 2.7. `GET /api/photos/{id}/original`
* **설명:** 원본 이미지를 스트리밍 반환합니다. RAW 파일은 실시간 sRGB JPEG로 메모리 디코딩 스트리밍됩니다.

### 2.8. `POST /api/search`
* **설명:** `SearchService`를 통해 텍스트 검색 결과와 SigLIP 2 벡터 검색 결과를 가중 합성하고 EXIF 메타데이터 필터를 적용하는 하이브리드 검색을 수행합니다.

### 2.9. `POST /api/search/similar`
* **설명:** `SearchService` 및 `VectorRepository`를 통해 특정 사진의 ChromaDB 저장 임베딩 기반 K-NN 시각 유사도 검색을 수행합니다.

### 2.10. `GET /api/photos/{id}` & `PATCH /api/photos/{id}/metadata`
* **설명:** 특정 사진의 상세 메타데이터를 조회하거나 사용자 편집 캡션/태그를 업데이트합니다.

### 2.11. `POST /api/chat/critique` & `POST /api/chat/critique-summary`
* **설명:** `ChatService`를 통해 VLM(Gemma 4 또는 UniPercept 8B) 모델로 사진 구도/조명 비평을 생성하거나 기존 비평들을 종합 분석한 LLM 요약 보고서를 생성합니다.

---

## 3. Gemma 4 E4B-it 시스템 프롬프트 (System Prompt)

Gemma 4 E4B-it 비전 언어 모델이 이미지로부터 고정밀 메타데이터를 정형화된 JSON 형태로 출력하도록 강제하기 위한 시스템 프롬프트 명세입니다.

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
