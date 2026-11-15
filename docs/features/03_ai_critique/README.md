# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🟢 Sign-Off (모든 구현 및 QA/리팩토링 100% 완료)`
- **구현 진척도**: `[■■■■] 4/4 Steps (Active Iteration Step 1~4 구현 완료)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

2단계 온디맨드 AI 비평(UniPercept 8B 3-Way 채점 + 단일 패스 통합 지각 앵커 ➔ Gemma 4 12B-it 지각 앵커 기반 한국어 직접 심층 비평), 미학 주도형 EXIF 적응적 종합 평점 모델, 정량 평점(`overall`/`iaa`/`iqa`/`ista`) 및 영문 원문(`critique_en`) DB 정규화, 캡션/태그 수동 편집, 백그라운드 비평 상태 Polling/취소/삭제, 포트폴리오 종합 총평 및 에디토리얼 매거진(Markdown/PDF) 내보내기를 담당하는 도메인입니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### 🚀 Active Iteration: UniPercept 지각 앵커 + Gemma 4 직접 심층 비평 하이브리드 파이프라인
- [x] **Step 1 [Schema & Types]**: `[N/A - 기존 DB 컬럼(critique, critique_en, 4종 평점) 및 프론트엔드 타입 100% 호환 재사용]`
- [x] **Step 2 [Data Access & API]**: `[N/A - 기존 POST /api/chat/critique 및 응답 스키마 100% 호환]`
- [x] **Step 3 [Domain Service & Logic]**: 단일 패스 지각 앵커 프롬프트 및 Gemma 4 직접 비평 서비스 파이프라인 구현 완료
  - 📂 구현: [`chat_service.py`](../../../backend/app/services/chat_service.py), [`mlx_adapters.py`](../../../backend/app/services/mlx_adapters.py), [`unipercept_adapter.py`](../../../backend/app/services/unipercept_adapter.py), [`ai_parser.py`](../../../backend/app/services/ai_parser.py) | 🧪 테스트: [`test_unipercept.py`](../../../backend/tests/test_unipercept.py), [`test_refactor_06_hygiene.py`](../../../backend/tests/test_refactor_06_hygiene.py) (`TC-CRT-11~13` PASS, 125 passed)
- [x] **Step 4 [UI & Integration]**:
  - 프론트엔드 한/영 원문 토글 카드([`OriginalEnglishCritiqueCard.tsx`](../../../src/components/critique/OriginalEnglishCritiqueCard.tsx)), AST 파서 헤더/테마 보강([`critiqueParser.tsx`](../../../src/utils/critiqueParser.tsx)) 및 마크다운 내보내기 연계([`critiqueExporter.ts`](../../../src/utils/critiqueExporter.ts)) 점검
  - 🧪 검증: `npx tsc --noEmit`, `npm run build` 및 백엔드 125종 전체 회귀 PASS

### ✅ Previous Baseline (As-Is 기구현 완료)
- [x] `ai_analysis` 테이블, 비평 요청/응답/상태 스키마 및 프론트엔드 `CritiqueStatus` 타입
- [x] 온디맨드 비평 생성/Polling/취소/삭제/총평 라우터(`/api/chat/*`) 및 캡션/태그 수동 편집
- [x] UniPercept 3대 정량 평점 및 영문 원문 DB 정규화 & 아카이브 정렬
- [x] EXIF 적응형 4대 가중치, 미학적 탁월성 보너스 연산 모듈 및 점수 가이드 모달
- [x] 상세 패널 비평 뷰, 전체 비평 대시보드, 에디토리얼 매거진 모달/독립 팝아웃 창 및 내보내기

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **Recent Commits**:
  - `c35be11` - `refactor(ui): split critique modals/exporters and fix progress labels`
  - `a92fb93` - `test(critique): add mps guard tests, mlx stubs, and adr-05 assertions`
  - `80f7f0f` - `refactor(critique): guard headless mps cache and modularize adapters`
  - `8231646` - `refactor(critique): unify status polling and enforce strict api types`
  - `3d9ddeb` - `test(critique): replace hollow tests with real scoring and chat api tests`
  - `e8a5e0f` - `docs(critique): mark REFACTOR-06 resolved and sync control tower`
  - `e53f9b4` - `refactor(critique): eliminate eager imports, silent errors, and redundant raw decoding`
  - `caaa345` - `docs(critique): mark REFACTOR-05 resolved and sync control tower`
  - `5d55cea` - `refactor(critique): encapsulate photo repository queries and fix metadata/cancel state bugs`
  - `1334e8b` - `docs(critique): mark REFACTOR-04 resolved and sync control tower`
  - `46bbb48` - `fix(critique): resolve modal hook ordering crash and harden pdf export`
  - `39dc215` - `docs(critique): mark DEFECT-03 resolved and update control tower`
  - `4fa3497` - `fix(critique): bypass internvl chat return_dict collision and propagate vqa errors`
  - `f430dbd` - `docs(critique): mark DEFECT-02 resolved and sync control tower`
  - `d2ec389` - `fix(critique): prevent unipercept 28gb memory leak and reload race on cancel`
  - `d848988` - `docs(critique): record code audit matrix findings and register defect tickets`
  - `9081f9c` - `docs(critique): promote hybrid pipeline spec to As-Is and complete step 4`
  - `a3afb63` - `fix(critique): improve markdown parser header tagging and export English anchor appendix`
  - `73a31cf` - `feat(critique): implement hybrid perceptual anchor critique pipeline`
  - `a9b398b` - `docs(critique): specify hybrid perceptual anchor pipeline with gemma 4 direct critique`
  - `756e6be` - `refactor(critique): eliminate silent fail blocks and decompose long adapter methods`
  - `1f0151c` - `refactor(critique): decompose monolithic critique components for SRP conformance`
- **Working Tree State**: 🟢 Clean (No uncommitted changes)
- **직전 완료 작업**: `2026-11-15 / systematic-debugger / REFACTOR-08 해결 완료 (Headless 비-MPS torch.mps Segfault 가드·conftest.py mlx_vlm 스텁·ADR-05 레거시 제거·백엔드/프론트엔드 비대 파일 <=300줄 분할·진행률/점수 가이드 모달 교정, 03_ai_critique 🟢 Sign-Off 전환)`
- **해결 완료 및 잔여 티켓 현황**:
  1. **✅ `DEFECT-01~03` & `REFACTOR-01~08` 전수 해결 완료 (`15/15 100%`, 미해결 0건)**:
     - `DEFECT-02~03` & `REFACTOR-03~07`: 취소 시 28GB 누수·`return_dict` 충돌·Polling 타이머 증식·Hooks 크래시·메타데이터 보존·Eager Import·실검증 전환 완료
     - `REFACTOR-08`: `base_model.clear_mps_cache`/`clear_mlx_cache` 가드 및 `conftest.py` 헤드리스 `mlx_vlm` 스텁/`test_mps_guard.py` 5종 추가, `chat_service.py` `MagicMock` 분기·인자 순서 버그 및 폐기된 2단계 번역/3-Way VQA/사문화 파서 제거, `critique_prompts.py`·`siglip_adapter.py`·`unipercept_runtime.py`·`critique_db_helpers.py` 분할(백엔드 수정/신설 11개 파일 함수 `<=30줄`·`data/info/temp/res` 0건), 프론트엔드 6대 비대 파일 `<=300줄` 분할(`critiquePrintTemplate.ts`·`critiqueExportHelpers.ts`·`critiqueMarkdownParser.ts`·`ScoringGuideContent.tsx`·`CritiqueCardHeader.tsx`·`CritiqueToolbarExportMenu.tsx`·`useCritiqueDocumentModal.ts`), 진행률 역행(`15%->10%`)/`[1/6]` 라벨 교정, `ScoreHudStrip`/`CritiqueDocumentArticle` 가이드 버튼 연결 및 `ScoringGuideModal` `createPortal`·캡처 `Escape` 격리 적용
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/ -q` (`151 passed`)
  - `./venv/bin/pytest backend/tests/test_mps_guard.py backend/tests/test_unipercept.py backend/tests/test_critique_cancellation.py backend/tests/test_refactor_06_hygiene.py -v` (`37 passed`)
  - `npx tsc --noEmit && npm run build` (`PASS`)
  - `python3 -B /Users/kimbeomjun/.gemini/config/skills/interactive-feature-planner/scripts/check_wiki_health.py docs` (`exit 0`)
- **다음 세션 포커스 및 추천 실행 프롬프트**:
  - `03_ai_critique` 도메인은 `🟢 Sign-Off` 상태입니다. 다음 잔여 리팩토링 도메인(`02_search_curation` `REFACTOR-01` 또는 `04_studio_ui_analytics` `REFACTOR-01`)을 진행하십시오.
  - 👉 추천 프롬프트: `"02_search_curation 도메인의 REFACTOR-01 티켓 해결해줘"`
