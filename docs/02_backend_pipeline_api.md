# [Doc 2] 백엔드 파이프라인 및 API / AI 프롬프트 명세

이 문서는 사진 등록(인덱싱), 전처리, AI 추론으로 이어지는 백엔드 파이프라인 흐름과 외부 노출 API, 그리고 Gemma 4 E4B-it의 프롬프트 체계를 정의합니다.

---

## 1. Indexing Service 워크플로우

새로운 사진 폴더가 등록되면 백그라운드 스레드에서 다음과 같은 순서로 작업이 수행됩니다.

```
[디렉토리 스캔] ──> [중복 검사 및 큐 등록] ──> [EXIF 추출 & RAW 디코딩]
                                                      │
                                                      ▼
[ChromaDB / SQLite] <── [원자적 커밋] <── [AI 추론 (SigLIP 2 & Gemma 2)]
```

1. **디렉토리 스캔 및 변경 감지:**
   * 사용자가 지정한 폴더 내의 모든 파일을 탐색합니다.
   * 각 파일에 대해 파일 시스템 상의 `mtime`(최종 수정 시간) 및 `file_size`를 SQLite의 `images` 테이블 데이터(`file_mtime`, `file_size`)와 먼저 1차 비교합니다.
   * 기존 DB 레코드와 수정 시각 및 파일 크기가 완벽히 일치하는 경우(변경 없음), SHA-256 해시 생성 및 분석 단계를 완전히 스킵합니다.
   * 신규 파일이거나 `mtime`/`file_size`가 변경된 파일에 한하여 SHA-256 해시를 새로 생성하고, 이를 인덱싱 작업 큐(Queue)에 등록합니다.
2. **메타데이터 추출 및 전처리:**
   * 이미지 파일에서 EXIF 메타데이터를 파싱합니다.
   * RAW 포맷(ARW, CR3, NEF 등)의 경우 `rawpy`를 사용해 디코딩 후 sRGB 텐서로 변환합니다.
   * 일반 이미지(JPEG, PNG 등)는 `Pillow`를 통해 리사이징 및 정규화(Normalization)하여 모델 입력용 텐서로 준비합니다.
3. **AI 추론 (백그라운드 스레드 분리):**
   * **SigLIP 2**: 준비된 이미지 텐서로부터 벡터 임베딩을 추출합니다. (메모리 상주)
   * **Gemma 4 E4B-it**: 순차 분석을 위해 VRAM/메모리에 Gemma 4 E4B-it 가중치를 지연 로딩하여 이미지 및 시스템 프롬프트를 입력하여 상세 묘사와 키워드를 추출합니다. 매번 로드하는 지연 시간 오버헤드를 막기 위해, 인덱싱 작업 큐가 빈 후에도 **60초간 Keep-alive 타이머 버퍼**를 두어 메모리에 대기시킨 뒤 해제합니다.
4. **원자적 커밋 및 보상 트랜잭션 (Atomic Commit & Compensation):**
   * SQLite 트랜잭션을 수립하고 `images`, `image_metadata`, `ai_analysis` 테이블 데이터 쓰기 준비를 마칩니다.
   * ChromaDB에 임베딩 및 필터용 메타데이터를 `upsert`합니다.
   * ChromaDB `upsert` 성공 후 SQLite 트랜잭션을 `commit`합니다.
   * 만약 SQLite `commit`이 실패하는 경우, SQLite는 자동 `rollback`되지만 ChromaDB는 롤백을 지원하지 않으므로, 백엔드의 `except` 블록에서 ChromaDB에 방금 삽입한 ID를 명시적으로 삭제(`delete`) 처리하여 두 데이터베이스 간 원자성과 동기화를 강제로 보장합니다.

---

## 2. API 엔드포인트 명세

