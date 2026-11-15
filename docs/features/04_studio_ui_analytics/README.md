# 📊 [04_studio_ui_analytics] Studio UI, Design System & Gear Analytics

- **현재 상태 (Lifecycle)**: `🛠️ Implementing (Baseline 완료 / REFACTOR-01~02 해결 / 통계 차트 드릴다운 Step 3~4 대기)`
- **구현 진척도**: `[■■□□] 2/4 Steps (Active Iteration)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

가상 스크롤(`@tanstack/react-virtual`) 기반 갤러리, 풀스크린 뷰어, 우측 딥다이브 패널, 다크 스튜디오 CSS 변수 디자인 시스템 및 35mm 환산 장비 통계 대시보드(차트 클릭 갤러리 드릴다운 포함)를 담당하는 도메인입니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### ✅ Current Baseline (As-Is 기구현 완료)
- [x] 뉴트럴 다크룸 CSS 변수(`--bg-canvas: #09090b`, `--accent-focal: #e11d48`) 및 EXIF/날짜 포맷터 정의
  - 📂 구현: [`App.css`](../../../src/App.css), [`exif.ts`](../../../src/utils/exif.ts), [`formatters.ts`](../../../src/utils/formatters.ts)
- [x] 카메라/렌즈 점유율 및 물리/35mm 환산 화각/조리개 분포 집계 API(`/api/analytics/stats`)
  - 📂 구현: [`analytics.py`](../../../backend/app/api/analytics.py), [`photo_repository.py`](../../../backend/app/repositories/photo_repository.py), [`useAnalyticsQuery.ts`](../../../src/hooks/useAnalyticsQuery.ts) | 🧪 테스트: [`test_api_analytics.py`](../../../backend/tests/test_api_analytics.py) (`PASS`)
- [x] 탭/선택/풀스크린 Zustand 전역 스토어 및 풀스크린 줌/패닝/단축키 제어 훅
  - 📂 구현: [`useAppStore.ts`](../../../src/store/useAppStore.ts), [`useFullscreenControls.ts`](../../../src/hooks/useFullscreenControls.ts), [`usePhotosQuery.ts`](../../../src/hooks/usePhotosQuery.ts)
- [x] `@tanstack/react-virtual` 갤러리 그리드, 우측 상세 패널, 풀스크린 뷰어 및 Recharts 도넛/바 차트
  - 📂 구현: [`PhotoGallery.tsx`](../../../src/components/PhotoGallery.tsx), [`PhotoCard.tsx`](../../../src/components/gallery/PhotoCard.tsx), [`DetailPanel.tsx`](../../../src/components/DetailPanel.tsx), [`FullscreenViewer.tsx`](../../../src/components/FullscreenViewer.tsx), [`FullscreenToolbar.tsx`](../../../src/components/fullscreen/FullscreenToolbar.tsx), [`FullscreenNavigation.tsx`](../../../src/components/fullscreen/FullscreenNavigation.tsx), [`AnalyticsView.tsx`](../../../src/components/AnalyticsView.tsx), [`ExifBarCharts.tsx`](../../../src/components/analytics/ExifBarCharts.tsx)

### 🚀 Active Iteration: 통계 차트 인터랙티브 드릴다운 (Click-to-Filter) `[To-Be]`
- [x] **Step 1 [DB & Types]**: `[N/A - 02_search_curation의 SearchFilters.use_35mm_equivalent 확장 공유]`
- [x] **Step 2 [Repo & API]**: `[N/A - 백엔드 /api/analytics/stats 추가 변경 없음]`
- [ ] **Step 3 [Service & State]**: `useAppStore.ts`에 차트 항목 클릭 시 기존 필터를 초기화하고 선택된 장비/화각(`use_35mm_equivalent` 연동)/조리개 필터를 세팅한 뒤 `activeTab = 'gallery'`로 즉시 전환하는 `applyAnalyticsDrilldown(partialFilter)` 액션 추가
- [ ] **Step 4 [UI & Integration]**: `GearDonutCharts.tsx`(카메라/렌즈 섹션 클릭) 및 `ExifBarCharts.tsx`(물리/35mm 화각 및 조리개 막대 클릭)에 포인터 커서·호버 툴팁 안내 및 드릴다운 핸들러 연결

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-11-15 / systematic-debugger / 04_studio_ui_analytics REFACTOR-02 해결 완료` (`bd92eb6`, `c095184`)
- **생성/수정된 핵심 파일**:
  - `src/types/analytics.ts`, `src/types/system.ts`, `src/types/photo.ts`: `GearStatItem`, `GearStats`, `ChartTooltipProps`, `PhotoSummary`, `FolderResponse`, `IndexingStatusResponse`, `ModelDownloadStatusResponse` 등 명시적 API/차트 인터페이스 신설
  - `src/services/api.ts`: 17개 메서드의 `Promise<any>`/`any[]` 반환형을 구체적 도메인 타입으로 일괄 교체
  - `src/hooks/usePhotosQuery.ts`, `src/components/PhotoGallery.tsx`, `src/components/gallery/PhotoCard.tsx`, `src/components/fullscreen/FullscreenMetadataOverlay.tsx`, `src/components/AnalyticsView.tsx`, `src/components/analytics/AnalyticsKpiGrid.tsx`, `src/components/analytics/ExifBarCharts.tsx`, `src/components/analytics/GearDonutCharts.tsx`, `src/utils/exif.ts`, `src/hooks/useBackendInit.ts`, `src/hooks/useModelDownloadStatus.ts`, `src/components/ModelDownloadModal.tsx`: 캐시 제네릭(`InfiniteData<PhotoSummary[]>`), 컴포넌트 props 및 예외(`unknown`) 타입 구체화로 `src/` 전역 `any` 0건 달성
- **최근 커밋 (`Recent Commits`)**:
  - `bd92eb6` - `refactor(api): define explicit domain response types in ApiClient`
  - `c095184` - `refactor(ui): eliminate remaining any types across gallery, analytics, and hooks`
- **Working Tree State**: 🟢 Clean (No uncommitted changes)
- **검증 완료된 테스트 실행 명령어**:
  - `npx tsc --noEmit && npm run build && ./venv/bin/pytest backend/tests/test_api_analytics.py` (`PASS`)
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - 미해결 티켓 0건으로 Active Step 3~4(`04_studio_ui_analytics 도메인 Step 3 개발 진행해줘`) 재개 가능. `ExifBarCharts.tsx`에서 화각 막대(`"35mm"`) 클릭 시 숫자(`35`)를 파싱하여 `focal_length_min: 35, focal_length_max: 35, use_35mm_equivalent: is35mmMode`로 전달할 것.
