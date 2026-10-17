# 📊 [04_studio_ui_analytics] Studio UI, Design System & Gear Analytics

- **현재 상태 (Lifecycle)**: `🩹 Debugging (Baseline 검증 완료 / REFACTOR 1건 대기)`
- **구현 진척도**: `[■■■■] 4/4 Steps`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 1건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

가상 스크롤(`@tanstack/react-virtual`) 기반 갤러리, 풀스크린 뷰어, 우측 딥다이브 패널, 다크 스튜디오 CSS 변수 디자인 시스템 및 35mm 환산 장비 통계 대시보드를 담당하는 도메인입니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### ✅ Baseline (As-Is 기구현 완료)
- [x] **Step 1 [Design Tokens & Formatters]**: 뉴트럴 다크룸 CSS 변수(`--bg-canvas: #09090b`, `--accent-focal: #e11d48`) 및 EXIF/날짜 포맷터 정의
  - 📂 구현: [`App.css`](../../../src/App.css), [`exif.ts`](../../../src/utils/exif.ts), [`formatters.ts`](../../../src/utils/formatters.ts)
- [x] **Step 2 [Analytics API & Query]**: 카메라/렌즈 점유율 및 물리/35mm 환산 화각/조리개 분포 집계 API(`/api/analytics/stats`)
  - 📂 구현: [`analytics.py`](../../../backend/app/api/analytics.py), [`photo_repository.py`](../../../backend/app/repositories/photo_repository.py), [`useAnalyticsQuery.ts`](../../../src/hooks/useAnalyticsQuery.ts) | 🧪 테스트: [`test_api_analytics.py`](../../../backend/tests/test_api_analytics.py) (`PASS`)
- [x] **Step 3 [Global Store & Viewer Hooks]**: 탭/선택/풀스크린 Zustand 전역 스토어 및 풀스크린 줌/패닝/단축키 제어 훅
  - 📂 구현: [`useAppStore.ts`](../../../src/store/useAppStore.ts), [`useFullscreenControls.ts`](../../../src/hooks/useFullscreenControls.ts), [`usePhotosQuery.ts`](../../../src/hooks/usePhotosQuery.ts)
- [x] **Step 4 [Virtual Gallery, Viewer & Charts UI]**: `@tanstack/react-virtual` 갤러리 그리드, 우측 상세 패널, 풀스크린 뷰어 및 Recharts 도넛/바 차트
  - 📂 구현: [`PhotoGallery.tsx`](../../../src/components/PhotoGallery.tsx), [`PhotoCard.tsx`](../../../src/components/gallery/PhotoCard.tsx), [`DetailPanel.tsx`](../../../src/components/DetailPanel.tsx), [`FullscreenViewer.tsx`](../../../src/components/FullscreenViewer.tsx), [`AnalyticsView.tsx`](../../../src/components/AnalyticsView.tsx), [`ExifBarCharts.tsx`](../../../src/components/analytics/ExifBarCharts.tsx)

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-10-17 / clean-code-auditor / 통계 API 스키마, CSS 변수 디자인 토큰 통합 및 정적 코드 감사`
- **생성/수정된 핵심 파일**:
  - `docs/features/04_studio_ui_analytics/*`: `/api/analytics/stats` 응답 포맷(`focal_lengths_35mm`, `name`/`count`), `App.css` CSS 변수 토큰 및 컴포넌트 경로 동기화
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_api_analytics.py && npx tsc --noEmit`
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `REFACTOR-01` 해결 시 `useAppStore.ts` 내부의 직접 `fetch()` 호출 3곳을 `src/services/api.ts` 클라이언트 메서드로 위임하고 `usePhotosQuery.ts`의 미사용 함수를 정리할 것.