사이드카(Sidecar)로 구동되는 Python FastAPI 서버는 프론트엔드와 루프백 인터페이스를 통해 통신합니다.
유지보수와 확장을 위해 `main.py`에 모든 코드를 넣지 않고, **라우터(Router)** 및 **스키마(Schema)** 를 모듈화하여 관리합니다.
* **`schemas.py`**: 모든 API 요청/응답에 사용되는 Pydantic 모델 정의
* **`api/photos.py`**: `/api/photos` 계열의 사진 갤러리 렌더링 및 메타데이터 엔드포인트
* **`api/indexing.py`**: `/api/index` 계열의 백그라운드 스캔 스케줄링 엔드포인트
* **`api/folders.py`**: `/api/folders` 계열의 스캔 폴더 관리(조회, 삭제) 엔드포인트
* **`api/chat.py`**: `/api/chat` 계열의 AI 사진 비평 및 챗봇 엔드포인트

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
* **설명:** 현재 진행 중인 인덱싱 작업의 상태와 진행률을 조회합니다. (프론트엔드에서 주기적으로 폴링)
* **Response:**
  ```json
  {
    "status": "processing", // idle, processing, completed, failed
    "total_files": 1240,
    "processed_files": 312,
    "current_file": "/Users/user/Pictures/2026_Travel/DSC_0124.ARW"
  }
  ```

### 2.3. `GET /api/folders` & `DELETE /api/folders`
* **설명:** 현재 인덱싱된 폴더 목록을 조회하거나 특정 폴더의 인덱싱 데이터를 제거합니다.

### 2.4. `GET /api/photos`
* **설명:** 갤러리 뷰(가상 스크롤) 렌더링에 필요한 사진 목록을 반환합니다. 페이징 처리를 지원합니다.
* **Query Parameters:** `limit=50`, `offset=0`, `parent_dir=...`
* **Response:**
  ```json
  [
    {
      "id": "sha256_hash_here",
      "file_name": "DSC_0124.ARW",
      "file_path": "/Users/user/Pictures/2026_Travel/DSC_0124.ARW",
      "capture_date": "2026-07-01T15:30:00",
      "camera_model": "ILCE-7RM5",
      "width": 9504,
      "height": 6336
    }
  ]
  ```

### 2.5. `GET /api/photos/{id}/thumbnail`
* **설명:** 가상 그리드 뷰용으로 빠르게 렌더링할 수 있는 리사이징된 썸네일 이미지를 반환합니다.
* **처리 규칙:** 
  * 인덱싱 시점에 미리 각 이미지의 sRGB 썸네일(JPEG, 가로 360px)을 생성하여 로컬 어플리케이션의 **Thumbnail Cache 디렉토리**에 저장해 둡니다.
  * 요청 수신 시, 캐시 폴더에 썸네일 파일이 존재하면 즉시 파일을 읽어 응답합니다.
  * 만약 캐시 미스(Cache Miss)가 발생한 경우에 한하여 메모리 상에서 RAW 또는 원본 이미지를 `rawpy`/`Pillow`로 실시간 디코딩 및 크기 조절 후 스트리밍하고 캐시 디렉토리에 저장합니다. 이를 통해 스크롤 시의 오버헤드를 원천 방지합니다.

### 2.6. `GET /api/photos/{id}/original`
* **설명:** 라이트박스 및 상세 정보 뷰를 위한 원본 이미지를 스트리밍 서빙합니다.
* **처리 규칙:** 브라우저에서 직접 디코딩 불가능한 RAW 파일 포맷의 경우, 백엔드가 메모리 상에서 sRGB JPEG 또는 WebP로 디코딩 후 스트리밍 반환해야 합니다.

### 2.7. `POST /api/search`
* **설명:** 사용자의 자연어 쿼리와 필터 조건을 결합하여 하이브리드 검색을 수행합니다.
* **Request Body:**
  ```json
  {
    "query": "비 오는 날 카페 통창문",
    "filters": {
      "camera_model": "ILCE-7RM5",
      "iso_min": 100,
      "iso_max": 800,
      "start_date": "2026-01-01T00:00:00",
      "end_date": "2026-12-31T23:59:59"
    },
    "limit": 100
  }
  ```
* **Response:**
  ```json
  [
    {
      "id": "sha256_hash_here",
      "score": 0.842, // 유사도 점수
      "file_path": "/Users/user/Pictures/2026_Travel/DSC_0124.ARW",
      "caption": "비 오는 날 창밖을 바라보며 따뜻한 커피 잔이 놓여 있는 카페 테이블",
      "tags": ["비", "카페", "커피", "창문"],
      "capture_date": "2026-07-01T15:30:00",
      "camera_model": "ILCE-7RM5",
      "width": 9504,
      "height": 6336
    }
  ]
  ```

