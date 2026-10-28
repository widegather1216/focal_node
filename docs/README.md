# 🧭 Focal Node: Master Control Tower (Living Wiki Hub)

> 외부 클라우드 전송 없이 Mac Native(Apple MLX & PyTorch MPS)로 구동되는 **프라이버시 보호 로컬 사진 관리 및 AI 시맨틱 검색/비평 데스크탑 플랫폼**입니다.
> **최종 업데이트**: 2026-10-28 (by `clean-code-developer`)

---

## 🎯 1. Current Spotlight (현재 포커스 & 다음 추천 액션)

- **Active 도메인**: [`03_ai_critique`](./features/03_ai_critique/README.md)
- **현재 단계 (Stage)**: `🟢 Sign-Off 대기` (`03_ai_critique` 미학 주도형 EXIF 적응적 종합 평점 모델 Step 1~4 전 계층 구현 완료)
- **직전 완료 작업**: [`03_ai_critique`](./features/03_ai_critique/README.md) 도메인 Step 4 [UI & Integration] 구현 완료 (`ScoringGuideModal.tsx` 컴포넌트 추가 및 `CritiqueContentRenderer.tsx` 스코어보드 헤더에 `[?] 점수 산출 가이드` 버튼 연결, TC-CRT-09 검증 완료, `npx tsc --noEmit && npm run build` 및 백엔드 98종 전수 통과)
- **👉 다음 추천 프롬프트 (복사해서 바로 실행)**:
  > `"03_ai_critique 도메인 클린코드 품질 감사 진행해줘"` *(전체 계층 정적 분석 및 클린코드 품질 감사 실행)*

---

## 📊 2. 전체 도메인 진행 현황판 (Master Progress Matrix)

| 도메인 (Bounded Context) | 생명주기 상태 | 구현 진척도 (Active Step 1~4) | QA 인수 통과율 | 미해결 티켓 (`🚨D` / `🧐R`) | 최근 작업 요약 |
| :--- | :--- :---: | :---: | :---: | :---: | :--- |
| 🏛️ [`00_core_foundation`](./features/00_core_foundation/README.md) | 🩹 Debugging | `[■■■■] 4/4` | `3/3 (100%)` | `0 / 1` | 동적 포트/IPC/모델 로더 검증 완료 (`REFACTOR-01` 대기) |
| 💾 [`01_indexing_storage`](./features/01_indexing_storage/README.md) | 📐 Planning | `[□□□□] 0/4` | `3/6 (50%)` | `0 / 1` | 스마트 오프라인 + SHA-256 Relocation + 2-Pass 인덱싱 Step 1~4 대기 |
| 🔍 [`02_search_curation`](./features/02_search_curation/README.md) | 📐 Planning | `[□□□□] 0/4` | `2/7 (29%)` | `0 / 1` | 거리 임계값 + RRF 랭킹 + 35mm/점수 필터 + 스마트 앨범 Step 1~4 대기 |
| 🤖 [`03_ai_critique`](./features/03_ai_critique/README.md) | 🟢 Sign-Off | `[■■■■] 4/4` | `4/4 (100%)` | `0 / 3` | Step 4 [UI & Integration] 완료 (ScoringGuideModal 연동, 품질 감사 대기) |
| 📊 [`04_studio_ui_analytics`](./features/04_studio_ui_analytics/README.md) | 📐 Planning | `[■■□□] 2/4` | `3/4 (75%)` | `0 / 2` | 통계 차트 클릭 갤러리 드릴다운(`Click-to-Filter`) Step 3~4 대기 |

*(※ 상태 범례: `📐 Planning` | `🛠️ Implementing` | `🧐 Auditing` | `🧪 QA Testing` | `🩹 Debugging` | `🟢 Sign-Off`)*
*(※ 미해결 티켓: `🚨D` = Open `DEFECT-xx` 개수, `🧐R` = Open `REFACTOR-xx` 개수)*

---

## 🕒 3. 최근 세션 타임라인 (Recent Session Changelog)

