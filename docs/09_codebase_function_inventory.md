# 📚 Focal Node 소스 코드 함수 인벤토리 및 명세서

본 문서는 **Focal Node (AI 기반 로컬 사진 검색 데스크탑 앱)** 의 코드 추상화, 리팩토링 및 신규 개발 시 다른 에이전트/개발자가 빠르게 코드베이스 구조와 각 함수의 사양을 파악할 수 있도록 작성된 명세서입니다.

---

## 🏛️ 1. 백엔드 코어 & 레이어드 포트 (Python FastAPI)

### 1.1. Core Abstract Ports (`backend/app/core/ports.py`)
AI 모델 어댑터의 인터페이스 규격을 정의하는 추상 클래스입니다.

| 클래스 / 메서드 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `ImageEmbeddingPort.get_image_embedding` | `image_path: str` | `List[float]` | 이미지 파일 경로를 받아 고차원 시각 임베딩 벡터를 추출합니다. |
| `TextEmbeddingPort.get_text_embedding` | `text: str` | `List[float]` | 자연어 검색 쿼리를 받아 텍스트 임베딩 벡터를 추출합니다. |
| `ImageCaptioningPort.generate_caption_and_tags` | `image_path: str` | `Dict[str, Any]` | 이미지 분석 후 `{"caption": str, "tags": list[str]}` 딕셔너리를 반환합니다. |

---

### 1.2. 이미지 & EXIF 유틸리티 (`backend/app/utils/image.py`)
RAW/Standard 이미지 디코딩 및 EXIF 메타데이터 파싱 유틸리티입니다.

| 함수 / 클래스 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `is_raw_image` | `file_path: str` | `bool` | 확장자(.arw, .cr3, .nef 등)를 통해 RAW 이미지 여부를 확인합니다. |
| `get_mime_type` | `file_path: str` | `str` | 파일 경로 기반으로 정확한 MIME 타입(RAW 커스텀 MIME 포함)을 반환합니다. |
| `decode_raw_to_pil` | `file_path: str` | `PIL.Image.Image` | RAW 파일을 메모리상에서 sRGB PIL Image로 변환합니다. 임베디드 썸네일 우선 추정 fallback을 적용합니다. |
| `extract_metadata` | `file_path: str` | `dict` | EXIF 태그(카메라/렌즈 모델, F값, 셔터스피드, ISO, 촬영일시) 및 이미지 해상도를 추출합니다. |

---

### 1.3. MLX AI 모델 어댑터 (`backend/app/services/mlx_adapters.py`)
SigLIP 2 및 Gemma 4 VLM 모델 추론 및 Keep-alive/메모리 관리를 수행합니다.

| 클래스 / 메서드 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `SigLIP2Adapter.get_image_embedding` | `image_path: str` | `list[float]` | SigLIP 2 모델을 이용해 이미지 벡터를 생성하고 L2 정규화하여 반환합니다. |
| `SigLIP2Adapter.get_text_embedding` | `text: str` | `list[float]` | SigLIP 2 텍스트 타워를 통해 텍스트 벡터를 생성하고 L2 정규화하여 반환합니다. |
| `GemmaAdapter.generate_caption_and_tags` | `image_path: str, metadata: dict = None` | `dict` | Gemma 4 비전 모델로 캡션, 키워드 태그, 전문 구도/조명 태그를 추론하고 JSON으로 반환합니다. |
| `GemmaAdapter.generate_deep_critique` | `image_path: str, metadata: dict = None` | `str` | 사진의 구도, 조명, 색감 및 개선점에 대한 전문가 수준의 비평 텍스트를 생성합니다. |
| `GemmaAdapter._keep_alive_loop` | 없음 (백그라운드 스레드) | None | 비동기 추론 큐가 비어있을 때 60초간 가중치를 유지한 후 메모리(Metal Cache)를 자동 해제합니다. |

---

### 1.4. 사진 처리 서비스 (`backend/app/services/photo.py`)
사진 등록/조회, 원본/썸네일 디코딩 스트리밍 및 원자적 DB 트랜잭션을 처리합니다.

| 함수 / 클래스 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `get_thumbnail_path` | `image_id: str` | `str` | 썸네일 캐시 파일의 절대 경로를 반환합니다. |
| `generate_and_cache_thumbnail` | `file_path: str, image_id: str` | `bytes` | 가로 360px 썸네일 JPEG를 캐시 폴더에 원자적으로 저장하고 바이트를 반환합니다. |
| `get_thumbnail_bytes` | `db_image: DBImage` | `bytes` | 썸네일 캐시를 먼저 읽고, miss 시 실시간 생성하여 반환합니다. |
| `get_original_image_bytes` | `db_image: DBImage` | `tuple[bytes, str]` | RAW 이미지는 실시간 JPEG 변환 스트리밍, 일반 이미지는 원본 바이트와 MIME을 반환합니다. |
| `register_photo_atomic` | `db, image_data, metadata_data, ai_data, embedding` | `DBImage` | 단일 사진을 SQLite 및 ChromaDB에 동시 저장하며 실패 시 보상 트랜잭션을 실행합니다. |
| `register_photos_batch_atomic` | `db, batch_data: list[dict]` | `None` | 배치 사진 데이터를 SQLite 및 ChromaDB에 원자적으로 일괄 저장합니다. |
| `update_photo_metadata` | `db, image_id, caption, tags` | `DBAIAnalysis` | 사용자 편집 캡션 및 태그를 업데이트하고 `is_user_edited=True`로 설정합니다. |

