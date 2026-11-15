# 🧪 [04_studio_ui_analytics] Verification & Ticket Logs

- **검증 상태**: `🩹 Debugging (Baseline AC 완료 / REFACTOR 1건 대기 / 차트 드릴다운 AC 1건 대기)`
- **인수 조건 통과율**: `2 / 3 (Baseline 100%)`
- **미해결 티켓**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 1건`

---

## 🎯 1. Given-When-Then 인수 조건 (Acceptance Criteria)

### AC 1. 대용량 갤러리 가상 스크롤 및 풀스크린 뷰어 전환 `[As-Is]`
* **Given:** 1,000장 이상의 사진이 로드된 갤러리 뷰에서,
* **When:** 사용자가 고속 스크롤을 수행하거나 사진을 클릭해 우측 상세 패널(`DetailPanel`) 프리뷰를 통해 풀스크린 뷰어를 열면,
* **Then:**
  1. 뷰포트 내 행만 DOM에 마운트되어 프레임 드랍 없이 360px 썸네일이 렌더링되어야 한다.
  2. 풀스크린 진입 시 `/api/photos/{id}/original?raw=true` 스트림이 로드되고 키보드 좌/우 화살표로 이전/다음 사진 이동이 가능해야 한다.

### AC 2. 35mm 환산 화각 및 장비 통계 시각화 `[As-Is]`
* **Given:** 풀프레임 및 크롭(APS-C) 바디로 촬영된 사진들이 인덱싱된 상태에서,
* **When:** 사이드바 `[Insights]` 탭에 진입하여 `[35mm 환산]` / `[실제 초점거리]` 토글을 전환하면,
* **Then:** `focal_lengths_35mm` 또는 `focal_lengths` 기준으로 화각 막대 차트가 즉시 전환되고 카메라/렌즈 도넛 차트가 정확히 렌더링되어야 한다.

### AC 3. 통계 차트 클릭 갤러리 인터랙티브 드릴다운 (`Click-to-Filter`) `[To-Be]`
* **Given:** `[Insights]` 탭의 장비/화각/조리개 차트가 렌더링된 상태에서,
* **When:** 사용자가 특정 카메라/렌즈 도넛 섹션이나 `[35mm 환산]` 모드의 `"35mm"` 화각 막대를 클릭하면,
* **Then:**
  1. `useAppStore.applyAnalyticsDrilldown`이 호출되어 해당 EXIF 조건(`use_35mm_equivalent` 모드 포함)이 `searchFilters`에 즉시 반영되어야 한다.
  2. `activeTab`이 `'gallery'`로 전환되며 해당 조건에 부합하는 사진들만 필터링되어 표시되어야 한다.

---

## 🧪 2. 테스트 시나리오 매트릭스 (Test Matrix)

| 구분 | 테스트 ID | 시나리오 설명 | 입력 / 조작 조건 | 기대 결과 | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Happy** | `TC-UI-01` | 가상 스크롤 갤러리 렌더링 | 1,000장 목록 스크롤 | DOM 노드 최소화 및 360px 캐시 바인딩 | `PASS` |
| **Happy** | `TC-UI-02` | 35mm 환산 통계 토글 | Insights 탭 -> 35mm 토글 | 환산 화각 기준 막대 차트 즉시 갱신 | `PASS` |
| **Boundary**| `TC-UI-03` | 검색/폴더 0개 Empty State | 사진이 없는 상태 | `"일치하는 사진이 없습니다"` Empty State 노출 | `PASS` |
| **Happy** | `TC-UI-04` | 차트 클릭 갤러리 드릴다운 (`[To-Be]`) | Insights 차트에서 `"35mm"` 막대 클릭 | 갤러리 탭 전환 + 35mm 화각 필터 자동 적용 | `⏳ Pending` |

---

## 🚨 3. 결함 리포트 (Defect Logs)

*(현재 등록된 OPEN 결함 없음)*

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `useAppStore.ts` 내 직접 `fetch()` 호출 `api.ts` 일원화, 빈 `catch`/Dead Code 정리 및 `FullscreenViewer.tsx`(433줄) 경량화
- **심각도**: 🟡 Should Fix (권장 조치)
- **위치**: `src/store/useAppStore.ts#L223-L286`, `src/hooks/usePhotosQuery.ts#L5-L27`, `src/components/FullscreenViewer.tsx#L1-L433`, `src/hooks/useFullscreenControls.ts#L17-L35`
- **위반 규칙**: 단방향 레이어 의존성 (`Store ➔ ApiClient`), Rule 4.1 (단일 UI 파일 <= 300줄, 중복 제거), Rule 4.3 (빈 `catch` 금지) & Dead Code 제거
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정/신설 파일**: [`useAppStore.ts`](../../../src/store/useAppStore.ts), [`api.ts`](../../../src/services/api.ts), [`usePhotosQuery.ts`](../../../src/hooks/usePhotosQuery.ts), [`useFullscreenControls.ts`](../../../src/hooks/useFullscreenControls.ts), [`FullscreenViewer.tsx`](../../../src/components/FullscreenViewer.tsx), [`FullscreenToolbar.tsx`](../../../src/components/fullscreen/FullscreenToolbar.tsx), [`FullscreenNavigation.tsx`](../../../src/components/fullscreen/FullscreenNavigation.tsx)
  - **원인 및 조치**:
    - `api.ts`에 `ApiHttpError`(HTTP status 보존)를 추가하고 `parseError`의 비-JSON 폴백 `catch`에 `console.debug` 로깅을 보강했으며, `useAppStore.ts`의 `fetchFolders`/`removeFolder` 직접 `fetch()` 및 빈 `catch`를 `api.fetchFolders()`·`api.removeFolder(path)` 호출(`404` 시 `ApiHttpError` 분기 재동기화 유지)로 일원화함(`cancelActiveCritique`는 선행 작업에서 이미 `api.cancelCritique`로 일원화 완료).
    - `usePhotosQuery.ts`에서 미사용 Dead Code인 `usePhotosQuery` 함수와 미사용 `useQuery` 임포트를 제거하고 `useToggleFavoriteMutation`만 유지함.
    - `useFullscreenControls.ts`의 중복 `getActivePhotoList`(`['critiques']` 키 불일치 포함) 및 `any` 타입을 제거하고 공통 유틸 [`activePhotoList.ts`](../../../src/utils/activePhotoList.ts)의 `getActivePhotoList(queryClient)`로 통합함.
    - `FullscreenViewer.tsx`(433줄)에서 상단 툴바(`FullscreenToolbar.tsx`, 230줄)와 좌/우 네비게이션(`FullscreenNavigation.tsx`, 74줄)을 분리하고 `getFitModeImageStyle` 헬퍼를 추출해 `FullscreenViewer.tsx`를 232줄(<=300줄)로 경량화함.
  - **회귀 테스트 결과**: `npx tsc --noEmit && npm run build` (`PASS`), `./venv/bin/pytest backend/tests/test_api_analytics.py` (`1 passed`)
 
