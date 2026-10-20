# 🧪 [02_search_curation] Verification & Ticket Logs

- **검증 상태**: `🩹 Open Issues (Baseline AC 검증 완료 / RRF·스마트앨범 AC 2건 대기 / REFACTOR 1건 대기)`
- **인수 조건 통과율**: `1 / 3 (Baseline 100%)`
- **미해결 티켓**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 1건`

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

### [REFACTOR-01] `SearchService` 모델 미설치 시 SQLite 폴백 방어 및 상세 패널 유사 사진(`similar:`) 버튼 연결
- **심각도**: 🟡 Should Fix (권장 조치)
- **위치**: `backend/app/services/search_service.py#L28-L37`, `src/components/detail/PhotoExifView.tsx`
- **위반 규칙**: Graceful Fallback & UI Feature Wiring
- **발견된 문제**:
  - `SearchService.search_photos`에서 `get_siglip_adapter().get_text_embedding()` 호출 시 예외 방어가 없어, 모델 미설치 상태에서 검색 시 SQLite 텍스트/EXIF 매칭 결과까지 함께 500 에러로 실패함.
  - 백엔드 `POST /api/search/similar` 및 `src/services/api.ts`의 `similar:{photoId}` 라우팅이 구현되어 있으나, 우측 상세 패널 UI에 이를 호출하는 버튼이 누락되어 있음.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - search_service.py에서 SigLIP 2 임베딩 추출 실패 시 경고 로깅 후 text_search_ids + EXIF 필터 결과만 반환하도록 try/except 폴백 적용
  - PhotoExifView.tsx 또는 DetailPanel.tsx 헤더에 setSearchQuery(`similar:${photo.id}`) 트리거 버튼 추가
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)
