# [Spec & Contracts] 04. Studio UI, Design System & Gear Analytics

---

## 🌐 1. 백엔드 장비 통계 API 계약 (`/api/analytics`) `[As-Is 기구현]`

* `GET /api/analytics/stats`
  - **Query Parameters:** 없음 (`focal_lengths`와 `focal_lengths_35mm`를 동시에 반환하며 프론트엔드 `ExifBarCharts.tsx`에서 클라이언트 토글)
  - **Response 200:**
    ```json
    {
      "total_photos": 1240,
      "cameras": [{ "name": "ILCE-7RM5", "count": 820 }],
      "lenses": [{ "name": "FE 24-70mm F2.8 GM II", "count": 510 }],
      "focal_lengths": [{ "name": "35mm", "count": 310 }, { "name": "85mm", "count": 290 }],
      "focal_lengths_35mm": [{ "name": "35mm", "count": 310 }, { "name": "85mm", "count": 290 }],
      "apertures": [{ "name": "f/1.4", "count": 240 }, { "name": "f/2.8", "count": 480 }]
    }
    ```

---

## 💻 2. 프론트엔드 전역 상태 계약 (`src/store/useAppStore.ts`) `[As-Is 기구현]`

```typescript
interface AppState {
  activeTab: 'gallery' | 'analytics' | 'critique';
  setActiveTab: (tab: 'gallery' | 'analytics' | 'critique') => void;
  selectedPhotoId: string | null;
  setSelectedPhotoId: (id: string | null) => void;
  isFullscreenOpen: boolean;
  setIsFullscreenOpen: (isOpen: boolean) => void;
  selectedPhotoIds: Set<string>;
  togglePhotoSelection: (id: string) => void;
  clearSelection: () => void;
  critiqueDocumentPhotoId: string | null;
  openCritiqueDocument: (photoId: string | null) => void;
  closeCritiqueDocument: () => void;
}
```

---

## 🎨 3. 디자인 시스템 & 다크 스튜디오 CSS 변수 토큰 (`src/App.css`)

| 역할 | CSS Custom Property | 컬러 값 (Hex / RGBA) | 적용 영역 |
| :--- | :--- | :--- | :--- |
| **App Canvas (최심부 배경)** | `--bg-canvas` | `#09090b` | 메인 갤러리 배경, 풀스크린 뷰어 캔버스 |
| **Surface (패널/사이드바)** | `--bg-surface` | `#121215` | 좌측 사이드바, 글로벌 헤더, 팝아웃 배경 |
| **Card (카드/컨테이너)** | `--bg-card` | `#18181b` | 사진 카드, 우측 상세 패널, 차트 카드 |
| **Elevated (모달/호버)** | `--bg-elevated` | `#27272a` | 드롭다운, 입력창, 필터 칩, 모달 표면 |
| **Text Hierarchy** | `--text-primary` / `--text-secondary` / `--text-muted` | `#f4f4f5` / `#a1a1aa` / `#71717a` | 주 타이틀 / 보조 본문 / 캡션 및 비활성 레이블 |
| **Primary Accent (Leica Red)** | `--accent-focal` / `--accent-focal-hover` | `#e11d48` / `#f43f5e` | 주요 액션 버튼, 선택 테두리, RAW 배지, 차트 바 |
| **Border (미세 경계선)** | `--border-subtle` / `--border-default` | `rgba(255,255,255,0.06)` / `rgba(255,255,255,0.1)` | 패널 구분선, 카드 외곽선 |
| **Semantic Status** | `--status-success` / `--status-warning` / `--status-danger` | `#10b981` / `#f59e0b` / `#ef4444` | 인덱싱 완료 / 진행·경고 / 에러·삭제 상태 |

---

## 🛡️ 4. UI 상태 전이 및 예외 처리

1. **Empty State 및 폴더 등록**: 검색 결과가 없거나 사진이 없을 때 `PhotoGallery.tsx`는 `"일치하는 사진이 없습니다"` 안내 화면을 노출하며, 좌측 `Sidebar.tsx`의 `[사진 폴더 추가]` 버튼을 통해 Tauri 네이티브 폴더 선택 다이얼로그를 호출합니다.
2. **EXIF 누락 사진 통계 처리**: 스크린샷이나 EXIF가 없는 이미지는 차트 왜곡을 막기 위해 `PhotoRepository.get_analytics()` 쿼리 단계에서 `NULL` 및 빈 문자열(`""`)을 필터링하여 장비 분포 집계에서 제외합니다.
