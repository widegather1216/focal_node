# 📚 Focal Node 소스 코드 함수 인벤토리 및 명세서

본 문서는 **Focal Node (AI 기반 로컬 사진 검색 데스크탑 앱)** 의 코드 추상화, 모듈화 및 신규 개발 시 빠르게 코드베이스 구조와 각 모듈/함수의 사양을 파악할 수 있도록 작성된 종합 명세서입니다.

---

## 🏛️ 1. 백엔드 코어 & 레이어드 포트 (Python FastAPI)

### 1.1. Core Abstract Ports (`backend/app/core/ports.py`)
AI 모델 어댑터의 인터페이스 규격을 정의하는 추상 클래스입니다.

| 클래스 / 메서드 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `ImageEmbeddingPort.get_image_embedding` | `image_path: str` | `List[float]` | 이미지 파일 경로를 받아 고차원 시각 임베딩 벡터를 추출합니다. |
| `ImageEmbeddingPort.get_zero_shot_hints` | `image_input: Any, top_k: int = 5` | `List[str]` | 이미지 임베딩 또는 경로를 받아 zero-shot 시각 키워드 후보를 반환합니다. |
| `TextEmbeddingPort.get_text_embedding` | `text: str` | `List[float]` | 자연어 검색 쿼리를 받아 텍스트 임베딩 벡터를 추출합니다. |
| `ImageCaptioningPort.generate_caption_and_tags` | `image_path: str, metadata: dict = None, siglip_hints: list = None` | `Dict[str, Any]` | 이미지 분석 후 `{"caption": str, "tags": list[str], "aesthetic_tags": list[str]}`를 반환합니다. |

---

### 1.2. 프로세스 & 기반 유틸리티 (`backend/app/utils/`)
* **`utils/image.py`**: RAW/Standard 이미지 디코딩 및 EXIF 메타데이터 파싱 유틸리티.
* **`utils/process.py`**: 부모 프로세스 생존 감시 스레드 (`watch_parent`).

| 함수 / 클래스 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `image.is_raw_image` | `file_path: str` | `bool` | 확장자(.arw, .cr3, .nef 등)를 통해 RAW 이미지 여부를 확인합니다. |
| `image.get_mime_type` | `file_path: str` | `str` | 파일 경로 기반으로 정확한 MIME 타입을 반환합니다. |
| `image.decode_raw_to_pil` | `file_path: str` | `PIL.Image.Image` | RAW 파일을 메모리상에서 sRGB PIL Image로 변환합니다. |
| `image.extract_metadata` | `file_path: str` | `dict` | EXIF 태그(카메라/렌즈 모델, F값, 셔터스피드, ISO, 35mm 환산화각 등)를 추출합니다. |
| `process.watch_parent` | 없음 | `None` (Daemon Loop) | 부모 프로세스 종료(ppid=1) 감지 시 백엔드를 자진 종료하여 데드락/좀비 프로세스를 방지합니다. |
| `process.start_parent_watcher` | 없음 | `None` | `watch_parent` 감시 스레드를 데몬 모드로 개시합니다. |

---

### 1.3. 데이터 액세스 계층 (`backend/app/repositories/`)
SQLite ORM과 ChromaDB 벡터 스토리지를 전담 조작하는 레포지토리 모듈입니다.

