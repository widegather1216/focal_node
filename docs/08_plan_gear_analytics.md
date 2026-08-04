# [구현 완료] 장비 통계 및 인사이트 (Gear Analytics) 명세 및 기획서

## 1. 개요
사진가가 보유한 수많은 사진 데이터를 기반으로 어떤 카메라, 렌즈, 화각(실효/35mm 환산), 조리개 값을 주로 사용하는지 시각적인 통계 차트로 보여주는 기능입니다. 

---

## 2. 데이터베이스 & API 로직 (`PhotoRepository.get_gear_analytics`)
- `image_metadata` 테이블을 활용하여 `PhotoRepository` 및 `/api/analytics` 엔드포인트에서 집계합니다.
- **엔드포인트:** `GET /api/analytics`
- **집계 데이터 구조 (GROUP BY COUNT):**
  - **카메라 바디 통계:** `camera_model`별 사진 장수
  - **렌즈 통계:** `lens_model`별 사진 장수
  - **화각 통계:** 실효 화각 및 `focal_length_35mm` (35mm 환산 화각) 분포
  - **조리개 통계:** `f_number` 별 장수
  - **센서 규격 분포:** `sensor_format` 별 장수 (Full Frame, APS-C 등)

---

## 3. 프론트엔드 UI (`src/components/AnalyticsView.tsx`)
- 사이드바 메뉴의 **[📊 Insights]** 탭 선택 시 메인 그리드 대신 `AnalyticsView` 컴포넌트를 렌더링합니다.
- `recharts` 라이브러리를 도입하여 미려한 도넛 차트(카메라/렌즈 점유율) 및 막대 차트(화각/조리개 사용 분포)를 렌더링합니다.
