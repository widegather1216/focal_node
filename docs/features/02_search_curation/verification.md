# 🧪 [02_search_curation] Verification & Ticket Logs

- **검증 상태**: `🩹 Debugging (DEFECT-01~03 해결 완료 — DEFECT-04~10 해결 대기)`
- **인수 조건 통과율**: `1 / 3 (Baseline 100%)`
- **미해결 티켓**: `🚨 DEFECT: 7건` | `🧐 REFACTOR: 0건`

---

## 🎯 1. Given-When-Then 인수 조건 (Acceptance Criteria)

### AC 1. 시맨틱 자연어 + EXIF 하이브리드 검색 `[As-Is]`
* **Given:** 사진 라이브러리 인덱싱이 완료된 상태에서,
* **When:** 검색창에 "비 내리는 밤거리"를 입력하고 조리개 필터를 `F1.4 ~ F2.0`으로 설정하여 검색하면,
* **Then:** SigLIP 2 시각 임베딩 유사도와 SQLite `image_metadata.f_number` 조건이 교집합으로 필터링되어 랭킹 순으로 반환되어야 한다.

### AC 2. 코사인 거리 임계값 절삭, RRF 랭킹 및 35mm 환산·비평 점수 필터 `[To-Be]`
* **Given:** 풀프레임 및 APS-C 크롭 바디 사진과 AI 비평 점수가 저장된 라이브러리에서,
* **When:** 라이브러리에 전혀 없는 주제어를 검색하거나, `35mm 환산 화각 = 35mm` 및 `최소 미학 점수(IAA) >= 85` 필터를 적용하면,
* **Then:**
  1. 코사인 거리 임계값(`d > 0.88`)을 초과하는 무관한 사진은 절삭되어 빈 결과(`[]`)를 반환해야 한다.
  2. `caption`, `tags`, `aesthetic_tags` 일치 후보와 벡터 유사 후보가 RRF($k=60$) 점수로 통합 정렬되어야 한다.
  3. 크롭 바디(예: 물리 23mm, 35mm 환산 35mm) 사진도 `COALESCE(focal_length_35mm, focal_length)` 조건에 의해 정확히 검색되어야 한다.

### AC 3. 스마트 앨범 저장 및 원클릭 복원 `[To-Be]`
* **Given:** 사용자가 검색어 또는 최소 1개 이상의 EXIF/점수 필터를 적용한 상태에서,
* **When:** `[+ 스마트 앨범으로 저장]`을 눌러 이름을 입력하고 저장하면,
* **Then:**
  1. `POST /api/smart-albums`를 통해 SQLite `smart_albums` 테이블에 영구 저장되어야 한다.
  2. 사이드바 'Smart Albums' 목록에 즉시 표시되며, 클릭 시 저장된 검색어와 필터가 복원되어 갤러리가 갱신되어야 한다.

---

## 🧪 2. 테스트 시나리오 매트릭스 (Test Matrix)