---

### 1.5. 백그라운드 인덱싱 서비스 (`backend/app/services/indexing_service.py`)
폴더 스캔, SHA-256 해시 생성, AI 파이프라인 연동 및 백그라운드 스케줄링을 담당합니다.

| 함수 / 클래스 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `calculate_sha256` | `file_path: str` | `str` | 8KB 청크 단위로 파일의 SHA-256 해시값(Primary Key)을 계산합니다. |
| `scan_directory` | `folder_paths: list[str]` | `list[str]` | 지원하는 표준/RAW 사진 확장자 파일들을 재귀 탐색하여 반환합니다. |
| `index_single_file_sync` | `file_path: str` | `dict \| str` | 파일 해시, EXIF, 썸네일, AI 추론을 실행하고 배치 저장용 데이터 패키지를 구성합니다. |
| `reindex_single_photo_inplace` | `photo_id: str` | `dict` | 기존 사진의 메타데이터와 AI 캡션/임베딩만 제자리(In-place)에서 재분석 및 업데이트합니다. |
| `cleanup_zombie_records` | `db: Session = None` | `None` | 실체 파일이 삭제된 SQLite 잔재 레코드 및 ChromaDB 오판 벡터(Orphan)를 동기화하여 정리합니다. |
| `remove_folder_data` | `folder_path: str` | `None` | 특정 폴더 하위의 모든 사진 레코드 및 ChromaDB 임베딩을 일괄 삭제합니다. |
| `run_indexing_background` | `folder_paths: list[str]` | `None` (async) | 백그라운드 이벤트 루프 차단 없이 세마포어(4개 동시) 청크 기반 인덱싱 루프를 구동합니다. |

---

### 1.6. API 라우터 (`backend/app/api/`)

* **Photos Router (`api/photos.py`)**
  * `get_photos(limit, offset, parent_dir, db)` ➔ `List[PhotoListResponse]`: 사진 목록 페이지네이션 및 폴더 필터 조회
  * `get_photo_thumbnail(id, db)` ➔ `Response(image/jpeg)`: 썸네일 서빙 (Event Loop Non-blocking)
  * `get_photo_original(id, db)` ➔ `Response / FileResponse`: 원본/RAW 스트리밍
  * `get_photo_detail(id, db)` ➔ `PhotoDetailResponse`: 상세 EXIF 및 AI 분석 정보 반환
  * `patch_photo_metadata(id, payload, db)` ➔ `UpdateMetadataResponse`: 캡션 및 태그 수정
  * `export_photos(payload, db)` ➔ `StreamingResponse(EventStream)`: 선택한 사진을 지정 폴더로 내보내기 진행 상황 스트리밍
  * `reindex_photo(id)` ➔ `PhotoDetailResponse`: 단일 사진 AI 재분석 수행
  * `toggle_favorite(id, db)` ➔ `FavoriteToggleResponse`: 즐겨찾기 토글

* **Indexing Router (`api/indexing.py`)**
  * `start_indexing(payload, background_tasks, db)` ➔ `{"message": "Indexing started"}`: 새 폴더 인덱싱 개시
  * `sync_database(background_tasks, db)` ➔ `{"message": "Sync started"}`: 전체 인덱싱 폴더 동기화 개시
  * `get_indexing_status()` ➔ `dict`: 현재 인덱싱 진행률 및 진행 상태 반환

* **Search Router (`api/search.py`)**
  * `search_photos(request, db)` ➔ `List[PhotoListResponse]`: 자연어 키워드/자연어 임베딩 + EXIF 복합 검색
  * `search_similar_photos(request, db)` ➔ `List[PhotoListResponse]`: 특정 사진 기준 시각적 유사도 K-NN 검색

* **Folders Router (`api/folders.py`)**
  * `get_folders(db)` ➔ `List[FolderResponse]`: 인덱싱 등록된 폴더 목록 반환
  * `unindex_folder(path)` ➔ `dict`: 폴더 및 관련 이미지 데이터 일괄 unindex

* **Chat Router (`api/chat.py`)**
  * `get_photo_critique(payload)` ➔ `CritiqueResponse`: VLM 사진 비평 생성

---

## 🖥️ 2. 데스크탑 프론트엔드 호스트 (Rust Tauri)

### `src-tauri/src/lib.rs` (Tauri App Controller & Sidecar Lifecycle Manager)

