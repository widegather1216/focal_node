# 🧭 Focal Node: Master Control Tower (Living Wiki Hub)

> 외부 클라우드 전송 없이 Mac Native(Apple MLX & PyTorch MPS)로 구동되는 **프라이버시 보호 로컬 사진 관리 및 AI 시맨틱 검색/비평 데스크탑 플랫폼**입니다.
> **최종 업데이트**: 2026-11-06 (by `clean-code-auditor`)

---

## 🎯 1. Current Spotlight (현재 포커스 & 다음 추천 액션)

- **Active 도메인**: [`03_ai_critique`](./features/03_ai_critique/README.md)
- **현재 단계 (Stage)**: `🩹 Debugging (UniPercept 취소 미해제 DEFECT-02·VQA 불능 DEFECT-03 및 REFACTOR 6건 해결 대기)`
- **직전 완료 작업**: [`03_ai_critique`](./features/03_ai_critique/README.md) 도메인 전 계층 7대 감사 완료 및 UniPercept 중단 시 28GB 메모리 미해제(`DEFECT-02`)·`transformers 5.x` VQA `return_dict` 충돌(`DEFECT-03`) 근본 원인 규명 및 티켓 등록
- **👉 다음 추천 프롬프트 (복사해서 바로 실행)**:
  > `"03_ai_critique 도메인의 DEFECT-02 티켓 해결해줘"` *(최우선 런타임 메모리 결함 수술적 해결)*

---

## 📊 2. 전체 도메인 진행 현황판 (Master Progress Matrix)

| 도메인 (Bounded Context) | 생명주기 상태 | 구현 진척도 (Active Step 1~4) | QA 인수 통과율 | 미해결 티켓 (`🚨D` / `🧐R`) | 최근 작업 요약 |
| :--- | :--- :---: | :---: | :---: | :---: | :--- |
| 🏛️ [`00_core_foundation`](./features/00_core_foundation/README.md) | 🟢 Sign-Off | `[■■■■] 4/4` | `3/3 (100%)` | `0 / 0` | 동적 포트/IPC/모델 로더 검증 및 REFACTOR-01 해결 완료 |
| 💾 [`01_indexing_storage`](./features/01_indexing_storage/README.md) | 📐 Planning | `[□□□□] 0/4` | `3/6 (50%)` | `0 / 0` | REFACTOR-01 해결 완료 (타입 일원화, Repo 캡슐화, 예외 로깅) |
| 🔍 [`02_search_curation`](./features/02_search_curation/README.md) | 📐 Planning | `[□□□□] 0/4` | `2/7 (29%)` | `0 / 1` | 거리 임계값 + RRF 랭킹 + 35mm/점수 필터 + 스마트 앨범 Step 1~4 대기 |
| 🤖 [`03_ai_critique`](./features/03_ai_critique/README.md) | 🩹 Debugging | `[■■■■] 4/4` | `11/13 (85%)` | `2 / 6` | UniPercept 취소 미해제(`DEFECT-02`)·VQA 불능(`DEFECT-03`) 및 `REFACTOR` 6건 대기 |
| 📊 [`04_studio_ui_analytics`](./features/04_studio_ui_analytics/README.md) | 📐 Planning | `[■■□□] 2/4` | `3/4 (75%)` | `0 / 2` | 통계 차트 클릭 갤러리 드릴다운(`Click-to-Filter`) Step 3~4 대기 |

*(※ 상태 범례: `📐 Planning` | `🛠️ Implementing` | `🧐 Auditing` | `🧪 QA Testing` | `🩹 Debugging` | `🟢 Sign-Off`)*
*(※ 미해결 티켓: `🚨D` = Open `DEFECT-xx` 개수, `🧐R` = Open `REFACTOR-xx` 개수)*

---

## 🕒 3. 최근 세션 타임라인 (Recent Session Changelog)

- **`[2026-11-06]` `[clean-code-auditor]` [`03_ai_critique`]**: 3개 계층 전수 정적 분석(`tsc`, `vite build`, `pytest` 106종 PASS), 7대 감사 매트릭스 점검 및 UniPercept 런타임 2대 결함 원인 규명 완료 (`d848988` / 비평 중단 시 `asyncio.to_thread` 워커 스레드 레이스/취소 전 재로드로 인한 28GB 메모리 미해제 `DEFECT-02`, `transformers==5.12.1` `return_dict` 중복 인자 충돌로 인한 VQA 100% `TypeError` 및 예외 문자열 은폐 `DEFECT-03`, `CritiqueDocumentModal` Hooks 크래시/PDF XSS 등 `REFACTOR-03~08` 총 `DEFECT 2건`·`REFACTOR 6건` 등록).

- **`[2026-11-05]` `[clean-code-developer]` [`03_ai_critique`]**: Step 4 [UI & Integration] 검증, 마크다운 AST 파서 정규식 보강, 3단 검증 및 위키 승격 병합 완료 (`9081f9c` / `critiqueParser.tsx` 헤더 테마 우선순위 정비 및 제목 바깥 괄호/볼드 정제, `critiqueExporter.ts` 영문 원문 부록 연동, `OriginalEnglishCritiqueCard` 및 `PhotoCritiqueView`/`CritiqueDocumentModal` 회귀 검증, `npx tsc --noEmit` & `npm run build` 통과, 백엔드 106종 회귀 테스트 100% 통과, `spec.md` As-Is 승격 병합 및 Step 1~4 완료 처리).

