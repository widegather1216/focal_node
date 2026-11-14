# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🩹 Debugging (DEFECT 전수 해결 완료, REFACTOR-08 1건 해결 대기)`
- **구현 진척도**: `[■■■■] 4/4 Steps (Active Iteration Step 1~4 구현 완료)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 1건` ([`verification.md`](./verification.md) 참조)
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
- **직전 완료 작업**: `2026-11-14 / systematic-debugger / REFACTOR-03 해결 완료 (useCritiqueStatusPolling·activePhotoList 분리, 타이머 증식/레이스·빈 catch·any/fetch 우회·['critiques'] 키 불일치 해소 및 300줄 이하 경량화, REFACTOR-08 1건 대기)`
- **해결 완료 및 잔여 티켓 현황**:
  1. **✅ `DEFECT-02~03` & `REFACTOR-03~07` 해결 완료 (`TC-CRT-10~13 PASS`, `13/13 100%`)**:
     - `DEFECT-02`: `_acquire_model_for_request` 취소 가드로 28GB 디스크 재적재 및 로딩 중 취소 후 메모리 상주 원천 차단, 최외곽 `finally` 언로드 및 `_on_unload()` MPS 텐서 해제
     - `DEFECT-03`: `_load_model_locked()`에서 `self.model.eval()` 명시 호출, `_generate_with_language_model` 헬퍼로 `InternVLChatModel.chat()`의 `return_dict` 시그니처 충돌을 우회하고 `self.model.language_model.generate(...)` 직접 호출 및 `<think>`/종료 토큰 정제, VQA 추론 실패 시 예외 전파(`raise`)
     - `REFACTOR-03`: `useCritiqueStatusPolling`·`activePhotoList` 분리로 3중 Polling/`focus` 타이머 증식 및 3.5s/4s 토스트 레이스 차단, `['critiques']` 접두어 조회 및 `usePhotoDetail`↔`usePhotoDetailQuery` 순환 참조 해소, `useAppStore.cancelActiveCritique` `api.cancelCritique` 일원화, `api.ts` 비평/상세 타입 구체화, 빈 `catch` 3곳 제거 및 `PhotoCritiqueView`(288줄)·`usePhotoDetail`(285줄) 경량화
     - `REFACTOR-04`: `CritiqueDocumentModal.tsx` Rules of Hooks 크래시 해소, 전역 키 가드, PDF XSS 이스케이프 및 다크 잉크 컬러 오버라이드
     - `REFACTOR-05`: `AIAnalysis.to_dict()` 11개 필드 보존 반환, `critique_status_manager.clear()` 좀비 상태 차단, `ChatService._cancel_task_threadsafe`, `PhotoRepository` 캡슐화
     - `REFACTOR-06`: `unipercept_utils`/`adapter`의 `torch`/`torchvision`/`transformers` Eager Import 제거(`_LazyTorchProxy`, `patch_transformers_tied_weights()`, Rule 2.5), `config.CONFIG_DIR` 격리(Rule 2.6), Gemma 추론 및 VQA 예외 삼킴 제거로 DB 오염 차단 및 `status="error"`/자율 폴백 보장, `load_pil_image`에 `min_dimension=1024` 및 `MAX_CONCURRENT_DECODES=3` 세마포어(Rule 2.3), `GemmaAdapter` CPU RAW 디코딩 `GPU_LOCK` 외부 분리(Rule 2.4), 1회 1024px 디코딩 공유, `task.add_done_callback` 누수 방지, `CritiqueStatusManager` 100개 상한 정책 적용
     - `REFACTOR-07`: `test_ensemble_math.py`에서 `services.scoring` 실제 4대 광학 가중치/보너스/융합 실검증 전환, `test_unipercept.py`의 `app.services.*` 임포트 통일 및 `TC-CRT-12/13` 실제 어댑터 파이프라인/VQA 실패 시 Gemma 자율 폴백 실실행 검증, `test_critique_repository_and_api.py`에 `POST /api/chat/critique`, `GET /api/chat/critique/status/{id}`, `POST /api/chat/critique-summary` 3대 엔드포인트 커버리지 보강 (132 passed)
  2. **🟡 Should Fix 리팩토링 (`REFACTOR-08` 1건 대기)**:
     - `REFACTOR-08`: ADR-05 이전 레거시 코드(~560줄)·비대 파일(`unipercept_adapter.py` 1,212줄, `mlx_adapters.py` 758줄, `critiqueExporter.ts` 710줄 등) 경량화, Headless MPS `empty_cache` Segfault 가드/테스트 스텁 보강 및 프로그레스/`ScoringGuideModal` 개선
- **검증 완료된 테스트 실행 명령어**:
  - `npx tsc --noEmit` (`PASS`)
  - `npm run build` (`PASS`)
  - `./venv/bin/pytest backend/tests/test_critique_repository_and_api.py backend/tests/test_critique_cancellation.py -q` (샌드박스 비-MPS no-op 호환, `24 passed`)
- **다음 세션 포커스 및 추천 실행 프롬프트**:
  - `REFACTOR-03` 해결 완료로 마지막 잔여 티켓 `REFACTOR-08`만 해결하면 `03_ai_critique` 도메인을 `🟢 Sign-Off`로 전환할 수 있습니다 (`systematic-debugger`).
  - 👉 추천 프롬프트: `"03_ai_critique 도메인의 REFACTOR-08 티켓 해결해줘"`
