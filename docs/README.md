# [Project Master] Focal Node: All-in-One Local Photo Studio

본 프로젝트는 외부 클라우드 전송 없이 Mac Native(Apple MLX)로 구동되는 **프라이버시 보호 로컬 사진 관리 및 AI 검색/비평 데스크탑 플랫폼**입니다.

초고속 자연어 시맨틱 검색, 고용량 RAW 디코딩, 전문 AI 에디토리얼 비평 및 35mm 환산 장비 통계 분석을 단일 데스크탑 환경에서 제공합니다.

---

## 🧭 최신 기능 위키 명세서 (Living Feature Wiki)

프로젝트의 모든 아키텍처, 데이터 모델, API 및 인수 조건은 단일 통합 위키에서 모듈별로 관리됩니다:

* 📄 **[마스터 개요 및 로드맵 (Feature Hub)](./features/core_studio/README.md)**
  * 전체 기능 개요, 마일스톤 완료 현황 및 신규 백로그 체크리스트
* 🏛️ **[시스템 아키텍처 청사진 (Architecture)](./features/core_studio/architecture.md)**
  * Mermaid 데이터 흐름도, 디렉터리 청사진, 3계층 의존성 규칙 및 4대 제약사항
* 📋 **[데이터 모델 및 API 명세서 (Spec & Contracts)](./features/core_studio/spec.md)**
  * SQLite/ChromaDB 스키마, 지능형 2단계 파이프라인 규칙, REST API 계약 및 엣지 케이스 처리
* ✅ **[인수 조건 및 검증 매트릭스 (Verification)](./features/core_studio/verification.md)**
  * Given-When-Then 인수 조건, Happy/Boundary/Negative 테스트 매트릭스 및 결함 관리 대장

---

## 🛠️ 핵심 기술 스택 (Tech Stack)

* **데스크탑 호스트:** Tauri v2, Rust
* **프론트엔드 UI:** React 19, TypeScript, Tailwind CSS, Zustand, TanStack Query, Recharts
* **백엔드 사이드카:** Python 3.11+, FastAPI (동적 포트 0 바인딩), SQLAlchemy
* **데이터베이스:** SQLite (WAL 모드, Foreign Keys 활성화), ChromaDB (Cosine Similarity)
* **AI 추론 엔진:** Apple MLX & PyTorch MPS (SigLIP 2, Gemma 4 12B-it-8bit, UniPercept 8B)
* **미디어 처리:** rawpy (메모리 내 디코딩, 세마포어=3 제어), Pillow

---

## 📦 문서 보관함 및 연구 자료 (Archive & Research)

* 🗄️ **[레거시 상세 명세 아카이브](./archive/legacy_specs/)** (기존 Phase 1~21 상세 명세 및 함수 인벤토리)
* 🔬 **[UniPercept RAM 점유 분석 및 최적화 리포트](./research/UniPercept_Memory_Analysis.md)**
* 📑 **[UniPercept 논문 한국어 완역본](./research/UniPercept_Paper_Korean.md)**