- **`[2026-10-28]` `[clean-code-developer]` [`03_ai_critique`]**: Step 4 [UI & Integration] 구현 완료 (`ScoringGuideModal.tsx` 컴포넌트 신규 구현 및 `CritiqueContentRenderer.tsx` 스코어보드 헤더에 `[?] 점수 산출 가이드` 버튼 연결, `TC-CRT-09` 검증 완료, `npx tsc --noEmit && npm run build` 통과, 도메인 회귀 56종 및 백엔드 98종 전수 통과, Step 1~4 구현 완료로 spec.md/architecture.md As-Is 승격 병합).
- **`[2026-10-28]` `[clean-code-developer]` [`03_ai_critique`]**: Step 3 [Domain Service] 구현 완료 (`unipercept_adapter.py`에 `_resolve_perceptual_weights`, `_calculate_aesthetic_bonus`, `_calculate_overall_vr_score` 추가 및 `scoring.py` 위임 연동, `generate_vr_scores`/`generate_full_ensemble_critique` 및 `chat_service.py` EXIF 메타데이터 연동, `TC-CRT-06/07` 단위 테스트 작성 및 통과, 도메인 회귀 56종 및 백엔드 98종 전수 통과).
- **`[2026-10-28]` `[clean-code-developer]` [`03_ai_critique`]**: Step 1 [DB & Migration] 구현 완료 (`database.py` `run_migrations()`에 EXIF 조인 기반 `overall_score` 적응형 일괄 재계산 백필(`_backfill_adaptive_overall_scores`) 및 `services/scoring.py` 4대 모드/미학보너스/평점클램핑 순수 연산 모듈 분리, Step 2 N/A 정리, 단위 테스트 `test_adaptive_scoring.py` 4종 작성 및 통과, 도메인 회귀 54종 및 백엔드 96종 전수 통과).
- **`[2026-10-26]` `[interactive-feature-planner]` [`03_ai_critique`]**: '미학 주도형 EXIF 적응적 사진 지각 평점 모델 및 점수 가이드 모달' 기획 완료 (UniPercept ISTA 텍스처 풍부도 왜곡 극복을 위한 EXIF 조리개/ISO 4대 가중치, 미학적 탁월성 보너스, `database.py` 기동 시 자동 백필, `ScoringGuideModal` 컴포넌트 스펙 확정, `ADR-04` 및 위키 전수 갱신).
- **`[2026-10-25]` `[clean-code-auditor]` [`03_ai_critique`]**: 3개 계층 [데이터 모델/Repo ➔ 도메인 서비스/API ➔ 클라이언트 상태/UI] 전수 정적 분석 및 클린코드 품질 감사 완료 (`tsc --noEmit` & `npm run build` PASS, `pytest` 50종 도메인 테스트 전수 PASS, `REFACTOR-01~02` 최신화 및 `REFACTOR-03` 발권 총 3건 대기).
- **`[2026-10-25]` `[clean-code-developer]` [`03_ai_critique`]**: Step 4 [UI & Integration] 구현 완료 (`CritiqueContentRenderer` 정규화 평점/영문 원문 props 바인딩 및 `OriginalEnglishCritiqueCard` 토글 컴포넌트 추가, `CritiqueCard` SCORE 배지 표시, `CritiqueView` `[최신순 / 종합평점순 / 미학점수순]` 세그먼트 정렬 토글 UI 연동, `DetailPanel`/`PhotoCritiqueView`/`CritiqueDocumentModal` 연계 반영, `tsc --noEmit` & `npm run build` 통과 및 백엔드 92종 전수 통과).
- **`[2026-10-24]` `[clean-code-developer]` [`03_ai_critique`]**: Step 3 [Service & State] 구현 완료 (`ChatService._save_critique_to_db`에서 `scores_dict` 및 `raw_en`을 `ai_analysis` 테이블의 정규화 컬럼(`overall_score`, `iaa_score`, `iqa_score`, `ista_score`, `critique_en`)에 직접 영구 저장 연동, 파이프라인 반환값 및 `critique_status_manager` 상태 객체 연동, 신규 단위 테스트 10종 작성 및 도메인 회귀 50종·백엔드 92종 전수 통과).
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
