# [Doc 1] 시스템 아키텍처 및 데이터베이스 설계

이 문서는 로컬 사진 검색 데스크탑 애플리케이션의 AI 백엔드 어댑터 패턴 구조와 SQLite 및 ChromaDB 스키마를 정의합니다.

---

## 1. 어댑터 패턴 (Adapter Pattern) 아키텍처

플랫폼별(Mac MLX, Windows ONNX/TensorRT 등) AI 추론 라이브러리의 파편화를 방지하고 확장성을 보장하기 위해 어댑터 패턴을 적용합니다.

```
                  ┌──────────────────────┐
                  │    Core Domain /     │
                  │   Indexing Service   │
                  └──────────┬───────────┘
                             │ (Imports & Calls)
                             ▼
                  ┌──────────────────────┐
                  │   core/ports.py      │ <─── Interface
                  └──────────┬───────────┘
                             │ (Implements)
              ┌──────────────┴──────────────┐
              ▼                             ▼
   ┌────────────────────┐        ┌────────────────────┐
   │ adapters/mlx/      │        │ adapters/onnx/     │ (Future Windows)
   │  - adapter.py      │        │  - adapter.py      │
   │  - image_processor.py       │                    │
   └────────────────────┘        └────────────────────┘
```

### 1.1. 주요 구성 파일
* **`core/ports.py`**: 메인 애플리케이션의 비즈니스 로직(Indexing Service 등)이 호출할 공통 추론 인터페이스 정의.
  * `embed_image(image_tensor: np.ndarray) -> list[float]` (전처리된 sRGB 이미지 텐서를 입력으로 받음)
  * `embed_text(text: str) -> list[float]`
  * `generate_caption(image_tensor: np.ndarray) -> dict` (출력 형식: `{"caption": "...", "tags": [...]}`)
* **`adapters/mlx/adapter.py`**: Apple Silicon (Mac Native) 전용 MLX 구현체.
  * **SigLIP 2**: 잦은 검색 및 임베딩 요청에 빠른 응답을 하기 위해 메모리 상주(Keep-alive) 상태로 유지.
  * **Gemma 4 E4B-it**: 대규모 언어 모델로 메모리 점유율이 높으므로 지연 로딩(Lazy Loading)을 적용합니다. 단, 모델을 로드하는 오버헤드(시간 지연)를 감안해 인덱싱 대기 큐가 비더라도 60초간 모델을 메모리에 유지하는 **Keep-alive 타이머 전략**을 수행한 후 메모리를 OS에 반환합니다.
* **`adapters/mlx/image_processor.py`**: Mac 하드웨어 가속 및 RAW 이미지 전처리 모듈.
  * 고용량 RAW 파일(ARW, CR3, DNG 등) 디코딩.
  * 광색역(Adobe RGB 등) 이미지를 표준 sRGB 색공간으로 정밀 변환 처리.

---

## 2. 데이터베이스 스키마 설계

로컬 파일 메타데이터 및 AI 분석 결과는 SQLite에 저장하고, 유사도 검색을 위한 SigLIP 2 이미지 임베딩 벡터는 ChromaDB에 저장합니다. 두 데이터베이스는 파일의 **SHA-256 해시값**을 Primary Key로 공유하여 동기화됩니다.

ChromaDB는 트랜잭션 및 롤백을 지원하지 않기 때문에, 데이터 정합성을 깨뜨리지 않도록 백엔드에서 **보상 트랜잭션(Compensating Transaction)**을 구현합니다. (SQLite 작업 실패 시 ChromaDB에 방금 upsert된 임베딩 벡터를 삭제 처리)

### 2.1. SQLite (관계형 메타데이터)

동시성 확보를 위해 **WAL(Write-Ahead Logging) 모드**로 운영하며, 외래 키 제약 조건을 활성화합니다.

#### Table 1: `images` (기본 파일 정보)
* `id` (VARCHAR(64), Primary Key): 파일의 SHA-256 해시값
* `parent_dir` (VARCHAR(1024), Indexed): 폴더 단위 탐색 속도 최적화를 위한 부모 폴더 절대 경로
* `file_path` (VARCHAR(1024), Unique): 원본 파일의 절대 경로
* `file_name` (VARCHAR(256)): 확장자를 포함한 파일명
* `file_size` (INTEGER): 파일 크기 (Bytes)
* `file_mtime` (FLOAT): 파일 시스템 상의 최종 수정 시각 (중복 스캔 방지용)
* `mime_type` (VARCHAR(50)): 파일의 MIME 타입 (image/jpeg, image/x-sony-arw 등)
* `is_favorite` (BOOLEAN, Default: False): 즐겨찾기 지정 여부
* `created_at` (DATETIME): DB 레코드 생성 일시
* `updated_at` (DATETIME): DB 레코드 수정 일시

#### Table 2: `image_metadata` (EXIF 하드웨어 데이터)
* `image_id` (VARCHAR(64), Primary Key, Foreign Key): `images.id` 참조, CASCADE ON DELETE
* `width` (INTEGER): 이미지 가로 픽셀 수
* `height` (INTEGER): 이미지 세로 픽셀 수
* `color_space` (VARCHAR(30)): 색공간 (sRGB, AdobeRGB, Display P3 등)
* `camera_model` (VARCHAR(100)): 카메라 제조사 및 모델명
* `lens_model` (VARCHAR(100)): 사용 렌즈 모델명
* `f_number` (FLOAT): 조리개 수치 (F-Stop)
* `focal_length` (FLOAT): 렌즈 화각 (Focal Length)
* `shutter_speed` (VARCHAR(30)): 셔터 스피드 (예: "1/250")
* `iso` (INTEGER): ISO 감도
* `capture_date` (DATETIME, Indexed): 사진 촬영 일시

#### Table 3: `ai_analysis` (AI 생성 맥락 및 사용자 편집 정보)
* `image_id` (VARCHAR(64), Primary Key, Foreign Key): `images.id` 참조, CASCADE ON DELETE
* `caption` (TEXT): Gemma 4 E4B-it가 생성한 상세 사진 묘사 캡션
* `tags` (TEXT): JSON 형태의 키워드 문자열 리스트 (예: `["바다", "하늘", "일몰"]`)
* `aesthetic_tags` (TEXT): 전문가용 구도/조명 관련 톤앤매너 태그 (JSON)
* `is_user_edited` (BOOLEAN, Default: False): 사용자가 직접 캡션이나 태그를 수정했는지 여부. (True인 경우 인덱싱 재수행 시 오버라이트 방지)

#### Table 4: `indexed_folders` (인덱싱 대상 폴더)
* `path` (VARCHAR(1024), Primary Key): 사용자 폴더 절대 경로
* `created_at` (DATETIME): DB 레코드 생성 일시

---

### 2.2. ChromaDB (벡터 데이터)

고속 코사인 유사도 검색을 지원하는 로컬 벡터 데이터베이스 컬렉션입니다.

#### Collection: `photo_embeddings`
* **`ids`**: SQLite `images.id`와 동일한 SHA-256 해시 리스트
* **`embeddings`**: SigLIP 2 모델이 출력한 고차원 실수 벡터 리스트 (예: 768차원 또는 1152차원)
* **`metadatas`**: 사전/사후 하이브리드 필터링을 위한 경량 메타데이터 딕셔너리 (필드명은 SQLite 스펙과 매칭)
  * 예시:
    ```json
    {
      "capture_date": "2026-07-01T15:30:00",
      "iso": 400,
      "camera_model": "ILCE-7RM5",
      "lens_model": "FE 35mm F1.4 GM"
    }
    ```
