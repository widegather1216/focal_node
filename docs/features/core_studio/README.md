# [Feature Hub] 올인원 로컬 포토 스튜디오 (Core Photo Studio)

외부 클라우드 전송 없이 Mac Native(Apple MLX)로 구동되는 프라이버시 보호 로컬 사진 관리 및 AI 검색/비평 플랫폼입니다.

---

## 📌 개요 및 상태

* **기능명:** Core Photo Studio (올인원 로컬 포토 스튜디오)
* **상태:** `🟢 Planning Complete (독립 세션 검증 게이트 1/2/3 전 부문 통과)`
* **타깃 플랫폼:** macOS (Tauri v2 + Python FastAPI Sidecar + Apple MLX)
* **핵심 가치:** 100% 온디바이스 프라이버시, 초고속 시맨틱 자연어 탐색, 전문 에디토리얼 AI 비평, EXIF 기반 장비 통계

---

## 🔗 빠른 링크 (Quick Links)

* 🏛️ [아키텍처 및 계층 규칙 (architecture.md)](./architecture.md)
* 📋 [데이터 모델, API 및 엣지케이스 명세 (spec.md)](./spec.md)
* ✅ [인수 조건 및 검증 매트릭스 (verification.md)](./verification.md)
* 📦 [레거시 명세 보관함 (Archive)](../../archive/legacy_specs/)

---

## 🗺️ 구현 및 정합성 로드맵 (Roadmap Checklist)

- [x] **M1. 인프라 & 로컬 AI 런타임 연동**
  - [x] Tauri v2 + FastAPI 동적 포트(0) 사이드카 통신
  - [x] Apple MLX 기반 SigLIP 2(검색) 및 Gemma 4 / UniPercept 8B 로더
- [x] **M2. 1단계 파이프라인: 지능형 백그라운드 인덱싱**
  - [x] 로컬 폴더 스캔 및 SHA-256 원자적 해싱
  - [x] EXIF 메타데이터 추출 및 360px sRGB JPEG 썸네일 캐싱
  - [x] SigLIP 2 시각 임베딩 생성 및 ChromaDB / SQLite WAL 저장
- [x] **M3. 초고속 탐색 & 하이브리드 검색**
  - [x] 가상 스크롤 갤러리 및 모노크롬 다크 스튜디오 UI
  - [x] 자연어 시맨틱 검색 + EXIF(조리개, ISO, 화각, 날짜) 필터 결합
  - [x] K-NN 톤앤매너 유사 사진 추천
- [ ] **M4. 스마트 앨범 (Smart Albums)**
  - [ ] 복합 검색 조건(자연어 + EXIF 필터) 프리셋 저장/불러오기 API
  - [ ] 사이드바 동적 앨범 탭 및 원클릭 필터 적용
- [x] **M5. 2단계 파이프라인: 온디맨드 전문 AI 비평**
  - [x] 상세 뷰어 진입 시 온디맨드 비평 생성 및 SQLite 영구 캐싱
  - [x] 에디토리얼 비평 리포트 모달 열람 및 Markdown/PDF 내보내기
  - [x] 60초 비동기 Keep-alive 및 실시간 비평 취소 파이프라인
- [x] **M6. 장비 통계 분석 및 워크플로우 연동**
  - [x] 35mm 환산 화각 도넛 차트 및 조리개/ISO 분포 시각화
  - [x] 외장 드라이브 오프라인 스마트 배지 및 무결성 관리
  - [x] 시스템 모델 다운로더 모달 및 실시간 상태 모니터링
