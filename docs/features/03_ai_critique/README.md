# 🤖 [03_ai_critique] On-Demand AI Critique & Editorial Export

- **현재 상태 (Lifecycle)**: `🧐 Auditing (UniPercept 지각 앵커 + Gemma 4 직접 심층 비평 전 계층 Step 1~4 구현 및 3단 검증 완료)`
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
- **직전 완료 작업**: `2026-11-05 / clean-code-developer / Step 4 [UI & Integration] 검증, 마크다운 AST 파서 정규식/테마 패턴 보강, 3단 검증(tsc, build, pytest 106종) PASS 및 위키 승격 병합 완료`
- **구현된 핵심 사항**:
  1. `critiqueParser.tsx`: 6-Way 스코어보드 추출 폴백 추가, `determineThemeType` 테마 분류 우선순위(`defect` 및 `advice` 우선 매칭으로 결함 섹션 태깅 정상화), 섹션 제목 바깥 대괄호 `[...]` 및 볼드 `**...**` 정제 유틸 추가
  2. `critiqueExporter.ts`: 마크다운 리포트 내보내기 시 `photo.ai_analysis.critique_en` 부록 자동 첨부 연계
  3. `PhotoCritiqueView.tsx` / `CritiqueDocumentModal.tsx` / `OriginalEnglishCritiqueCard.tsx`: UniPercept 8B VQA 영문 앵커 토글 및 3대 표준 헤더 AST 마크다운 렌더링 정상 동작 확인
  4. 3단 검증: `npx tsc --noEmit` 통과, `npm run build` 번들 빌드 성공, `./venv/bin/pytest backend/tests/ -v` 106종 전체 회귀 100% 통과
- **검증 완료된 테스트 실행 명령어**:
  - `npx tsc --noEmit` (`PASS`)
  - `npm run build` (`PASS`)
  - `./venv/bin/pytest backend/tests/ -v` (`106 passed`)
- **다음 세션 포커스 및 추천 실행 프롬프트**:
  - `03_ai_critique` 도메인의 클린코드 품질 감사를 진행합니다.
  - 👉 추천 프롬프트: `"03_ai_critique 도메인 클린코드 품질 감사 진행해줘"`
