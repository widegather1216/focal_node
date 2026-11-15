# 🧪 [02_search_curation] Verification & Ticket Logs

- **검증 상태**: `🛠️ Implementing (Baseline 및 REFACTOR-01 완료 / RRF·스마트앨범 AC 2건 대기)`
- **인수 조건 통과율**: `1 / 3 (Baseline 100%)`
- **미해결 티켓**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 0건`

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

---

## 🚨 3. 결함 리포트 (Defect Logs)

*(현재 등록된 OPEN 결함 없음)*

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `SearchService` 모델 미설치 시 SQLite 폴백 방어, `search.py` 표준 로깅 전환 및 상세 패널 유사 사진(`similar:`) 버튼 연결
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정 파일**: [`search_service.py`](../../../backend/app/services/search_service.py#L20-L115), [`search.py`](../../../backend/app/api/search.py#L1-L48), [`useAppStore.ts`](../../../src/store/useAppStore.ts#L119-L124), [`PhotoGallery.tsx`](../../../src/components/PhotoGallery.tsx#L21-L26), [`DetailPanel.tsx`](../../../src/components/DetailPanel.tsx#L148-L167), [`test_api_search.py`](../../../backend/tests/test_api_search.py#L1-L157)
  - **원인 및 조치**: `SearchService`에서 임베딩 추출(`_extract_query_embedding_sync`), 검색 한도 계산(`_compute_search_limit`), 벡터 질의(`_query_vector_ids`), 후보 결합(`_resolve_query_candidate_ids`)을 SRP 헬퍼로 분리해 모든 메서드를 `<=26줄`·`중첩<=2`로 경량화하고, SigLIP 2 미설치/로딩/추론 예외 시 `logger.warning` 기록 후 500 에러 없이 SQLite `text_search_ids` + EXIF 결과로 정상 폴백(`200 OK`)하도록 교정함. `search.py`의 `traceback.print_exc()`를 `logger.exception(...)`으로 전환하고, `useAppStore.findSimilarPhotos` 원자적 액션(`similar:${photo.id}` 설정 + 필터 초기화 + `'gallery'` 탭 전환 + 패널 닫기)·`PhotoGallery` `similar:` 즉시 디바운스 우회 및 `DetailPanel` `[유사한 무드 사진 찾기]` 버튼을 연결함.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_api_search.py backend/tests/test_concurrency_hardening.py -v` (`15 passed`), `./venv/bin/pytest backend/tests/ -q` (`154 passed`), `npx tsc --noEmit && npm run build` (`PASS`)