| 클래스 / 메서드 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `PhotoRepository.get_by_id` | `photo_id: str` | `Optional[Image]` | ID로 단일 사진 메타데이터 객체를 조회합니다. |
| `PhotoRepository.get_by_path` | `file_path: str` | `Optional[Image]` | 원본 파일 경로로 단일 사진 객체를 조회합니다. |
| `PhotoRepository.list_photos` | `limit: int, offset: int, parent_dir: str` | `List[Image]` | 페이지네이션 및 폴더 필터를 적용하여 사진 목록을 최신순 조회합니다. |
| `PhotoRepository.search_by_text` | `query_str: str` | `List[str]` | SQLite `AIAnalysis` 캡션 및 태그에 대해 와일드카드 이스케이프가 적용된 텍스트 검색을 수행합니다. |
| `PhotoRepository.filter_and_paginate` | `photo_ids_from_chroma, filters, offset, limit` | `List[Image]` | 벡터 검색 결과 ID와 EXIF 필터(조리개, ISO, 날짜 범위 등)를 조합하여 최종 페이지네이션합니다. |
| `PhotoRepository.toggle_favorite` | `photo_id: str` | `Optional[Image]` | 해당 사진의 즐겨찾기(`is_favorite`) 상태를 반전 저장합니다. |
| `PhotoRepository.get_gear_analytics` | 없음 | `dict` | 카메라/렌즈 모델, 초당 화각, 35mm 환산 화각, 조리개 통계 데이터를 집계하여 반환합니다. |
| `VectorRepository.count` | 없음 | `int` | ChromaDB에 등록된 임베딩 총 개수를 반환합니다. |
| `VectorRepository.upsert` | `ids, embeddings, metadatas` | `None` | ChromaDB 벡터 스토어에 ID, 임베딩 벡터, 메타데이터를 일괄 등록/업데이트합니다. |
| `VectorRepository.delete` | `ids: List[str]` | `None` | 900개 청크 단위로 안전하게 ChromaDB에서 해당 벡터들을 삭제합니다. |
| `VectorRepository.query_similar_by_embedding` | `query_embedding: List[float], n_results: int` | `List[str]` | 쿼리 벡터 기준 코사인 유사도가 가장 높은 상위 사진 ID 리스트를 반환합니다. |
| `VectorRepository.get_embedding_by_id` | `photo_id: str` | `Optional[List[float]]` | 특정 사진의 ChromaDB 저장 벡터를 가져옵니다. |

---

### 1.4. MLX AI 어댑터 & 다운로더 (`backend/app/services/`)
* **`services/mlx_adapters.py`**: SigLIP 2 및 Gemma 4 VLM 추론 및 60초 Keep-alive VRAM 관리.
* **`services/unipercept_adapter.py`**: UniPercept 8B 비평 전문 모델 추론 및 메모리 즉시 언로드.
* **`services/model_downloader.py`**: Hugging Face 모델 백그라운드 다운로드 모듈.

| 클래스 / 메서드 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `SigLIP2Adapter.get_image_embedding` | `image_path: str` | `list[float]` | SigLIP 2 시각 타워로 이미지 벡터를 추출하고 L2 정규화합니다. |
| `SigLIP2Adapter.get_text_embedding` | `text: str` | `list[float]` | SigLIP 2 텍스트 타워로 텍스트 벡터를 추출하고 L2 정규화합니다. |
| `SigLIP2Adapter.get_zero_shot_hints` | `image_input, top_k=5` | `list[str]` | 이미지 임베딩과 분류 체계를 비교하여 Top-K 시각 후보 키워드를 추출합니다. |
| `GemmaAdapter.generate_caption_and_tags` | `image_path, metadata, siglip_hints` | `dict` | Gemma 4 비전 모델로 캡션, 일반 태그, 미학 태그를 추론합니다. |
| `GemmaAdapter.generate_deep_critique` | `image_path, metadata` | `str` | 사진 구도/조명/색감에 관한 4-bit 퀀타이즈 전문가 비평을 생성합니다. |
| `GemmaAdapter.translate_and_format_critique` | `raw_en: str, quality_score` | `str` | UniPercept의 영문 비평 및 점수를 가공된 한국어 비평 텍스트로 번역합니다. |
| `UniPerceptAdapter.generate_unipercept_critique` | `image_path, metadata` | `dict` | UniPercept 8B VQA 기반 깊이 있는 기술적 비평 및 점수를 추론합니다. |
| `UniPerceptAdapter.unload_model` | 없음 | `None` | UniPercept 모델을 메모리에서 명시적 해제(`mx.clear_cache()`)하여 VRAM을 확보합니다. |
| `model_downloader.download_with_retry` | `repo_id, label, max_retries` | `bool` | OOM 방지 ignore 패턴을 적용하여 HF snapshot을 안전 재시도 다운로드합니다. |
| `model_downloader.start_background_model_downloader` | 없음 | `None` | 모델 백그라운드 다운로드 스레드를 실행합니다. |

