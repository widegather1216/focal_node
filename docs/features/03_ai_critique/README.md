# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🩹 Debugging (UniPercept 취소 미해제 DEFECT-02·VQA 불능 DEFECT-03 및 REFACTOR 6건 해결 대기)`
- **구현 진척도**: `[■■■■] 4/4 Steps (Active Iteration Step 1~4 구현 완료)`
- **미해결 티켓 현황**: `🚨 DEFECT: 2건` | `🧐 REFACTOR: 6건` ([`verification.md`](./verification.md) 참조)
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
  - 📂 구현: [`chat_service.py`](../../../backend/app/services/chat_service.py), [`mlx_adapters.py`](../../../backend/app/services/mlx_adapters.py), [`unipercept_adapter.py`](../../../backend/app/services/unipercept_adapter.py), [`ai_parser.py`](../../../backend/app/services/ai_parser.py) | 🧪 테스트: [`test_unipercept.py`](../../../backend/tests/test_unipercept.py) (`TC-CRT-11~13` PASS, 16 passed)
- [x] **Step 4 [UI & Integration]**:
  - 프론트엔드 한/영 원문 토글 카드([`OriginalEnglishCritiqueCard.tsx`](../../../src/components/critique/OriginalEnglishCritiqueCard.tsx)), AST 파서 헤더/테마 보강([`critiqueParser.tsx`](../../../src/utils/critiqueParser.tsx)) 및 마크다운 내보내기 연계([`critiqueExporter.ts`](../../../src/utils/critiqueExporter.ts)) 점검
  - 🧪 검증: `npx tsc --noEmit`, `npm run build` 및 백엔드 106종 전체 회귀 PASS

### ✅ Previous Baseline (As-Is 기구현 완료)
- [x] `ai_analysis` 테이블, 비평 요청/응답/상태 스키마 및 프론트엔드 `CritiqueStatus` 타입
- [x] 온디맨드 비평 생성/Polling/취소/삭제/총평 라우터(`/api/chat/*`) 및 캡션/태그 수동 편집
- [x] UniPercept 3대 정량 평점 및 영문 원문 DB 정규화 & 아카이브 정렬
- [x] EXIF 적응형 4대 가중치, 미학적 탁월성 보너스 연산 모듈 및 점수 가이드 모달
- [x] 상세 패널 비평 뷰, 전체 비평 대시보드, 에디토리얼 매거진 모달/독립 팝아웃 창 및 내보내기

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **Recent Commits**:
  - `9081f9c` - `docs(critique): promote hybrid pipeline spec to As-Is and complete step 4`
  - `a3afb63` - `fix(critique): improve markdown parser header tagging and export English anchor appendix`
  - `73a31cf` - `feat(critique): implement hybrid perceptual anchor critique pipeline`
  - `a9b398b` - `docs(critique): specify hybrid perceptual anchor pipeline with gemma 4 direct critique`
  - `756e6be` - `refactor(critique): eliminate silent fail blocks and decompose long adapter methods`
  - `1f0151c` - `refactor(critique): decompose monolithic critique components for SRP conformance`
- **직전 완료 작업**: `2026-11-06 / clean-code-auditor / 전 계층 7대 매트릭스 감사 및 UniPercept 취소 미해제(DEFECT-02)·VQA 불능(DEFECT-03) 근본 원인 규명 완료 (DEFECT 2건·REFACTOR 6건 대기)`
- **감사 완료 범위 및 핵심 발견 사항**:
  1. **정적 분석기 결과**: `npx tsc --noEmit` (`PASS`), `npm run build` (`PASS`), `./venv/bin/pytest backend/tests/ -v` (`106 passed`), `transformers==5.12.1` `generate` 재현 검증 완료
  2. **🚨 핵심 런타임 결함 (`DEFECT-02~03` — 최우선 해결)**:
     - `DEFECT-02` (`TC-CRT-10 FAIL`): 비평 중단 시 `task.cancel()`이 코루틴만 먼저 종료해 `self.model is None`(로딩 중) 상태에서 빈 `unload_model()`이 실행되거나, `generate_perceptual_anchor_vqa`가 `check_cancelled` 전에 `_load_model_locked()`를 호출해 28GB를 디스크에서 재적재 후 방치함
     - `DEFECT-03` (`TC-CRT-11 FAIL`): `transformers==5.12.1`의 `_prefill(..., return_dict=True)`와 `InternVLChatModel.chat()`의 `return_dict=None` 전달이 충돌하여 VQA가 100% `TypeError`로 실패하고, `#L556-L558` 예외 삼킴으로 인해 `"Perceptual analysis error: ..."` 문자열이 정상 앵커로 위장 저장됨
  3. **🔴 Must Fix 리팩토링 (`REFACTOR-04~07`)**:
     - `REFACTOR-04`: `CritiqueDocumentModal.tsx` 조기 `return null` 이후 `useMemo` 호출로 인한 모달 오픈 즉시 런타임 크래시·전역 키 가로채기 및 PDF 내보내기 미이스케이프 `innerHTML`(XSS)·다크 인라인 색상 역전
     - `REFACTOR-05`: `PATCH /api/photos/{id}/metadata` 응답의 비평/평점 필드 누락(캐시 유실), `DELETE /critique/{id}` 후 인메모리 상태 미삭제 부활, 취소 시 워커 스레드 `task.cancel()` 비스레드안전 호출 및 `PhotoRepository` 우회 쿼리
     - `REFACTOR-06`: `unipercept_adapter`/`unipercept_utils` 상단 `torch`/`transformers` Eager Import(Rule 2.5), Gemma 추론 예외 문자열 반환(DB 오염), RAW 저해상도(`min_dimension=None`)/중복 디코딩 및 `GPU_LOCK`/메모리 누수
     - `REFACTOR-07`: 프로덕션 미임포트 허수 테스트(`test_ensemble_math.py`, `TC-CRT-12`) 실검증 전환 및 `/api/chat/*` 누락 라우트 테스트 보강
  4. **🟡 Should Fix (`REFACTOR-03`, `REFACTOR-08`)**: 3중 비평 Polling 타이머 증식·빈 `catch`·캐시 키 불일치 수정 및 ADR-05 이전 사문화 코드(~560줄)·UI 진행률 라벨/`ScoringGuideModal` 포털 보강
- **검증 완료된 테스트 실행 명령어**:
  - `npx tsc --noEmit` (`PASS`)
  - `npm run build` (`PASS`)
  - `./venv/bin/pytest backend/tests/ -v` (`106 passed`)
- **다음 세션 포커스 및 추천 실행 프롬프트**:
  - 최우선 런타임 결함인 `DEFECT-02`(취소 시 28GB 미해제) 및 `DEFECT-03`(VQA `return_dict` 충돌)부터 순차 해결합니다 (`systematic-debugger`).
  - 👉 추천 프롬프트: `"03_ai_critique 도메인의 DEFECT-02 티켓 해결해줘"`
