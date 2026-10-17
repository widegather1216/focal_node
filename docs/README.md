# 🧭 Focal Node: Master Control Tower (Living Wiki Hub)

> 외부 클라우드 전송 없이 Mac Native(Apple MLX & PyTorch MPS)로 구동되는 **프라이버시 보호 로컬 사진 관리 및 AI 시맨틱 검색/비평 데스크탑 플랫폼**입니다.
> **최종 업데이트**: 2026-10-17 (by `clean-code-auditor` & `interactive-feature-planner`)

---

## 🎯 1. Current Spotlight (현재 포커스 & 다음 추천 액션)

- **Active 도메인**: [`02_search_curation`](./features/02_search_curation/README.md) / [`01_indexing_storage`](./features/01_indexing_storage/README.md)
- **현재 단계 (Stage)**: `📐 Planning Complete` (신규 기능 구현 대기) & `🩹 Debugging` (클린코드 리팩토링 티켓 등록 완료)
- **직전 완료 작업**: 레거시 문서(`docs/archive/`) 일괄 정리, 전 도메인 코드-문서 정합성(Drift) 100% 교정 및 정적 코드 감사(`REFACTOR` 티켓 발권) 완료
- **👉 다음 추천 프롬프트 (복사해서 바로 실행)**:
  > `"02_search_curation 도메인 Step 1 개발 진행해줘"` *(또는 리팩토링 우선 시: `"03_ai_critique 도메인의 REFACTOR-01 티켓 해결해줘"`)*

---

## 📊 2. 전체 도메인 진행 현황판 (Master Progress Matrix)

| 도메인 (Bounded Context) | 생명주기 상태 | 구현 진척도 (Step 1~4) | QA 인수 통과율 | 미해결 티켓 (`🚨D` / `🧐R`) | 최근 작업 요약 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| 🏛️ [`00_core_foundation`](./features/00_core_foundation/README.md) | 🩹 Debugging | `[■■■■] 4/4` | `3/3 (100%)` | `0 / 1` | 동적 포트/IPC/모델 로더 검증 완료 (`REFACTOR-01` 등록) |
| 💾 [`01_indexing_storage`](./features/01_indexing_storage/README.md) | 📐 Planning | `[□□□□] 0/4` | `3/4 (75%)` | `0 / 1` | Baseline 완료, 스마트 오프라인(`is_offline`) Step 1~4 대기 |
| 🔍 [`02_search_curation`](./features/02_search_curation/README.md) | 📐 Planning | `[□□□□] 0/4` | `2/5 (40%)` | `0 / 1` | 하이브리드 검색 완료, **M4. 스마트 앨범 Step 1~4 대기** |
| 🤖 [`03_ai_critique`](./features/03_ai_critique/README.md) | 🩹 Debugging | `[■■■■] 4/4` | `3/3 (100%)` | `0 / 2` | 2-모델 비평 및 MD/PDF 내보내기 완료 (`REFACTOR-01, 02` 대기) |
| 📊 [`04_studio_ui_analytics`](./features/04_studio_ui_analytics/README.md) | 🩹 Debugging | `[■■■■] 4/4` | `3/3 (100%)` | `0 / 1` | 가상 스크롤 갤러리 및 35mm 통계 완료 (`REFACTOR-01` 대기) |

*(※ 상태 범례: `📐 Planning` | `🛠️ Implementing` | `🧐 Auditing` | `🧪 QA Testing` | `🩹 Debugging` | `🟢 Sign-Off`)*
*(※ 미해결 티켓: `🚨D` = Open `DEFECT-xx` 개수, `🧐R` = Open `REFACTOR-xx` 개수)*

---

## 🕒 3. 최근 세션 타임라인 (Recent Session Changelog)

- **`[2026-10-17]` `[clean-code-auditor]` [`ALL`]**: 전 도메인 위키-코드 불일치(API 경로, 스키마, 파일 트리, CSS 토큰) 교정, 레거시 문서(`docs/archive/`) 폐기 및 도메인별 `REFACTOR` 티켓 발권.
- **`[2026-10-17]` `[interactive-feature-planner]` [`01_indexing_storage`, `02_search_curation`]**: 스마트 오프라인(`is_offline`) 및 M4 스마트 앨범(`smart_albums`) 4단계 구현 로드맵 수립.

---

## 🛠️ 4. 핵심 기술 스택 및 연구 자료 (Tech Stack & Research)

* **데스크탑 호스트:** Tauri v2, Rust (`[Sidecar] PORT: {port}` 감지, `get_api_port` / `reveal_in_finder` / `save_binary_file` IPC)
* **프론트엔드 UI:** React 19, TypeScript, Custom CSS Variables (`src/App.css`), Zustand (`useAppStore`), TanStack Query & Virtual, Recharts
* **백엔드 사이드카:** Python 3.10+, FastAPI (`port=0`), SQLAlchemy, SQLite (`focal_node.db`, WAL 모드), ChromaDB (`photo_embeddings`, cosine)
* **AI 추론 엔진:** Apple MLX (`Gemma 4 12B-it-8bit`, 60s Keep-alive) & PyTorch MPS (`SigLIP 2` 메모리 상주, `UniPercept 8B` 즉시 언로드)
* **연구 레퍼런스:** 🔬 [UniPercept RAM 점유 및 최적화 분석](./research/UniPercept_Memory_Analysis.md) | 📑 [UniPercept 지각 평가 이론 및 수식 요약](./research/UniPercept_Paper_Korean.md)