---

### 1.5. 모듈화된 인덱서 서브 패키지 (`backend/app/services/indexer/` & `indexing_service.py`)

| 함수 / 클래스 | 위치 (Module) | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- | :--- |
| `indexing_status` | `status.py` | (Global Variable) | `dict` | 백그라운드 인덱싱 진행률(`processed_files`, `total_files`, `status`, `current_file`) 상태. |
| `pause_indexing` / `resume_indexing` / `cancel_indexing` | `status.py` | 없음 | `None` | 백그라운드 인덱싱 큐를 일시정지, 재개 또는 즉시 취소합니다. |
| `calculate_sha256` | `scanner.py` | `file_path: str` | `str` | 8KB 청크 단위로 파일 SHA-256 해시값(Primary Key)을 계산합니다. |
| `scan_directory` | `scanner.py` | `folder_paths: list[str]` | `list[str]` | 지원 확장자(RAW 포함) 이미지들을 재귀 스캔하여 반환합니다. |
| `delete_photo_atomic_sync` | `cleaner.py` | `db, image_id` | `None` | SQLite 및 VectorRepository(ChromaDB)에서 원자적으로 레코드를 삭제합니다. |
| `cleanup_zombie_records` | `cleaner.py` | `db: Session = None` | `None` | 미존재/삭제 폴더 레코드 및 ChromaDB 고아 임베딩을 정제 청소합니다. |
| `remove_folder_data` | `cleaner.py` | `folder_path: str, db: Session = None` | `None` | 지정 폴더와 하위 모든 사진 레코드/벡터를 원자적 일괄 삭제합니다. |
| `run_ai_pipeline_sync` | `worker.py` | `file_path: str` | `tuple[dict, list, dict]` | EXIF, SigLIP 2 임베딩, Gemma 4 캡션을 연속 추론하여 반환합니다. |
| `index_single_file_sync` | `worker.py` | `file_path: str` | `dict \| str` | 해시 검사, IndexingPipeline 실행 및 수정 파일 인플레이스 교체를 수행합니다. |
| `reindex_single_photo_inplace` | `worker.py` | `photo_id: str` | `dict` | 기존 사진의 메타데이터와 AI 캡션/임베딩만 제자리에서 재추론 및 업데이트합니다. |
| `run_indexing_background` | `worker.py` | `folder_paths: list[str]` | `None` (async) | 세마포어(4개) 청크 기반의 비동기 백그라운드 인덱싱 조율 루프를 실행합니다. |
| `indexing_service` | `indexing_service.py` | (Facade) | N/A | 위 `indexer/` 서브모듈의 모든 주요 함수/변수를 re-export하여 100% 역방향 호환을 제공합니다. |

---

### 1.6. 비즈니스 서비스 계층 (`backend/app/services/`)
API 라우터로부터 비즈니스 로직을 분리 캡슐화한 서비스 모듈입니다.

| 클래스 / 메서드 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `SearchService.search_photos` | `request: SearchRequest` | `List[Image]` | 텍스트 검색 결과와 SigLIP 2 벡터 검색 결과를 가중 합성하고 EXIF 필터를 적용합니다. |
| `SearchService.search_similar_photos` | `request: SimilarSearchRequest` | `List[Image]` | 대상 사진의 임베딩을 가져와 ChromaDB K-NN 시각 유사도 검색을 수행합니다. |
| `ChatService.generate_photo_critique` | `payload: CritiqueRequest` | `Dict[str, Any]` | Gemma 또는 UniPercept VLM 선택에 따른 사진 비평 추론 및 DB 저장을 수행합니다. |
| `ChatService.generate_critique_summary` | `payload: CritiqueSummaryRequest` | `Dict[str, Any]` | 축적된 비평 데이터들을 바탕으로 Gemma LLM 종합 요약 보고서를 생성합니다. |
| `photo.generate_and_cache_thumbnail` | `file_path: str, image_id: str` | `bytes` | 가로 360px JPEG 썸네일을 캐시 디렉터리에 원자적 무손실 저장 후 바이트를 반환합니다. |
| `photo.get_original_image_bytes` | `db_image: DBImage` | `tuple[bytes, str]` | RAW 파일은 실시간 sRGB JPEG 디코딩 스트리밍, 일반 이미지는 원본 바이트를 반환합니다. |
| `photo.register_photos_batch_atomic` | `db, batch_data: list[dict]` | `None` | 배치 인덱싱 데이터를 SQLite 및 VectorRepository(ChromaDB)에 일괄 저장합니다. |

