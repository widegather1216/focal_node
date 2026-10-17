# [Decisions (ADR)] 04. Studio UI, Design System & Gear Analytics

---

### [ADR-01] 프로페셔널 뉴트럴 다크 스튜디오 & Leica Red 액센트 디자인 시스템 채택
- **배경**: 화려한 브랜드 컬러가 들어간 UI 배경은 사진작가가 사진의 노출과 화이트밸런스를 판단할 때 색채 착시(Simultaneous Contrast)를 유발함.
- **결정**: Capture One 및 Leica FOTOS 스타일의 무채색 다크룸 표면(`#09090b` ~ `#27272a`)을 전역 캔버스로 채택하고, 주요 액션과 포커스 인디케이터에만 시그니처 Leica Red(`#e11d48`) 액센트를 적용함.
- **영향**: 사진 원본의 색감 집중도 극대화 및 일관된 스튜디오 감성 확보.

### [ADR-02] TanStack Virtual + Zustand 상태 분리
- **배경**: 수만 장의 썸네일 그리드에서 다중 선택이나 필터 변경 시 전체 그리드 리렌더링이 발생하면 UI 지연이 발생함.
- **결정**: 뷰포트 내 행만 렌더링하는 `@tanstack/react-virtual`을 적용하고, UI 선택/필터 상태는 `useAppStore`(Zustand)로 분리함.
- **영향**: 대용량 라이브러리에서도 즉각적인 탭 전환 및 다중 선택 반응성 확보.