### [REFACTOR-02] API 클라이언트(`api.ts`, 368줄) 및 Analytics/Fullscreen/Gallery 훅·컴포넌트 내 `any` 타입 구체화
- **심각도**: 🟡 Should Fix (권장 조치)
- **위치**: `src/services/api.ts#L29-L358`, `src/hooks/useFullscreenControls.ts#L17,L25,L28,L40,L51`, `src/hooks/usePhotoDetail.ts#L82,L90,L93,L117,L124,L180,L245`, `src/components/analytics/AnalyticsKpiGrid.tsx#L8-L10`, `src/components/analytics/ExifBarCharts.tsx#L6-L9`, `src/components/analytics/GearDonutCharts.tsx#L6-L9`, `src/components/fullscreen/FullscreenMetadataOverlay.tsx#L6`, `src/components/PhotoGallery.tsx#L101,L105`
- **위반 규칙**: Type Safety & Defensive Coding (무분별한 `any` 지양 및 명시적 모델 인터페이스 바인딩)
- **발견된 문제**:
  - `api.ts`(368줄)의 17개 메서드가 `Promise<any>` / `Promise<any[]>`로 정의되어 있어 하위 훅(`usePhotosQuery`, `usePhotoDetail`, `useFullscreenControls`)과 컴포넌트(`AnalyticsKpiGrid`, `PhotoGallery`) 전반으로 `any` 타입 누수가 전파됨.
  - `FullscreenMetadataOverlay.tsx#L6`의 props가 `photo: any`로, `ExifBarCharts`/`GearDonutCharts`의 차트 데이터/툴팁 props가 `any[]`/`React.ComponentType<any>`로 단언되어 컴파일 타임 검증이 무력화됨.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - api.ts 메서드 반환형을 PhotoSummary[], PhotoDetail, FolderResponse[], GearStats 등 구체적 인터페이스로 지정
  - Analytics/Fullscreen/Gallery 컴포넌트 및 훅의 props·캐시 제네릭을 PhotoDetail/GearStatItem/InfiniteData<PhotoSummary[]>로 엄격 바인딩
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)