---

### 1.7. API 라우터 (`backend/app/api/`)

* **Photos Router (`api/photos.py`)**
  * `get_photos(limit, offset, parent_dir, db)` ➔ `List[PhotoListResponse]`: `PhotoRepository` 기반 갤러리 조회
  * `get_photo_thumbnail(id, db)` ➔ `Response(image/jpeg)`: 캐시 우선 썸네일 스트리밍
  * `get_photo_original(id, db)` ➔ `Response / FileResponse`: RAW 디코딩 / 원본 이미지 스트리밍
  * `get_photo_detail(id, db)` ➔ `PhotoDetailResponse`: 상세 EXIF 및 AI 분석 정보 조회
  * `patch_photo_metadata(id, payload, db)` ➔ `UpdateMetadataResponse`: 캡션 및 태그 수정
  * `export_photos(payload)` ➔ `StreamingResponse(EventStream)`: 선택 사진 복사 내보내기 진행 상황 스트리밍
  * `reindex_photo(id)` ➔ `PhotoDetailResponse`: 단일 사진 AI 재분석
  * `toggle_favorite(id, db)` ➔ `FavoriteToggleResponse`: 즐겨찾기 토글 (`PhotoRepository` 위임)

* **Indexing Router (`api/indexing.py`)**
  * `start_indexing(payload, background_tasks, db)` ➔ `{"message": "Indexing started"}`
  * `sync_database(background_tasks, db)` ➔ `{"message": "Sync started"}`
  * `pause_indexing_endpoint()` / `resume_indexing_endpoint()` / `cancel_indexing_endpoint()` ➔ 조율 제어
  * `get_indexing_status()` ➔ 현재 인덱싱 프로그레스 및 글로벌 상태 반환

* **Search Router (`api/search.py`)**
  * `search_photos(request, db)` ➔ `List[PhotoListResponse]`: `SearchService` 하이브리드 검색 위임
  * `search_similar_photos(request, db)` ➔ `List[PhotoListResponse]`: `SearchService` K-NN 검색 위임

* **Folders Router (`api/folders.py`)**
  * `get_folders(db)` ➔ `List[FolderResponse]`: 인덱싱 등록 폴더 목록 반환
  * `unindex_folder(path, db)` ➔ `dict`: `remove_folder_data`로 폴더 및 관련 데이터 unindex

* **Chat Router (`api/chat.py`)**
  * `get_photo_critique(payload)` ➔ `CritiqueResponse`: `ChatService` VLM 비평 생성 위임
  * `get_all_critiques(db)` ➔ `List[CritiqueItemResponse]`: 비평 목록 조회
  * `delete_photo_critique(photo_id, db)` ➔ 비평 삭제
  * `generate_critique_summary(payload)` ➔ `CritiqueSummaryResponse`: `ChatService` 비평 종합 보고서 생성 위임

* **Analytics Router (`api/analytics.py`)**
  * `get_analytics_stats(db)` ➔ `AnalyticsStatsResponse`: `PhotoRepository.get_gear_analytics` 통계 반환

---

## 🖥️ 2. 데스크탑 프론트엔드 호스트 (Rust Tauri)

### `src-tauri/src/lib.rs` (Tauri App Controller & Sidecar Lifecycle Manager)

