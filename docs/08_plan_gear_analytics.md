# 장비 통계 및 인사이트 (Gear Analytics) 구현 기획서

## 1. 개요
사진가가 보유한 수많은 사진 데이터를 기반으로, 어떤 카메라, 렌즈, 화각, 조리개 값을 주로 사용하는지 시각적인 통계 차트로 보여주는 기능입니다. 촬영 습관을 분석하고자 하는 전문/아마추어 사진가들에게 강력한 동기를 부여합니다.

## 2. 데이터베이스 로직 (`backend/app/api/analytics.py`)
- 기존의 `image_metadata` 테이블을 활용하므로 추가적인 DB 스키마 수정은 필요하지 않습니다.
- 신규 엔드포인트: `GET /api/analytics`
- 반환할 데이터 구조 (GROUP BY COUNT):
  - **카메라 바디 통계:** `camera_model`별 사진 장수 (예: `{"ILCE-7RM3": 120, "ILCE-9": 50}`)
  - **렌즈 통계:** `lens_model`별 사진 장수
  - **화각 통계:** `focal_length` 구간별 혹은 정확한 수치별 장수
  - **조리개 통계:** `f_number` 별 장수

## 3. 프론트엔드 UI (`src/components/AnalyticsView.tsx`)
### 3.1. 사이드바 연동
- 사이드바 메뉴 상단 혹은 하단에 **[📊 Insights]** (또는 Analytics) 탭을 추가합니다.
- 이 탭을 클릭하면 메인 화면의 `PhotoGallery` 대신 `AnalyticsView` 컴포넌트가 렌더링되도록 상태(`currentView` 등)를 분기합니다.

### 3.2. 차트 렌더링 (recharts)
- 미려한 차트 렌더링을 위해 `npm install recharts` 라이브러리를 도입합니다. (React 생태계에서 가장 안정적이고 커스텀이 쉬움)
- **도넛/파이 차트:** 카메라 모델(Camera Body) 및 렌즈 모델(Lens) 점유율 표시.
- **막대 차트(Bar Chart):** 화각(Focal Length) 및 조리개(Aperture) 사용 분포도 표시.
- 차트 위에 마우스를 올렸을 때(Hover) 해당 장비로 찍은 정확한 사진 장수가 노출되도록 툴팁을 구성합니다.

## 4. 단계별 개발 가이드
1. 백엔드에서 SQLAlchemy `func.count()`와 `group_by()`를 이용해 4가지 주요 통계를 집계하는 API 구현.
2. 프론트엔드에 `recharts` 패키지 설치.
3. `useAppStore.ts`에 현재 보고 있는 화면(View)이 갤러리인지 분석 화면인지 구분하는 상태 추가 (예: `activeView: 'gallery' | 'analytics'`).
4. `AnalyticsView.tsx`를 생성하고 API를 호출하여 받아온 데이터를 `recharts` 컴포넌트에 주입 및 스타일링.