| 함수 / 명령 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `get_api_port` | `state: State<Arc<AppState>>` | `Result<u16, String>` (async) | 백엔드 프로세스가 자동 할당받은 uvicorn 동적 포트를 프론트엔드에 전달합니다. |
| `reveal_in_finder` | `path: String` | `Result<(), String>` | OS 파일 탐색기(macOS Finder, Windows Explorer)에서 해당 파일 위치를 하이라이트 표시합니다. |
| `run` | 없음 | 없음 | Tauri 데스크탑 앱 초기화, Python Sidecar 기동, stdout/stderr 파싱 이벤트(다운로드/인덱싱 진행률) 브로드캐스트 및 프로세스 라이프사이클을 관리합니다. |

---

## 🎨 3. 프론트엔드 클라이언트 (React & TypeScript)

### 3.1. API 클라이언트 (`src/services/api.ts`)

| 클래스 / 메서드 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `healthCheck` | 없음 | `Promise<any>` | 백엔드 헬스 체크 API 호스팅 확인. |
| `fetchPhotos` | `limit, offset, folder` | `Promise<Photo[]>` | 갤러리 그리드용 사진 목록 페이지네이션 Fetch. |
| `searchPhotos` | `query, filters, limit, offset` | `Promise<Photo[]>` | 자연어 검색 및 유사도(similar:id) 검색 요청. |
| `getPhotoDetail` | `id: string` | `Promise<PhotoDetail>` | 선택한 사진의 상세 정보 요청. |
| `updatePhotoMetadata` | `id, caption, tags` | `Promise<any>` | 메타데이터 수정 내용 전송. |
| `exportPhotos` | `photoIds, destinationFolder` | `Promise<ExportResult>` | EventSource 스트림으로 사진 복사 내보내기 수행. |
| `fetchFolders` / `removeFolder` | `path?: string` | `Promise<Folder[]>` | 등록된 폴더 목록 조회 및 unindex 요청. |
| `startIndexing` / `syncDatabase`| `folderPaths: string[]` | `Promise<any>` | 인덱싱 개시 및 전체 동기화 요청. |
| `getPhotoCritique` | `photoId: string` | `Promise<{critique: string}>` | 사진 AI 비평 텍스트 요청. |
| `reindexPhoto` | `id: string` | `Promise<PhotoDetail>` | 사진 1장 AI 재분석 요청. |
| `toggleFavorite` | `id: string` | `Promise<{id, is_favorite}>` | 즐겨찾기 상태 변경. |
| `getPhotoThumbnailUrl` | `id: string` | `string` | `http://127.0.0.1:{port}/api/photos/{id}/thumbnail` URL 생성. |
| `getPhotoOriginalUrl` | `id: string` | `string` | `http://127.0.0.1:{port}/api/photos/{id}/original` URL 생성. |

---

### 3.2. 상태 관리 스토어 (`src/store/useAppStore.ts`)

| State / Action | 데이터 타입 / 파라미터 | 역할 및 목적 |
| :--- | :--- | :--- |
| `apiPort` | `number \| null` | Rust 백엔드 사이드카 호스트가 주입한 동적 포트 상태. |
| `selectedFolder` | `string \| null` | 현재 선택된 사이드바 폴더 필터. |
| `searchQuery` / `searchFilters` | `string` / `SearchFilters` | 자연어 검색 쿼리 및 EXIF 필터(조리개, ISO, 날짜 범위, 카메라 모델 등). |
| `selectedPhotoId` | `string \| null` | 현재 상세 패널(DetailPanel)에 열린 사진 ID. |
| `selectedPhotoIdsForExport`| `Set<string>` | 다중 선택 내보내기 대상 사진 ID 집합. |
| `isIndexing` / `indexingProgress`| `boolean` / `{processed, total, currentFile}`| 백그라운드 인덱싱 상태 및 프로그레스바 데이터. |
| `modelDownloadProgress` | `{status, progress, modelName}` | AI 모델 다운로드 진행률 메타데이터. |

---

## 🚀 4. 소스 코드 추상화(Abstraction) 방향 제안

1. **AI 추론 인터페이스 분리 (`services/mlx_adapters.py` -> Clean Architecture)**
   - 현재 `mlx_adapters.py`에 PyTorch/MLX 로딩 및 파싱 코드가 결합되어 있습니다.
   - `core/ports.py` 추상 클래스를 완전한 Dependency Injection 구조로 분리하여, 추후 다른 추론 엔진(예: ONNX, TensorRT) 추가 시 어댑터만 교체 가능하도록 설계 변경이 유용합니다.

2. **인덱싱 워크플로우 파이프라인 패턴 적용 (`services/indexing_service.py`)**
   - `index_single_file_sync` 내부의 메타데이터 추출 -> 썸네일 생성 -> AI 분석 -> DB 저장을 **파이프라인 단계(Pipeline Step)** 패턴으로 추상화하면 유지보수성과 에러 격리성이 향상됩니다.

3. **API Repositories 레이어 도입**
   - Router 층에서 SQLAlchemy 쿼리와 ChromaDB 인터랙션이 일부 혼재되어 있습니다. `repositories/photo_repository.py` 형태의 데이터 액세스 레이어로 추상화하는 것을 권장합니다.