| 구분 | 테스트 ID | 시나리오 설명 | 입력 / 조작 조건 | 기대 결과 | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Happy** | `TC-SRC-01` | 자연어 + EXIF 하이브리드 검색 | "노을 바다" + ISO 100~400 | 유사도 및 EXIF 일치 사진 반환 | `PASS` |
| **Happy** | `TC-SRC-02` | K-NN 유사 사진 추천 API | `POST /api/search/similar` (`similar:{id}`) 요청 | 자기 자신 제외 코사인 유사 사진 리스트 반환 | `PASS` |
| **Happy** | `TC-SRC-03` | 스마트 앨범 저장 및 적용 (`[To-Be]`) | 복합 필터 적용 후 앨범 저장/클릭 | 사이드바 등록 및 원클릭 필터 복원 | `⏳ Pending` |
| **Boundary**| `TC-SRC-04` | 공백/초과 이름 스마트 앨범 (`[To-Be]`) | 공백 문자열 또는 101자 이름 입력 | HTTP 422 반환 및 토스트 경고 | `⏳ Pending` |
| **Negative**| `TC-SRC-05` | 조건 없는 빈 스마트 앨범 저장 (`[To-Be]`) | 검색어와 필터 모두 비운 채 요청 | UI 버튼 비활성화 및 백엔드 422 방어 | `⏳ Pending` |
| **Boundary**| `TC-SRC-06` | 무관한 검색어 거리 임계값 절삭 (`[To-Be]`) | 존재하지 않는 피사체 검색 (`d > 0.88`) | 무관한 하위 사진 절삭 및 빈 목록 반환 | `⏳ Pending` |
| **Happy** | `TC-SRC-07` | 35mm 환산 화각 & 비평 점수 필터 (`[To-Be]`) | APS-C 23mm(환산 35mm) + IAA>=85 필터 | 크롭 바디 35mm 환산 사진 포함 반환 | `⏳ Pending` |
| **Boundary**| `TC-SRC-08` | SigLIP 2 >64토큰 검색어 트런케이션 (`DEFECT-01`) | 64토큰 초과 한국어/영문 자연어 검색 | `ValueError` 없이 임베딩 추출 및 정상 검색 | `PASS (Fixed in DEFECT-01)` |
| **Boundary**| `TC-SRC-09` | 비ASCII(한글) 태그 `ensure_ascii=False` 검색 (`DEFECT-02`) | 한글 태그 저장/수정 후 SQLite 폴백 검색 | `\uXXXX` 이스케이프 없이 한글 태그 정상 매칭 | `PASS (Fixed in DEFECT-02)` |
| **Boundary**| `TC-SRC-10` | `date_to` 날짜 문자열 종료일 전체 포함 (`DEFECT-03`) | `date_from=2025-11-18`, `date_to=2025-11-18` + `14:30` 촬영 | 종료일 `23:59:59`까지 당일 사진 포함 반환 | `PASS (Fixed in DEFECT-03)` |
| **Happy** | `TC-SRC-11` | 검색/필터/`similar:` 시 `selectedFolder` 스코프 유지 (`DEFECT-04`) | 특정 폴더 선택 후 검색어/필터/유사사진 실행 | 선택한 폴더(및 하위) 내부 사진만 반환 | `FAIL (DEFECT-04)` |
| **Boundary**| `TC-SRC-12` | 즐겨찾기 필터 해제 시 `undefined` 잔존 키 제거 (`DEFECT-05`) | 하트 필터 ON ➔ OFF 토글 후 배지/목록 확인 | 배지 소멸 및 `fetchPhotos(..., selectedFolder)` 복귀 | `FAIL (DEFECT-05)` |
| **Boundary**| `TC-SRC-13` | `PhotoGallery` 조건부 마운트 `ResizeObserver` 재결합 (`DEFECT-06`) | 초기 로딩/빈 결과 후 그리드 마운트 및 리사이즈 | `columnCount` 반응형 갱신 정상 동작 | `FAIL (DEFECT-06)` |
| **Boundary**| `TC-SRC-14` | `SigLIP2Adapter` taxonomy 사전계산 `GPU_LOCK`/`self.lock` 보호 (`DEFECT-07`) | `_precompute_taxonomy_embeddings()` 동시 호출 | `.to(device)` 및 캐시가 락 경계 내에서만 실행 | `FAIL (DEFECT-07)` |
| **Boundary**| `TC-SRC-15` | 32,766 변수 초과·음수 `limit`/`offset`·`ILIKE` 이스케이프·정렬 tie-breaker (`DEFECT-08`) | 35k ID 필터, `limit=-1`, `Z6_2` 검색, 동시각 연사 | SQL 오류/전량 누출/와일드카드 누출/페이지 역전 차단 | `FAIL (DEFECT-08)` |
| **Negative**| `TC-SRC-16` | `search_similar_photos` 빈 벡터 인덱스 `404` 일관성 (`DEFECT-09`) | `vector_count == 0` 상태에서 `POST /api/search/similar` | `200 OK []` 위장 없이 `404` 반환 | `FAIL (DEFECT-09)` |
| **Boundary**| `TC-SRC-17` | `SearchService` 스레드 세션 격리 및 `AbortSignal` 전달 (`DEFECT-10`) | `to_thread` 취소 경합 및 빠른 검색어 전환 | `Session` 크로스 스레드 `close()` 경합 차단 및 fetch 취소 | `FAIL (DEFECT-10)` |

---

## 🚨 3. 결함 리포트 (Defect Logs)