- **`[2026-11-05]` `[clean-code-developer]` [`03_ai_critique`]**: Step 3 [Domain Service & Logic] 구현 및 3단 검증 완료 (`73a31cf` / UniPercept 단일 패스 지각 앵커 프롬프트 `UNIPERCEPT_VQA_SINGLE_PASS_PROMPT` 및 디코딩 파라미터 정상화, `GemmaAdapter.generate_perceptual_critique` 신설, `_execute_unipercept_critique_pipeline` 직결 개편 및 UniPercept 오류 시 Gemma 4 자율 비평 자동 폴백 연동, 단위 테스트 `TC-CRT-11~13` 통과, 백엔드 106종 및 `npm run build` 100% 통과, verification.md AC 5 100% PASS 갱신).

- **`[2026-11-04]` `[interactive-feature-planner]` [`03_ai_critique`]**: UniPercept 지각 앵커 + Gemma 4 직접 심층 비평 2단계 하이브리드 파이프라인 기획 및 위키 전수 갱신 완료 (`a9b398b` / UniPercept의 VQA 어휘 붕괴/기계적 분해표 결함 해소를 위해 VR 채점 + 단일 패스 3~4문장 지각 앵커 추출로 경량화, Gemma 4가 지각 앵커를 뼈대 삼아 직접 한국어 3대 헤더 리포트를 완성하도록 파이프라인 재설계, 비평 시간 3~5분 ➔ 20~30초 단축 목표, spec.md To-Be/architecture.md/decisions.md ADR-05/verification.md AC 5 및 TC-CRT-11~13 등록 완료).

- **`[2026-11-04]` `[systematic-debugger]` [`03_ai_critique`]**: REFACTOR-02 리팩토링 티켓 해결 완료 (`756e6be` / 비평 추론 어댑터 `chat_service.py`, `mlx_adapters.py`, `unipercept_adapter.py` 내 `except Exception: pass` Silent Fail 전면 제거 및 명시적 로깅 보강, `format_and_structure_critique` 및 `generate_vqa_critiques_3way` 장문 메서드 30줄 가이드 준수 SRP 헬퍼 분리, 백엔드 103종 테스트 및 `npm run build` 100% 통과, `verification.md` REFACTOR-02 RESOLVED 갱신).
- **`[2026-11-04]` `[systematic-debugger]` [`03_ai_critique`]**: REFACTOR-01 리팩토링 티켓 해결 완료 (`1f0151c` / `CritiqueDocumentModal` 1,766줄 ➔ 449줄로 약 75% 경량화, `CritiqueContentRenderer` 856줄 ➔ 109줄 축소, `PhotoCritiqueView`에서 `ScoreHudStrip` 분리, `CritiqueView` 375줄 ➔ 223줄 경량화, `critiqueParser.tsx`/`critiqueExporter.ts`/`useModalZoomPan.ts` 등 12개 전문 서브 모듈 분할 완료, `npm run build` 및 pytest 43건 100% 통과, verification.md REFACTOR-01 RESOLVED 갱신).
- **`[2026-11-03]` `[systematic-debugger]` [`03_ai_critique`]**: DEFECT-01 결함 해결 완료 (`e99482f`, `16aaff0` / 비평 취소/중지 시 Gemma active_requests 가드 해제 force=True 지원, asyncio Task에 task.cancel 신호 전달, PyTorch MPS torch.mps.synchronize() 동기화로 Metal 캐시 즉각 반환, 단위/회귀 테스트 4종 추가 및 8종 통과, verification.md TC-CRT-10 PASS 및 DEFECT-01 RESOLVED 갱신).
- **`[2026-11-03]` `[clean-code-auditor]` [`03_ai_critique`]**: DEFECT-01 결함 발권 (비평 취소/중지 시 Gemma active_requests 가드 버그로 인한 언로드 스킵, torch.mps.synchronize 누락으로 인한 Metal 캐시 반환 지연, asyncio Task에 task.cancel 미전달로 인한 VLM 메모리 잔류 원인 분석 및 수정 계획 수립, verification.md에 TC-CRT-10 FAIL 및 DEFECT-01 티켓 등록, 관제탑 docs/README.md 동기화).
- **`[2026-11-03]` `[systematic-debugger]` [`01_indexing_storage`]**: REFACTOR-01 해결 완료 (`PhotoMetadata` `focal_length_35mm`/`shutter_speed` 프론트엔드 타입 통일, `IndexedFolder`를 `PhotoRepository` 메서드로 캡슐화, 썸네일 캐시 `except Exception: pass` 제거 및 `FileNotFoundError`/`OSError` 로깅 보강, 백엔드 99종 전수 통과 및 `tsc`/`build` PASS).
- **`[2026-11-01]` `[systematic-debugger]` [`00_core_foundation`]**: REFACTOR-01 해결 완료 (`chroma.py`의 `import chromadb`를 `get_chroma_client()` 내부로 지연 이동하여 기동 시 eager import 제거, `base_model.py` 및 `model_downloader.py` 내 빈 `except: pass`에 디버그/경고 로깅 보강하여 Silent Fail 제거, 백엔드 98종 전수 통과, 00_core_foundation `🟢 Sign-Off` 전환).
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