### 2.8. `GET /api/photos/{id}`
* **설명:** 라이트박스 및 상세 정보 패널 표시를 위한 특정 사진의 상세 메타데이터와 AI 분석 정보를 일괄 조회합니다.
* **Response:**
  ```json
  {
    "id": "sha256_hash_here",
    "file_name": "DSC_0124.ARW",
    "file_path": "/Users/user/Pictures/2026_Travel/DSC_0124.ARW",
    "file_size": 48201044,
    "mime_type": "image/x-sony-arw",
    "metadata": {
      "width": 9504,
      "height": 6336,
      "color_space": "Adobe RGB",
      "camera_model": "ILCE-7RM5",
      "lens_model": "FE 35mm F1.4 GM",
      "f_number": 1.4,
      "shutter_speed": "1/250",
      "iso": 100,
      "capture_date": "2026-07-01T15:30:00"
    },
    "ai_analysis": {
      "caption": "비 오는 날 창밖을 바라보며 따뜻한 커피 잔이 놓여 있는 카페 테이블",
      "tags": ["비", "카페", "커피", "창문"],
      "is_user_edited": false
    }
  }
  ```

### 2.9. `PATCH /api/photos/{id}/metadata`
* **설명:** 사용자가 직접 편집한 상세 정보(캡션, 태그 목록)를 SQLite DB에 즉시 업데이트합니다. 업데이트 완료 시 `is_user_edited` 플래그는 자동으로 `true`로 갱신됩니다.
* **Request Body:**
  ```json
  {
    "caption": "수정된 사진 묘사 캡션 내용",
    "tags": ["수정된키워드1", "수정된키워드2"]
  }
  ```
* **Response:**
  ```json
  {
    "status": "success",
    "id": "sha256_hash_here",
    "ai_analysis": {
      "caption": "수정된 사진 묘사 캡션 내용",
      "tags": ["수정된키워드1", "수정된키워드2"],
      "is_user_edited": true
    }
  }
  ```


### 2.10. `POST /api/chat/critique`
* **설명:** 선택된 단일 사진에 대해 VLM(Gemma 4) 모델을 통한 상세한 AI 비평을 생성합니다.

---

## 3. Gemma 4 E4B-it 시스템 프롬프트 (System Prompt)

Gemma 4 E4B-it 비전 언어 모델이 이미지로부터 고정밀 메타데이터를 정형화된 JSON 형태로 출력하도록 강제하기 위한 시스템 프롬프트 명세입니다.

```
당신은 사진 검색 시스템을 위한 전문 AI 이미지 분석가입니다.

[분석 지침]
1. 객관적 묘사: 사진에서 명확히 보이는 사물, 사람, 배경만 설명하십시오. 이름, 특정 지명, 개인 정보 등 사진만으로 추측할 수 없는 정보는 임의로 상상하여 작성하지 마십시오.
2. 디테일 포착: 사진의 촬영 시간대(낮/밤/일몰 등), 날씨(맑음/비/눈 등), 분위기, 조명 특성을 문장 내에 반드시 포함시키십시오.
3. 태그 추출: 명사 및 형용사 위주로 검색에 실질적 도움을 줄 수 있는 핵심 키워드 5~15개를 선정하십시오.

[출력 형식]
마크다운 기호(예: ```json 등)나 추가적인 텍스트 설명을 절대로 포함하지 마십시오.
오직 아래의 JSON 포맷만 순수하게 출력해야 합니다.

{"caption": "사실적인 1~2줄 묘사", "tags": ["키워드1", "키워드2", "키워드3"]}
```

### 3.1. 방어적 JSON 파싱 유틸리티 (LLM 출력 보정)
* LLM이 프롬프트를 무시하고 마크다운 코드 블록(예: ` ```json ... ``` `)이나 일반 텍스트 설명(예: "분석 결과입니다:")을 혼용하는 예외를 차단합니다.
* 백엔드는 문자열의 첫 번째 `{` 와 마지막 `}` 위치를 찾아내어 내부 내용만 슬라이싱하는 정규식 필터링 작업을 거친 뒤 `json.loads`를 호출해야 합니다.
* 만약 완전한 JSON 해독이 실패할 시, 예외를 캐치하여 전체 백그라운드 인덱싱 파이프라인의 중단을 예방하고 빈 값(`caption=""`, `tags=[]`)으로 대체 삽입을 보장합니다.

