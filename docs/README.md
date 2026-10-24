# 🧭 Focal Node: Master Control Tower (Living Wiki Hub)

> 외부 클라우드 전송 없이 Mac Native(Apple MLX & PyTorch MPS)로 구동되는 **프라이버시 보호 로컬 사진 관리 및 AI 시맨틱 검색/비평 데스크탑 플랫폼**입니다.
> **최종 업데이트**: 2026-10-17 (by `interactive-feature-planner` & `clean-code-auditor`)

---

## 🎯 1. Current Spotlight (현재 포커스 & 다음 추천 액션)

- **Active 도메인**: [`03_ai_critique`](./features/03_ai_critique/README.md)
- **현재 단계 (Stage)**: `🛠️ Implementing` (`03_ai_critique` Step 2 완료 / Step 3 대기) & `🩹 Debugging` (`REFACTOR` 7건 대기)
- **직전 완료 작업**: [`03_ai_critique`](./features/03_ai_critique/README.md) Step 2 [Repo & API] 구현 완료 (`PhotoRepository.list_critiques` 평점순 정렬 및 `delete_critique` 정규화 초기화, `GET /api/chat/critiques` 정규화 평점/원문 연동, `ApiClient` 타입 확장, 신규 9종 포함 도메인 회귀 40종·백엔드 82종 전수 통과)
- **👉 다음 추천 프롬프트 (복사해서 바로 실행)**:
  > `"03_ai_critique 도메인 Step 3 개발 진행해줘"` *(ChatService._save_critique_to_db 정규화 컬럼 직접 저장 연동)*

---

## 📊 2. 전체 도메인 진행 현황판 (Master Progress Matrix)

| 도메인 (Bounded Context) | 생명주기 상태 | 구현 진척도 (Active Step 1~4) | QA 인수 통과율 | 미해결 티켓 (`🚨D` / `🧐R`) | 최근 작업 요약 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| 🏛️ [`00_core_foundation`](./features/00_core_foundation/README.md) | 🩹 Debugging | `[■■■■] 4/4` | `3/3 (100%)` | `0 / 1` | 동적 포트/IPC/모델 로더 검증 완료 (`REFACTOR-01` 대기) |
| 💾 [`01_indexing_storage`](./features/01_indexing_storage/README.md) | 📐 Planning | `[□□□□] 0/4` | `3/6 (50%)` | `0 / 1` | 스마트 오프라인 + SHA-256 Relocation + 2-Pass 인덱싱 Step 1~4 대기 |
| 🔍 [`02_search_curation`](./features/02_search_curation/README.md) | 📐 Planning | `[□□□□] 0/4` | `2/7 (29%)` | `0 / 1` | 거리 임계값 + RRF 랭킹 + 35mm/점수 필터 + 스마트 앨범 Step 1~4 대기 |
| 🤖 [`03_ai_critique`](./features/03_ai_critique/README.md) | 🛠️ Implementing | `[■■□□] 2/4` | `4/5 (80%)` | `0 / 2` | Step 2 [Repo & API] 완료 (Step 3 서비스 저장 대기) |
| 📊 [`04_studio_ui_analytics`](./features/04_studio_ui_analytics/README.md) | 📐 Planning | `[■■□□] 2/4` | `3/4 (75%)` | `0 / 2` | 통계 차트 클릭 갤러리 드릴다운(`Click-to-Filter`) Step 3~4 대기 |

*(※ 상태 범례: `📐 Planning` | `🛠️ Implementing` | `🧐 Auditing` | `🧪 QA Testing` | `🩹 Debugging` | `🟢 Sign-Off`)*
*(※ 미해결 티켓: `🚨D` = Open `DEFECT-xx` 개수, `🧐R` = Open `REFACTOR-xx` 개수)*

---

## 🕒 3. 최근 세션 타임라인 (Recent Session Changelog)

- **`[2026-10-24]` `[clean-code-developer]` [`03_ai_critique`]**: Step 2 [Repo & API] 구현 완료 (`PhotoRepository.list_critiques(sort_by)` 평점순 정렬 지원 및 `delete_critique` 정규화 초기화, `GET /api/chat/critiques` 응답에 정규화 4종 평점/`critique_en` 반영, `ApiClient.getCritiques(sortBy)` 타입 강화, 신규 단위 테스트 9종 작성 및 도메인 회귀 40종·백엔드 82종 전수 통과).
- **`[2026-10-20]` `[clean-code-developer]` [`03_ai_critique`]**: Step 1 [DB & Types] 구현 완료 (`ai_analysis` 정규화 컬럼 추가, `run_migrations()` DDL/인덱스 생성 및 6-Way 스코어보드 자동 백필, Pydantic/TS 타입 확장, 단위 테스트 8종 작성 및 회귀 31종 전수 통과).
- **`[2026-10-17]` `[interactive-feature-planner]` [`01~04`]**: 5대 핵심 로직·스펙 발전안(SHA-256 Relocation, 2-Pass 점진적 인덱싱, 코사인 임계값+RRF 랭킹, 비평 평점 DB 정규화, 35mm 환산 필터 및 차트 드릴다운) 설계 및 위키 전수 반영.
- **`[2026-10-17]` `[clean-code-auditor]` [`ALL`]**: 전 도메인 7대 감사 매트릭스 전수 정적 분석(tsc, pytest 65건 전수 통과 확인), Silent Fail/`any` 타입/거대 컴포넌트 식별 및 `REFACTOR` 티켓 최신화.
- **`[2026-10-17]` `[clean-code-auditor]` [`ALL`]**: 전 도메인 위키-코드 불일치(API 경로, 스키마, 파일 트리, CSS 토큰) 교정, 레거시 문서(`docs/archive/`) 폐기 및 도메인별 `REFACTOR` 티켓 발권.

---

## 🛠️ 4. 핵심 기술 스택 및 연구 자료 (Tech Stack & Research)

* **데스크탑 호스트:** Tauri v2, Rust (`[Sidecar] PORT: {port}` 감지, `get_api_port` / `reveal_in_finder` / `save_binary_file` IPC)
* **프론트엔드 UI:** React 19, TypeScript, Custom CSS Variables (`src/App.css`), Zustand (`useAppStore`), TanStack Query & Virtual, Recharts
* **백엔드 사이드카:** Python 3.10+, FastAPI (`port=0`), SQLAlchemy, SQLite (`focal_node.db`, WAL 모드), ChromaDB (`photo_embeddings`, cosine)
* **AI 추론 엔진:** Apple MLX (`Gemma 4 12B-it-8bit`, 60s Keep-alive) & PyTorch MPS (`SigLIP 2` 메모리 상주, `UniPercept 8B` 즉시 언로드)
* **연구 레퍼런스:** 🔬 [UniPercept RAM 점유 및 최적화 분석](./research/UniPercept_Memory_Analysis.md) | 📑 [UniPercept 지각 평가 이론 및 수식 요약](./research/UniPercept_Paper_Korean.md)
