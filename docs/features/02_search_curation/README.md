# 🔍 [02_search_curation] Hybrid Search, K-NN Curation & Smart Albums

- **현재 상태 (Lifecycle)**: `🩹 Debugging (DEFECT-01~04 해결 완료 — DEFECT-05~10 해결 대기)`
- **구현 진척도**: `[□□□□] 0/4 Steps (Active Iteration)`
- **미해결 티켓 현황**: `🚨 DEFECT: 6건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
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
  - `f4c4ab4` - `fix(search): preserve selectedFolder parent_dir scope across search and similar queries`
  - `f66d1d9` - `docs(search): mark DEFECT-03 resolved and sync control tower`
  - `dd0731a` - `fix(search): expand date-only date_to filter to end of day`
- **Working Tree State**: 🟢 Clean (`DEFECT-04` 커밋 완료)
- **직전 완료 작업**: `2026-11-18 / systematic-debugger / DEFECT-04 (검색·EXIF 필터·similar: 활성 시 selectedFolder 스코프 유지, NFD/NFC·리프 심볼릭 링크·형제 접두어 차단 및 후보 풀 조기 절단 해소) 해결 및 회귀 검증 완료`
- **생성/수정된 핵심 파일**:
  - `src/components/PhotoGallery.tsx` & `src/services/api.ts`: `selectedFolder`를 `searchPhotos(..., folder)` 및 `/api/search`, `/api/search/similar`의 `parent_dir`로 전달(`postJson` 헬퍼 분리)
  - `backend/app/schemas.py`: `SearchRequest`, `SimilarSearchRequest`에 `parent_dir: Optional[str] = None` 추가
  - `backend/app/services/search_service.py`: `parent_dir` 활성 시 Chroma 후보 풀 확장(`_compute_search_limit`)·`search_by_text(..., limit=None)` 기아 방지 및 `filter_and_paginate(..., parent_dir=request.parent_dir)` 연동
  - `backend/app/repositories/photo_repository.py`: `_resolve_folder_bounds`, `_paginate_ordered_folder_query`, `_filter_candidate_ids` 도입으로 `_list_photos_in_folder`와 동일한 `utils/path.py` 폴더 경계·공백/음수 슬라이스 가드 공유
  - `backend/tests/test_api_search.py`: `TC-SRC-11` 폴더 스코프(자연어·EXIF·필터 단독·`similar:`), NFD/NFC·리프 심볼릭 링크·형제 접두어·>500 텍스트 풀·공백/음수 경계 회귀 테스트 2종 추가
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_api_search.py -v` (`12 passed`)
  - `./venv/bin/pytest backend/tests/ -q` (`181 passed`)
  - `npx tsc --noEmit && npm run build` (`PASS`)
  - `node --test tests/frontend/*.test.mjs` (`19 passed`)
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - 미해결 티켓 `DEFECT-05~10`(다음 타깃: `P1 High` `DEFECT-05` 즐겨찾기 필터 해제 시 `{ is_favorite: undefined }` 잔존 키 제거) 순차 해결 후 Active Iteration Step 1 착수. Step 2 구현 시 `VectorRepository.query_similar_by_embedding`에서 `include=["distances"]`로 거리를 조회하여 `d <= max_distance`인 후보만 반환하도록 수정할 것.