| 함수 / 명령 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `get_api_port` | `state: State<Arc<AppState>>` | `Result<u16, String>` (async) | 백엔드 프로세스가 자동 할당받은 uvicorn 동적 포트를 프론트엔드에 전달합니다. |
| `reveal_in_finder` | `path: String` | `Result<(), String>` | OS 파일 탐색기(macOS Finder)에서 해당 파일 위치를 표시합니다. |
| `run` | 없음 | 없음 | Tauri 앱 초기화, Sidecar 기동, 포트 파싱 및 이벤트 브로드캐스트를 구동합니다. |

---

## 🎨 3. 프론트엔드 클라이언트 (React & TypeScript)

### 3.1. API 클라이언트 (`src/services/api.ts`)

| 클래스 / 메서드 | 입력 (Parameters) | 출력 (Return Value) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `healthCheck` | 없음 | `Promise<any>` | 백엔드 헬스 체크 API 호스팅 확인. |
| `fetchPhotos` | `limit, offset, folder` | `Promise<Photo[]>` | 갤러리 그리드용 사진 목록 Fetch. |
| `searchPhotos` | `query, filters, limit, offset` | `Promise<Photo[]>` | 자연어 검색 및 유사도(similar:id) 검색 요청. |
| `getPhotoDetail` | `id: string` | `Promise<PhotoDetail>` | 선택한 사진의 상세 정보 요청. |
| `updatePhotoMetadata` | `id, caption, tags` | `Promise<any>` | 메타데이터 수정 내용 전송. |
| `exportPhotos` | `photoIds, destinationFolder` | `Promise<ExportResult>` | EventSource 스트림으로 사진 내보내기 수행. |
| `fetchFolders` / `removeFolder` | `path?: string` | `Promise<Folder[]>` | 등록된 폴더 목록 조회 및 unindex 요청. |
| `startIndexing` / `syncDatabase`| `folderPaths: string[]` | `Promise<any>` | 인덱싱 개시 및 전체 동기화 요청. |
| `getPhotoCritique` | `photoId: string` | `Promise<{critique: string}>` | 사진 AI 비평 텍스트 요청. |
| `reindexPhoto` | `id: string` | `Promise<PhotoDetail>` | 사진 1장 AI 재분석 요청. |
| `toggleFavorite` | `id: string` | `Promise<{id, is_favorite}>` | 즐겨찾기 상태 변경. |
| `getPhotoThumbnailUrl` | `id: string` | `string` | `http://127.0.0.1:{port}/api/photos/{id}/thumbnail` URL 생성. |
| `getPhotoOriginalUrl` | `id: string` | `string` | `http://127.0.0.1:{port}/api/photos/{id}/original` URL 생성. |

---

### 3.2. 프론트엔드 서브 컴포넌트, 커스텀 훅 및 타입 모듈 (`src/`)

