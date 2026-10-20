# [Architecture] 04. Studio UI, Design System & Gear Analytics

---

## 🏛️ 1. 프론트엔드 뷰 계층 및 통계 차트 드릴다운 흐름도

```mermaid
flowchart TD
    App["App.tsx (탭 라우터: Gallery / Insights / Critique)"]
    
    subgraph GalleryFlow["갤러리 & 상세 뷰어 계층"]
        Gallery["PhotoGallery.tsx\n(@tanstack/react-virtual)"] --> Card["gallery/PhotoCard.tsx\n(360px 썸네일 지연 로드)"]
        Detail["DetailPanel.tsx"] --> ExifView["detail/PhotoExifView.tsx"]
        Fullscreen["FullscreenViewer.tsx\n(원본 RAW/JPEG 캔버스)"] --> Overlay["fullscreen/FullscreenMetadataOverlay.tsx"]
    end

    subgraph AnalyticsFlow["장비 통계 인사이트 계층"]
        Analytics["AnalyticsView.tsx"] --> Kpi["analytics/AnalyticsKpiGrid.tsx"]
        Analytics --> Donut["analytics/GearDonutCharts.tsx (카메라/렌즈)"]
        Analytics --> Bar["analytics/ExifBarCharts.tsx (물리/35mm 화각 & F값)"]
    end

    App --> GalleryFlow
    App --> AnalyticsFlow
    Analytics -->|GET /api/analytics/stats| AnalyticsAPI["backend/app/api/analytics.py"]
    Donut -->|Click-to-Filter 드릴다운| Store["useAppStore.ts\n(applyAnalyticsDrilldown ➔ activeTab='gallery')"]
    Bar -->|Click-to-Filter (35mm 모드 연동)| Store
    Store --> Gallery
```

---

## 🏗️ 2. 도메인 파일 트리 및 단일 책임 (SRP)

```text
backend/app/
└── api/analytics.py                   # [기존] 카메라/렌즈 점유율, 물리/35mm 환산 화각, 조리개 집계 라우터

src/
├── App.css                            # [기존] 전역 다크룸 CSS 변수(--bg-canvas, --accent-focal 등) 및 유틸리티
├── store/useAppStore.ts               # [수정대상] activeTab, selectedPhotoId 및 applyAnalyticsDrilldown 액션 추가
├── utils/
│   ├── exif.ts                        # [기존] EXIF 셔터스피드/조리개/화각 포맷팅 유틸리티
│   └── formatters.ts                  # [기존] 파일 크기, 날짜, 시간 포맷팅 유틸리티
├── hooks/
│   ├── useAnalyticsQuery.ts           # [기존] 장비 통계 TanStack Query 훅
│   ├── useFullscreenControls.ts       # [기존] 풀스크린 줌/패닝/키보드 네비게이션 제어 훅
│   └── usePhotosQuery.ts              # [기존/리팩토링대상] 즐겨찾기 낙관적 업데이트 뮤테이션 훅
└── components/
    ├── PhotoGallery.tsx               # [기존] 반응형 가상화 그리드 계산 및 무한 스크롤
    ├── DetailPanel.tsx                # [기존] 우측 슬라이드 인 상세 컨테이너
    ├── FullscreenViewer.tsx           # [기존] 풀스크린 원본 뷰어 및 줌/이동 캔버스
    ├── AnalyticsView.tsx              # [기존] 장비 인사이트 대시보드 컨테이너
    ├── gallery/
    │   └── PhotoCard.tsx              # [기존] 개별 썸네일 카드, 즐겨찾기 토글, 다중 선택 체크박스
    ├── detail/
    │   └── PhotoExifView.tsx          # [기존] EXIF 촬영 스펙 배지 및 Finder 열기(reveal_in_finder) 버튼
    ├── fullscreen/
    │   └── FullscreenMetadataOverlay.tsx # [기존] 풀스크린 플로팅 EXIF 오버레이
    └── analytics/
        ├── AnalyticsKpiGrid.tsx       # [기존] 총 사진 수, 카메라 기종 수, 렌즈 라인업 수, 최다 활용 조리개 KPI 카드
        ├── GearDonutCharts.tsx        # [수정대상] 카메라 바디 및 렌즈 점유율 도넛 차트 (섹션 클릭 드릴다운 지원)
        └── ExifBarCharts.tsx          # [수정대상] 물리 vs 35mm 환산 화각 토글 및 조리개 막대 차트 (막대 클릭 드릴다운 지원)
```

---

## 🤝 3. 타 도메인 참조 및 경계 계약 (Cross-Domain Dependencies)

* **참조하는 외부 도메인 (Inbound/Read)**:
  - `01_indexing_storage`: `PhotoRepository.get_analytics()`를 통해 장비/화각/조리개 집계 조회 및 `/api/photos/{id}/thumbnail`, `/api/photos/{id}/original` 스트림 바인딩.
  - `02_search_curation`: `useAppStore`의 `searchQuery`, `searchFilters`(`use_35mm_equivalent` 포함)를 구독하여 `PhotoGallery.tsx` 뷰포트 목록을 갱신하고, 통계 차트 클릭 시 검색 필터를 역방향으로 주입합니다.
  - `03_ai_critique`: `DetailPanel.tsx` 내부에 `PhotoCritiqueView` 및 `PhotoAiAnalysisView` 마운트.
* **외부 도메인에 노출하는 계약 (Outbound/Expose)**:
  - 전역 디자인 시스템 CSS 변수(`src/App.css`)와 선택/탭/모달 상태(`useAppStore`)를 전 도메인 UI 컴포넌트에 제공합니다.

---

## 🔒 4. 도메인 아키텍처 제약 규칙

1. **가상 스크롤 강제**: 갤러리 그리드는 DOM 노드 폭증을 막기 위해 반드시 `@tanstack/react-virtual` 뷰포트 렌더링을 유지하며, 그리드에서는 원본(`/original`)이 아닌 `/thumbnail`(360px) URL만 바인딩합니다.
2. **뉴트럴 다크 스튜디오 색채 규율**: 사진 자체의 색감 왜곡(Simultaneous Contrast)을 방지하기 위해 UI 배경과 표면에는 무채색 다크룸 팔레트(`--bg-canvas: #09090b` ~ `--bg-elevated: #27272a`)를 사용하고, 시그니처 포인트 액센트로 Leica Red(`--accent-focal: #e11d48` / `#f43f5e`)만 제한적으로 사용합니다.
