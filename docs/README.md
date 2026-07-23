# [Project Master] AI 기반 로컬 사진 검색 데스크탑 앱

본 프로젝트는 SigLIP 2와 Gemma 4 E4B-it 모델을 활용하여, 외부 클라우드 전송 없이 로컬 환경에서 프라이버시를 완벽히 보호하며 사진을 관리하고 자연어로 검색할 수 있는 데스크탑 애플리케이션입니다.

메모리를 극도로 절약하기 위해 Electron 대신 **Tauri + Python Sidecar** 아키텍처를 채택하고 있습니다.

---

## 📂 개발 참고 문서 목차 (Table of Contents)

1. 🏛️ **[시스템 아키텍처 및 데이터베이스 설계](./01_system_architecture_db.md)**
   * 어댑터 패턴 (Adapter Pattern) 구조
   * SQLite 관계형 데이터베이스 스키마 (WAL 모드 적용)
   * ChromaDB 벡터 데이터베이스 컬렉션 구성

2. ⚙️ **[백엔드 파이프라인 및 API / AI 프롬프트 명세](./02_backend_pipeline_api.md)**
   * Indexing Service 백그라운드 워크플로우
   * FastAPI API 엔드포인트 규격
   * Gemma 4 E4B-it 이미지 분석 시스템 프롬프트

3. 🎨 **[프론트엔드 아키텍처 및 UI/UX 설계](./03_frontend_ui_ux.md)**
   * Zustand 전역 상태 및 TanStack Query 서버 상태 관리
   * `@tanstack/react-virtual` 가상 스크롤 및 성능 최적화
   * 온보딩, 사이드바, 메인 갤러리 및 상세 패널 레이아웃

4. ⚠️ **[에이전트 구현 제약사항 명세 (중요)](./04_implementation_constraints.md)**
   * FastAPI 동적 포트 할당 및 Tauri 포트 주입 규칙
   * SQLite WAL 모드 및 외래 키 동시성 설정
   * 메모리 내(In-Memory) RAW 파일 스트리밍 구현 규칙
   * CPU Bound 작업의 이벤트 루프 블로킹 방지 대책

5. 🤖 **[AI 모델 설치 및 로컬 구동 가이드](./05_ai_model_setup.md)**
   * Gemma 4 E4B-it 설치 및 MLX 구동 방법
   * SigLIP 2 설치 및 PyTorch MPS 가속 구동 방법
   * Apple Silicon GPU (Metal) 가속 검증 지침

6. 📐 **[코드베이스 함수 인벤토리 및 명세서](./09_codebase_function_inventory.md)**
   * 백엔드(FastAPI), 데스크탑 호스트(Tauri/Rust), 프론트엔드(React/TS) 파일별 함수 및 API 명세
   * 함수별 파라미터(입력), 반환타입(출력) 및 역할 설명
   * 소스 코드 추상화(Abstraction) 및 리팩토링 제안 사항

---

## 🚀 1. 프로젝트 개요 및 핵심 목표

### 1.1. 핵심 목표
* **자연어 기반 시맨틱 검색:** "비 오는 날 카페", "역광에서 뛰어가는 강아지" 등 맥락과 분위기로 사진 검색.
* **오프라인 메타데이터 생성:** AI가 사진을 분석하여 캡션과 핵심 태그(키워드)를 자동 생성.
* **프로 사진가 워크플로우 지원:** 고용량 RAW 파일(ARW, CR3 등) 디코딩 및 Adobe RGB 처리, 정밀한 EXIF 메타데이터(ISO, 조리개 등) 추출.
* **하드웨어 최적화:** M4 칩의 통합 메모리 구조를 극대화하는 MLX 어댑터를 우선 구축하고, 향후 Windows 확장성을 보장하는 어댑터(DIP) 패턴 적용.

### 1.2. 기술 스택 (Tech Stack)
* **Frontend:** Tauri, React 18, TypeScript, Tailwind CSS, Zustand, TanStack Query
* **Backend:** Python (FastAPI), SQLAlchemy, PyInstaller
* **Database:** SQLite (관계형 메타데이터, WAL 모드), ChromaDB (벡터 데이터)
* **AI Models & Engine:** SigLIP 2, Gemma 4 E4B-it / Apple MLX (Mac Native)