| 컴포넌트 / 훅 / 타입 모듈 | 위치 (Path) | 주요 입력 (Props / Params) | 역할 및 사양 |
| :--- | :--- | :--- | :--- |
| `PhotoCard` | `components/gallery/PhotoCard.tsx` | `photo, isSelected, onSelectPhoto, onToggleSelection, onToggleFavorite` | 갤러리 가상화 그리드의 개별 사진 셀 (체크박스, 하트, 썸네일, hover 배지) |
| `CritiqueSummaryCard` | `components/critique/CritiqueSummaryCard.tsx` | `summaryData, isGeneratingSummary, summaryError, onCopySummary...` | AI 비평 종합 요약 정보 및 토글/복사 모달 카드 |
| `CritiqueCard` | `components/critique/CritiqueCard.tsx` | `item, index, copiedId, onSelectPhoto, onOpenFullscreen...` | 개별 이미지 AI 비평 정보 및 액션 버튼 카드 |
| `FullscreenMetadataOverlay` | `components/fullscreen/FullscreenMetadataOverlay.tsx` | `photo, isVisible` | 뷰어 하단 플로팅 EXIF 메타데이터(카메라, 렌즈, 화각, 조리개, ISO) 패널 |
| `FolderList` | `components/sidebar/FolderList.tsx` | `folders, selectedFolder, onSelectFolder, removeFolder...` | 등록된 인덱싱 폴더 목록 표시 및 추가/삭제 다이얼로그 |
| `IndexingProgressCard` | `components/sidebar/IndexingProgressCard.tsx` | `isIndexing, indexingState, indexingProgress` | 실시간 백그라운드 인덱싱 진행률(%) 및 파일 경로 표시 |
| `AnalyticsKpiGrid` | `components/analytics/AnalyticsKpiGrid.tsx` | `stats` | 총 사진, 사용 카메라, 렌즈 라인업, 최다 조리개 요약 KPI 카드 4종 |
| `GearDonutCharts` | `components/analytics/GearDonutCharts.tsx` | `cameras, lenses, colors, customTooltip` | 카메라 바디 및 렌즈 모델 점유율 도넛 차트 2종 시각화 |
| `ExifBarCharts` | `components/analytics/ExifBarCharts.tsx` | `focal_lengths, focal_lengths_35mm, apertures, customTooltip` | 화각(`use35mmMode` 상태 캡슐화) 및 조리개 사용 분포 막대 차트 2종 시각화 |
| `PhotoAiAnalysisView` | `components/detail/PhotoAiAnalysisView.tsx` | `aiAnalysis, editing, captionEdit, tagsEdit, handleSave...` | AI 캡션/태그/미학 태그 렌더링 및 사용자 편집/저장 폼 |
| `FilterRangeInput` | `components/filter/FilterRangeInput.tsx` | `label, minValue, maxValue, onMinChange, onMaxChange` | 검색 필터의 ISO/조리개/초점거리 Min-Max 숫자 범위 입력 컴포넌트 |
| `AppSplash` | `components/common/AppSplash.tsx` | `backendStatus, backendError, isDownloadingModel` | 앱 초기 구동 시 백엔드 포트 수신 및 환경 준비 대기 화면 |
| `LoadingSpinner` | `components/common/LoadingSpinner.tsx` | `size, color, message, fullScreen` | 공통 로딩 스피너 및 무한 회전 애니메이션 컴포넌트 |
| `useDebounce` | `hooks/useDebounce.ts` | `value: T, delay: number = 500` | 입력값(검색어 등) 500ms 디바운스 처리 범용 커스텀 훅 |
| `useFullscreenControls` | `hooks/useFullscreenControls.ts` | 없음 | 풀스크린 뷰어 단축키(Esc, Arrow, Zoom, Zen), 확대/축소, 이전/다음 탐색 훅 |
| `types/photo.ts` | `types/photo.ts` | N/A | `Photo`, `PhotoMetadata`, `SearchFilters` 타입 정의 모듈 |
| `types/critique.ts` | `types/critique.ts` | N/A | `CritiqueItem`, `CritiqueSummaryResponse` 타입 정의 모듈 |

---

## 🚀 4. 소스 코드 추상화 및 아키텍처 달성 현황

1. **인덱싱 워크플로우 파이프라인 패턴 적용 완료 (`services/pipeline.py`)**
   - Hash ➔ Thumbnail ➔ EXIF ➔ AIInference 4단계 `PipelineStep`으로 추상화 완료.
2. **인덱서 서비스 모듈화 완료 (`services/indexer/`)**
   - 547줄의 monolith 구성을 `status.py`, `scanner.py`, `cleaner.py`, `worker.py`로 SRP 분리 완료.
3. **API Repositories 및 Business Services 계층 완비**
   - Router의 직렬 쿼리와 비즈니스 로직을 `PhotoRepository`, `VectorRepository`, `SearchService`, `ChatService`로 완벽 캡슐화 완료.
4. **프론트엔드 단일 책임 원칙(SRP) 적용 및 리렌더링 최적화 완료 (`src/`)** [NEW]
   - `CritiqueView`, `FullscreenViewer`, `Sidebar`, `AnalyticsView`, `DetailPanel` 등 대형 모놀리식 뷰를 12개 서브 컴포넌트 및 커스텀 훅으로 해체하여 슬림화.
   - `use35mmMode` 상태 캡슐화를 통해 화각 토글 시 전체 페이지 리렌더링 차단 및 `src/types/` 중앙 타입 모듈화 완수.