### [DEFECT-01] `SigLIP2Adapter` 64토큰 초과 검색어 `ValueError` 크래시 및 시맨틱 검색 전면 무력화
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정 파일**: [`siglip_adapter.py`](../../../backend/app/services/siglip_adapter.py#L9-L136), [`test_siglip_zero_shot.py`](../../../backend/tests/test_siglip_zero_shot.py#L99-L136), [`test_api_search.py`](../../../backend/tests/test_api_search.py#L165-L216)
  - **원인 및 조치**: `SiglipProcessor`의 `tokenizer.model_max_length`가 `10^30`인 반면 `text_config.max_position_embeddings`가 `64`여서 64토큰 초과 질의 시 시퀀스 길이 초과 `ValueError`가 발생하고 `SearchService`가 `None` 폴백으로 벡터 검색이 무력화되는 결함 및 `get_zero_shot_hints`의 `if not image_emb:` `np.ndarray` 불리언 평가 결함을 확인함. `SIGLIP_TEXT_MAX_LENGTH = 64` 상수 및 모델 `text_config.max_position_embeddings` 연동 `_resolve_text_max_length()`를 신설해 `get_text_embedding`과 `_precompute_taxonomy_embeddings`의 `self.processor(..., padding="max_length", truncation=True, max_length=max_length, return_tensors="pt")`에 트런케이션을 적용하고, `get_zero_shot_hints`를 `if image_emb is None or len(image_emb) == 0:` 안전 가드로 교정함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_api_search.py backend/tests/test_siglip_zero_shot.py -v` (`11 passed`), `./venv/bin/pytest backend/tests/ -q` (`175 passed`)

### [DEFECT-02] `tags`/`aesthetic_tags` `ensure_ascii=True` 직렬화로 인한 한글 태그 SQLite 검색 및 SigLIP 폴백 불능
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정 파일**: [`photo.py`](../../../backend/app/services/photo.py#L186-L194), [`photo_repository.py`](../../../backend/app/repositories/photo_repository.py#L220-L235), [`photo_reindex.py`](../../../backend/app/services/photo_reindex.py#L57-L66), [`database.py`](../../../backend/app/database.py#L77-L88), [`test_api_search.py`](../../../backend/tests/test_api_search.py#L228-L348)
  - **원인 및 조치**: `_prepare_photo_models`, `PhotoRepository.update_caption_and_tags`, `_update_ai_analysis_orm`에서 `json.dumps(...)` 기본 `ensure_ascii=True`로 `tags`/`aesthetic_tags`를 직렬화해 `["바다", "노을"]`이 `'["\\ubc14\\ub2e4", "\\ub178\\uc744"]'`로 저장되면서 `AIAnalysis.tags.ilike('%바다%')`가 0건을 반환하던 결함을 확인함. `backend/app/` 내 태그/미학태그 JSON 직렬화 전수 경로에 `ensure_ascii=False`를 적용(`_parse_json_list` 및 `to_detail_dict` 호환 100% 유지)하고, `database.py` `run_migrations()`에 [`_normalize_escaped_ai_tags`](../../../backend/app/database.py#L198-L253) 비파괴 백필을 추가해 기존 SQLite `\uXXXX` 데이터를 UTF-8 JSON으로 정규화하며 잘못된 JSON은 수정 없이 경고 로깅 후 안전 스킵하도록 조치함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_api_search.py -v` (`8 passed`), `./venv/bin/pytest backend/tests/ -q` (`177 passed`)

### [DEFECT-03] `date_to` 날짜 필터 자정(`00:00:00`) 절삭으로 종료일 당일 촬영 사진 전량 누락
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정 파일**: [`schemas.py`](../../../backend/app/schemas.py#L9-L125), [`photo_repository.py`](../../../backend/app/repositories/photo_repository.py#L14-L23), [`photo_repository.py`](../../../backend/app/repositories/photo_repository.py#L153-L155), [`test_api_search.py`](../../../backend/tests/test_api_search.py#L353-L430)
  - **원인 및 조치**: `<input type="date">`의 `"YYYY-MM-DD"` 입력 또는 `datetime.date` 값이 Pydantic `datetime` 파싱 시 `datetime(Y, M, D, 0, 0, 0)`으로 변환되어 `capture_date <= date_to` 비교에서 당일 `00:00:01~23:59:59.999999` 촬영 사진이 누락되던 결함을 확인함. `schemas.py`에 `normalize_date_filter_bound()` 및 `SearchFilter` `field_validator(mode="before" / "after")`를 도입해 `"YYYY-MM-DD"` 문자열과 `datetime`이 아닌 `datetime.date`만 `date_from`=`00:00:00`·`date_to`=`23:59:59.999999`로 확장하고, 명시적 타임스탬프(`"2025-11-18T00:00:00"`, `"2025-11-18T12:00:00"`)는 정확한 시각 경계를 보존하며 `Z`/timezone-aware ISO 문자열(`"2024-12-31T23:59:59Z"`)은 `tzinfo=None` 정규화로 SQLite naive `capture_date` 비교와 호환되도록 교정함. 또한 `PhotoRepository._apply_exif_filters`에 `_resolve_date_filter_bound()`를 연동해 `SearchFilter`를 거치지 않는 직접 호출자도 동일 경계 규칙을 따르도록 보강함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_api_search.py -v` (`10 passed`), `./venv/bin/pytest backend/tests/ -q` (`179 passed`), `npx tsc --noEmit` (`PASS`)

### [DEFECT-04] 검색·EXIF 필터·`similar:` 활성 시 `selectedFolder` 컨텍스트 전면 소실
- **현재 상태**: 🟡 OPEN (`🟠 P1 High`)
- **발생 위치**: [`PhotoGallery.tsx`](../../../src/components/PhotoGallery.tsx#L55-L65), [`api.ts`](../../../src/services/api.ts#L94-L133), [`schemas.py`](../../../backend/app/schemas.py#L90-L100), [`photo_repository.py`](../../../backend/app/repositories/photo_repository.py#L166-L204)
- **원인 및 재현**: `hasQuery || hasFilters` 분기 시 `selectedFolder`가 API 및 백엔드 `SearchRequest`/`SimilarSearchRequest`/`filter_and_paginate`로 전달되지 않아 폴더 선택 상태에서도 전체 라이브러리를 검색함.

### [DEFECT-05] 즐겨찾기 필터 해제 시 `{ is_favorite: undefined }` 잔존 키로 인한 유령 배지(`1`) 및 폴더 스코프 붕괴
- **현재 상태**: 🟡 OPEN (`🟠 P1 High`)
- **발생 위치**: [`SidebarSearchControls.tsx`](../../../src/components/sidebar/SidebarSearchControls.tsx#L55-L61), [`SearchFilterMenu.tsx`](../../../src/components/SearchFilterMenu.tsx#L34), [`PhotoGallery.tsx`](../../../src/components/PhotoGallery.tsx#L58)
- **원인 및 재현**: 즐겨찾기 필터 OFF 시 `is_favorite: undefined` 키를 객체에 남겨 `Object.keys().length === 1`이 유지되어 배지 `1` 표시 및 `api.searchPhotos` 경로 고정 발생.

### [DEFECT-06] `PhotoGallery` 조건부 마운트 `parentRef`에 대한 `useEffect(..., [])` `ResizeObserver` 영구 미등록
- **현재 상태**: 🟡 OPEN (`🟠 P1 High`)
- **발생 위치**: [`PhotoGallery.tsx`](../../../src/components/PhotoGallery.tsx#L29-L46), [`PhotoGallery.tsx`](../../../src/components/PhotoGallery.tsx#L109-L189)
- **원인 및 재현**: 최초 마운트(`status === 'pending'`) 및 빈 결과 시 `<div ref={parentRef}>`가 미렌더링되어 `parentRef.current === null` 상태에서 `useEffect(..., [])`가 조기 반환하고 이후 재마운트 시 `ResizeObserver`가 영구 미등록됨.

### [DEFECT-07] `SigLIP2Adapter._precompute_taxonomy_embeddings()`의 `GPU_LOCK` 경계 밖 MPS 텐서 전송 및 락 경합
- **현재 상태**: 🟡 OPEN (`🟠 P1 High`)
- **발생 위치**: [`siglip_adapter.py`](../../../backend/app/services/siglip_adapter.py#L44-L72)
- **원인 및 재현**: `_precompute_taxonomy_embeddings()` 62행에서 `.to(self.device)`를 `GPU_LOCK` 밖에서 호출하고 `self.lock` 없이 `cached_taxonomy_embeddings`를 초기화하여 MPS 동시 충돌 위험 존재.

### [DEFECT-08] `PhotoRepository` 32,766 변수 초과 크래시, 음수 `limit`/`offset`, `ILIKE` 미이스케이프·정렬 누락 및 `parseError` 422 직렬화 결함
- **현재 상태**: 🟡 OPEN (`🟠 P1 High`)
- **발생 위치**: [`photo_repository.py`](../../../backend/app/repositories/photo_repository.py#L114-L204), [`schemas.py`](../../../backend/app/schemas.py#L90-L100), [`api.ts`](../../../src/services/api.ts#L62-L73)
- **원인 및 재현**: `_build_chroma_id_filter` 35k ID 시 `too many SQL variables` 크래시, `SearchRequest`/`SimilarSearchRequest` 음수 `limit=-1` 시 SQLite 전량 반환, `camera_model`/`lens_model` `_`/`%` 미이스케이프, `L203` `Image.id` 2차 정렬 누락, `parseError` 배열 `detail` `"[object Object]"` 반환.

### [DEFECT-09] `SearchService.search_similar_photos` 빈 벡터 인덱스(`vector_count == 0`) 시 `200 OK []` 거짓 성공 위장
- **현재 상태**: 🟡 OPEN (`🟠 P1 High`)
- **발생 위치**: [`search_service.py`](../../../backend/app/services/search_service.py#L86-L97)
- **원인 및 재현**: `vector_count > 0`일 때 임베딩 미존재는 `ValueError(404)`를 발생시키지만 `vector_count == 0`일 때는 `return []`(`200 OK`)으로 조기 반환해 임베딩 누락을 정상 빈 결과로 은폐함.

### [DEFECT-10] `SearchService` 취소 시 스레드 간 `Session` 동시 `close()` 경합 및 `PhotoGallery` `AbortSignal` 미전달
- **현재 상태**: 🟡 OPEN (`🟠 P1 High`)
- **발생 위치**: [`search.py`](../../../backend/app/api/search.py#L13-L48), [`search_service.py`](../../../backend/app/services/search_service.py#L14-L111), [`PhotoGallery.tsx`](../../../src/components/PhotoGallery.tsx#L56-L65), [`api.ts`](../../../src/services/api.ts#L81-L133)
- **원인 및 재현**: `Depends(get_db)` 세션을 `asyncio.to_thread` 워커와 공유해 태스크 취소 시 `AsyncExitStack` `close()`와 워커 쿼리가 경합하며, 프론트엔드 `queryFn`이 `signal`을 전달하지 않아 이전 검색 HTTP 요청이 중단되지 않음.

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `SearchService` 모델 미설치 시 SQLite 폴백 방어, `search.py` 표준 로깅 전환 및 상세 패널 유사 사진(`similar:`) 버튼 연결
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정 파일**: [`search_service.py`](../../../backend/app/services/search_service.py#L20-L115), [`search.py`](../../../backend/app/api/search.py#L1-L48), [`useAppStore.ts`](../../../src/store/useAppStore.ts#L119-L124), [`PhotoGallery.tsx`](../../../src/components/PhotoGallery.tsx#L21-L26), [`DetailPanel.tsx`](../../../src/components/DetailPanel.tsx#L148-L167), [`test_api_search.py`](../../../backend/tests/test_api_search.py#L1-L157)
  - **원인 및 조치**: `SearchService`에서 임베딩 추출(`_extract_query_embedding_sync`), 검색 한도 계산(`_compute_search_limit`), 벡터 질의(`_query_vector_ids`), 후보 결합(`_resolve_query_candidate_ids`)을 SRP 헬퍼로 분리해 모든 메서드를 `<=26줄`·`중첩<=2`로 경량화하고, SigLIP 2 미설치/로딩/추론 예외 시 `logger.warning` 기록 후 500 에러 없이 SQLite `text_search_ids` + EXIF 결과로 정상 폴백(`200 OK`)하도록 교정함. `search.py`의 `traceback.print_exc()`를 `logger.exception(...)`으로 전환하고, `useAppStore.findSimilarPhotos` 원자적 액션(`similar:${photo.id}` 설정 + 필터 초기화 + `'gallery'` 탭 전환 + 패널 닫기)·`PhotoGallery` `similar:` 즉시 디바운스 우회 및 `DetailPanel` `[유사한 무드 사진 찾기]` 버튼을 연결함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_api_search.py backend/tests/test_concurrency_hardening.py -v` (`15 passed`), `./venv/bin/pytest backend/tests/ -q` (`154 passed`), `npx tsc --noEmit && npm run build` (`PASS`)
