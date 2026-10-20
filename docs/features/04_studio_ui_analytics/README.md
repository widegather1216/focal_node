# 📊 [04_studio_ui_analytics] Studio UI, Design System & Gear Analytics

- **현재 상태 (Lifecycle)**: `📐 Planning (Baseline 완료 / 통계 차트 드릴다운 Step 1~4 대기 / REFACTOR 2건 대기)`
- **구현 진척도**: `[□□□□] 0/4 Steps (Active Iteration)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 2건` ([`verification.md`](./verification.md) 참조)
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
  - 📂 구현: [`PhotoGallery.tsx`](../../../src/components/PhotoGallery.tsx), [`PhotoCard.tsx`](../../../src/components/gallery/PhotoCard.tsx), [`DetailPanel.tsx`](../../../src/components/DetailPanel.tsx), [`FullscreenViewer.tsx`](../../../src/components/FullscreenViewer.tsx), [`AnalyticsView.tsx`](../../../src/components/AnalyticsView.tsx), [`ExifBarCharts.tsx`](../../../src/components/analytics/ExifBarCharts.tsx)

### 🚀 Active Iteration: 통계 차트 인터랙티브 드릴다운 (Click-to-Filter) `[To-Be]`
- [x] **Step 1 [DB & Types]**: `[N/A - 02_search_curation의 SearchFilters.use_35mm_equivalent 확장 공유]`
- [x] **Step 2 [Repo & API]**: `[N/A - 백엔드 /api/analytics/stats 추가 변경 없음]`
- [ ] **Step 3 [Service & State]**: `useAppStore.ts`에 차트 항목 클릭 시 기존 필터를 초기화하고 선택된 장비/화각(`use_35mm_equivalent` 연동)/조리개 필터를 세팅한 뒤 `activeTab = 'gallery'`로 즉시 전환하는 `applyAnalyticsDrilldown(partialFilter)` 액션 추가
- [ ] **Step 4 [UI & Integration]**: `GearDonutCharts.tsx`(카메라/렌즈 섹션 클릭) 및 `ExifBarCharts.tsx`(물리/35mm 화각 및 조리개 막대 클릭)에 포인터 커서·호버 툴팁 안내 및 드릴다운 핸들러 연결

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-10-17 / interactive-feature-planner / 장비 통계 차트 클릭 갤러리 드릴다운(Click-to-Filter) 및 35mm 환산 필터 연동 스펙 수립`
- **생성/수정된 핵심 파일**:
  - `docs/features/04_studio_ui_analytics/*`: `applyAnalyticsDrilldown` 상태 전이 계약 및 `GearDonutCharts`/`ExifBarCharts` 인터랙티브 드릴다운 명세 반영
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_api_analytics.py && npx tsc --noEmit`
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `ExifBarCharts.tsx`에서 화각 막대(`"35mm"`) 클릭 시 숫자(`35`)를 파싱하여 `focal_length_min: 35, focal_length_max: 35, use_35mm_equivalent: is35mmMode`로 전달할 것.
