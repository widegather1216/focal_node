# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🩹 Debugging (DEFECT 전수 해결 완료, REFACTOR 3건 해결 대기)`
- **구현 진척도**: `[■■■■] 4/4 Steps (Active Iteration Step 1~4 구현 완료)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 3건` ([`verification.md`](./verification.md) 참조)
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
- **직전 완료 작업**: `2026-11-07 / systematic-debugger / REFACTOR-06 (UniPercept Eager Import·추론 예외 삼킴·RAW 저해상도 디코딩 및 GPU_LOCK/메모리 누수 교정) 해결 및 회귀 검증 완료 (DEFECT 0건·REFACTOR 3건 대기)`
- **해결 완료 및 잔여 티켓 현황**:
  1. **✅ `DEFECT-02~03` & `REFACTOR-04~06` 해결 완료 (`TC-CRT-10~13 PASS`, `13/13 100%`)**:
     - `DEFECT-02`: `_acquire_model_for_request` 취소 가드로 28GB 디스크 재적재 및 로딩 중 취소 후 메모리 상주 원천 차단, 최외곽 `finally` 언로드 및 `_on_unload()` MPS 텐서 해제
     - `DEFECT-03`: `_load_model_locked()`에서 `self.model.eval()` 명시 호출, `_generate_with_language_model` 헬퍼로 `InternVLChatModel.chat()`의 `return_dict` 시그니처 충돌을 우회하고 `self.model.language_model.generate(...)` 직접 호출 및 `<think>`/종료 토큰 정제, VQA 추론 실패 시 예외 전파(`raise`)
     - `REFACTOR-04`: `CritiqueDocumentModal.tsx` Rules of Hooks 크래시 해소, 전역 키 가드, PDF XSS 이스케이프 및 다크 잉크 컬러 오버라이드
     - `REFACTOR-05`: `AIAnalysis.to_dict()` 11개 필드 보존 반환, `critique_status_manager.clear()` 좀비 상태 차단, `ChatService._cancel_task_threadsafe`, `PhotoRepository` 캡슐화
     - `REFACTOR-06`: 수정 파일 `utils/image.py`, `services/unipercept_utils.py`, `services/unipercept_adapter.py`, `services/mlx_adapters.py`, `services/chat_service.py`, `services/critique_status.py`, `tests/test_refactor_06_hygiene.py` — `unipercept_utils`/`adapter`의 `torch`/`torchvision`/`transformers` Eager Import를 제거하고 `_LazyTorchProxy` 및 `patch_transformers_tied_weights()` 적용(Rule 2.5), `config.CONFIG_DIR` 격리 적용(Rule 2.6), Gemma 추론 및 VQA 예외 삼킴 제거로 DB 오염 차단 및 `status="error"`/자율 폴백 보장, `load_pil_image`에 `min_dimension=1024` 및 `MAX_CONCURRENT_DECODES=3` 세마포어 적용(Rule 2.3), `GemmaAdapter` CPU RAW 디코딩을 `GPU_LOCK` 외부로 분리(Rule 2.4), `generate_full_ensemble_critique`에서 1회 1024px 디코딩 후 VR+VQA 및 Gemma 간 공유, `task.add_done_callback` 고아 태스크 누수 방지, `CritiqueStatusManager` 100개 상한 축출 정책 적용
  2. **🔴 Must Fix 리팩토링 (`REFACTOR-07` — 우선 해결)**:
     - `REFACTOR-07`: 프로덕션 미임포트 허수 테스트(`test_ensemble_math.py`, `TC-CRT-12`) 실검증 전환 및 `/api/chat/*` 누락 라우트 테스트 보강
  3. **🟡 Should Fix (`REFACTOR-03`, `REFACTOR-08`)**: 3중 비평 Polling 타이머 증식·빈 `catch`·캐시 키 불일치 수정 및 ADR-05 이전 사문화 코드(~560줄)·UI 진행률 라벨/`ScoringGuideModal` 포털 보강
- **검증 완료된 테스트 실행 명령어**:
  - `npx tsc --noEmit` (`PASS`)
  - `npm run build` (`PASS`)
  - `./venv/bin/pytest backend/tests/ -v` (`125 passed`)
- **다음 세션 포커스 및 추천 실행 프롬프트**:
  - `REFACTOR-06`이 해결되었으므로, 다음 최우선 `🔴 Must Fix` 티켓인 `REFACTOR-07`(허수 단위 테스트 실검증 전환 및 `/api/chat/*` 라우트 커버리지 보강)을 이어서 해결합니다 (`systematic-debugger`).
  - 👉 추천 프롬프트: `"03_ai_critique 도메인의 REFACTOR-07 티켓 해결해줘"`
