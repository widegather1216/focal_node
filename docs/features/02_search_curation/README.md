# 🔍 [02_search_curation] Hybrid Search, K-NN Curation & Smart Albums

- **현재 상태 (Lifecycle)**: `🩹 Debugging (DEFECT-01~08 해결 완료 — DEFECT-09~10 해결 대기)`
- **구현 진척도**: `[□□□□] 0/4 Steps (Active Iteration)`
- **미해결 티켓 현황**: `🚨 DEFECT: 2건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

SigLIP 2 자연어 시맨틱 검색(코사인 거리 임계값 절삭)과 SQLite 캡션/태그/`aesthetic_tags` 텍스트 매칭을 **RRF(Reciprocal Rank Fusion)**로 결합하고, EXIF(카메라, 렌즈, 조리개, ISO, 35mm 환산/물리 초점거리, 날짜) 및 AI 비평 점수 조건으로 교집합 필터링하는 하이브리드 검색, K-NN 무드 유사 사진 추천 및 **스마트 앨범(Smart Albums)** 프리셋을 담당합니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### ✅ Current Baseline (As-Is 기구현 완료)
- [x] SigLIP 2 텍스트-이미지 코사인 유사도 + SQLite 캡션/태그 및 EXIF 교집합 하이브리드 검색
  - 📂 구현: [`search.py`](../../../backend/app/api/search.py), [`search_service.py`](../../../backend/app/services/search_service.py) | 🧪 테스트: [`test_api_search.py`](../../../backend/tests/test_api_search.py) (`PASS`)
- [x] K-NN 시각 임베딩 기반 유사 톤앤매너 레퍼런스 추천 (`POST /api/search/similar`)
  - 📂 구현: [`search.py`](../../../backend/app/api/search.py), [`search_service.py`](../../../backend/app/services/search_service.py) | 🧪 테스트: [`test_api_search.py`](../../../backend/tests/test_api_search.py) (`PASS`)
- [x] 프론트엔드 500ms 디바운스 검색바 및 다중 범위 수치 입력/날짜 필터 메뉴
  - 📂 구현: [`SearchFilterMenu.tsx`](../../../src/components/SearchFilterMenu.tsx), [`FilterRangeInput.tsx`](../../../src/components/filter/FilterRangeInput.tsx), [`useDebounce.ts`](../../../src/hooks/useDebounce.ts)

### 🚀 Active Iteration: RRF 하이브리드 랭킹 고도화, 35mm 환산/점수 필터 & M4. 스마트 앨범 `[To-Be]`
- [ ] **Step 1 [DB & Types]**: `models.py`에 `SmartAlbum` 테이블 추가, `schemas.py` 및 `src/types/photo.ts`의 `SearchFilter`에 `use_35mm_equivalent: bool = True`, `min_overall_score`, `min_iaa_score` 추가 및 `SmartAlbum` 스키마/인터페이스 정의
- [ ] **Step 2 [Repo & API]**: `VectorRepository.query_similar_by_embedding`에 코사인 거리 임계값(`max_distance=0.88`) 컷오프 추가, `PhotoRepository`에 `aesthetic_tags` 검색 포함·`COALESCE(focal_length_35mm, focal_length)` 화각 필터·스마트 앨범 CRUD 및 `backend/app/api/smart_albums.py` 라우터 생성
- [ ] **Step 3 [Service & State]**: `SearchService`에 **RRF($k=60$) 가중 랭킹 결합** 및 SigLIP 미설치 폴백 적용, `useAppStore.ts`에 `smartAlbums`, `activeSmartAlbumId`, `applySmartAlbum()` 액션 추가
- [ ] **Step 4 [UI & Integration]**: `SearchFilterMenu.tsx`에 35mm 환산 화각 토글·최소 비평 점수 필터·`[+ 스마트 앨범 저장]` 모달 추가 및 `Sidebar.tsx`에 스마트 앨범 원클릭 필터 목록 렌더링

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **Recent Commits (2026-11-18)**:
  - `64202b1` - `fix(search): chunk large candidate filters, validate pagination, escape EXIF ILIKE, and format 422 details`
  - `1fb8c3c` - `docs(search): mark DEFECT-07 resolved and sync control tower`
  - `aa99020` - `fix(search): guard SigLIP taxonomy precomputation and device transfers with GPU_LOCK`
- **Working Tree State**: 🟢 Clean (`DEFECT-08` 커밋 완료)
- **직전 완료 작업**: `2026-11-18 / systematic-debugger / DEFECT-08 (PhotoRepository 900청크 분할 조회 및 list_critiques 청크 정렬, SearchRequest/SimilarSearchRequest limit/offset 422 검증 및 repository 가드, _escape_like_pattern·_normalize_text_filter 적용·filter_and_paginate nullslast+Image.id 정렬 교정, apiError.ts Pydantic 422 배열 detail 직렬화 분리) 해결 및 회귀 검증 완료`
- **생성/수정된 핵심 파일**:
  - `backend/app/repositories/photo_repository.py`: `_escape_like_pattern`, `_normalize_text_filter`, `_query_chunk_matching_ids`, `_collect_matching_candidate_ids`, `_sort_critique_rows`, `_fetch_critique_rows_chunked` 도입 및 `filter_and_paginate` `nullslast(), models.Image.id` tie-breaker 교정
  - `backend/app/schemas.py`: `SearchRequest`, `SimilarSearchRequest` `limit` (`ge=1, le=500`)·`offset` (`ge=0`) `Field` 검증 추가
  - `src/utils/apiError.ts` & `src/services/api.ts`: `formatApiErrorDetail`·`extractResponseErrorMessage` 분리 및 `ApiClient.parseError` 연동
  - `backend/tests/test_api_search.py` & `tests/frontend/apiError.test.mjs`: `TC-SRC-15` 백엔드 4종(35k ID·`list_critiques` 35k·음수/초과 422·`ILIKE` 이스케이프/공백/동시각·NULL 정렬) 및 프론트엔드 `parseError` 422 단위 테스트 3종 추가
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_api_search.py -v` (`16 passed`)
  - `./venv/bin/pytest backend/tests/ -q` (`189 passed`)
  - `node --test tests/frontend/*.test.mjs` (`31 passed`)
  - `npx tsc --noEmit && npm run build` (`PASS`)
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - 미해결 티켓 `DEFECT-09~10`(다음 타깃: `P1 High` `DEFECT-09` `SearchService.search_similar_photos` 빈 벡터 인덱스 `200 OK []` 위장) 순차 해결 후 Active Iteration Step 1 착수. Step 2 구현 시 `VectorRepository.query_similar_by_embedding`에서 `include=["distances"]`로 거리를 조회하여 `d <= max_distance`인 후보만 반환하도록 수정할 것.
