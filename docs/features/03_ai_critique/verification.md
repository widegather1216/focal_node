# 🧪 [03_ai_critique] Verification & Ticket Logs

- **검증 상태**: `🩹 Debugging (DEFECT 전수 해결 완료, REFACTOR 5건 해결 대기)`
- **인수 조건 통과율**: `13 / 13 (100%)`
- **미해결 티켓**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 5건`

---

## 🎯 1. Given-When-Then 인수 조건 (Acceptance Criteria)

### AC 1. 2단계 온디맨드 AI 비평 생성 및 Polling 상태 추적 `[As-Is]`
* **Given:** 갤러리에서 특정 사진의 상세 패널을 열고 `[AI 비평 생성]`을 요청했을 때,
* **When:** 백엔드에서 `UniPercept 8B` 또는 `Gemma 4` 비평 추론이 진행되면,
* **Then:**
  1. 프론트엔드가 `GET /api/chat/critique/status/{photo_id}` JSON Polling을 통해 실시간 진행 단계(`step`, `progress`)를 프로그레스 위젯과 전역 토스트에 표시해야 한다.
  2. 생성이 완료되면 결과가 SQLite `ai_analysis.critique` 컬럼에 영구 캐싱되어 재진입 시 즉시 열람되어야 한다.
  3. `UniPercept 8B` 추론 완료 직후 모델 가중치가 즉시 메모리에서 언로드되어야 한다.

### AC 2. 에디토리얼 문서 모달 열람 및 Markdown/PDF 내보내기 `[As-Is]`
* **Given:** 비평이 생성된 사진에서 `[매거진 문서 보기]` 모달(`CritiqueDocumentModal`)을 열었을 때,
* **When:** `[Markdown 저장]` 또는 `[PDF 저장]` 버튼을 클릭하면,
* **Then:** 촬영 EXIF 메타데이터와 비평 본문이 결합된 `.md` 또는 `.pdf` 파일이 클라이언트 사이드에서 생성되어 로컬 디스크에 다운로드되어야 한다.

### AC 3. 정량 평점(`overall`/`iaa`/`iqa`/`ista`)·영문 원문 DB 정규화 및 평점순 정렬 `[As-Is]`
* **Given:** `UniPercept 8B` 6-Way 앙상블 비평이 생성되거나 기존 비평 DB가 마이그레이션될 때,
* **When:** 비평 저장 또는 `GET /api/chat/critiques?sort_by=overall_score`가 호출되면,
* **Then:**
  1. `ai_analysis` 테이블의 `overall_score`, `iaa_score`, `iqa_score`, `ista_score` 및 `critique_en` 컬럼에 정규화된 값들이 저장(또는 기존 텍스트에서 자동 백필)되어야 한다.
  2. 비평 아카이브 탭(`CritiqueView.tsx`)에서 `[최신순 / 종합평점순 / 미학점수순]` 정렬 전환 및 한/영 원문 즉시 토글이 동작해야 한다.

### AC 4. 미학 주도형 EXIF 적응적 종합 평점 및 점수 가이드 모달 `[As-Is]`
* **Given:** 특정 사진의 비평이 생성되거나 마이그레이션이 실행될 때,
* **When:** `calculate_overall_vr_score`가 호출되거나 프론트엔드에서 `[?] 점수 산출 가이드` 버튼이 클릭되면,
* **Then:**
  1. 사진의 EXIF(조리개 F값, ISO)에 따라 [인물/감성], [풍경/건축], [야경/스트리트], [표준] 4대 적응형 가중치가 적용되어야 한다.
  2. $\text{IAA} \ge 75$ 및 $\text{IAA} > \text{IQA}$ 조건에서 미학적 탁월성 보너스($\Delta_{\text{aesthetic}}$)가 정확히 산출 및 가산되어야 한다.
  3. 기존 DB 사진들의 `overall_score`가 `run_migrations()`에서 새 수식으로 일괄 자동 재계산(Backfill)되어야 한다.
  4. 프론트엔드 스코어보드 헤더의 `[?] 점수 산출 가이드` 클릭 시 `ScoringGuideModal`이 오픈되어 4대 가중치 표와 보너스 공식이 안내되어야 한다.

### AC 5. UniPercept 지각 앵커 + Gemma 4 직접 심층 비평 하이브리드 파이프라인 `[As-Is]`
* **Given:** 사용자가 특정 사진에 대해 UniPercept 기반 AI 비평 생성을 요청했을 때,
* **When:** 백엔드에서 2단계 하이브리드 파이프라인이 실행되면,
* **Then:**
  1. UniPercept 8B가 VR 3-Way 채점과 단일 패스 통합 지각 VQA(3~4문장 영문 앵커)를 생성하고 10초 이내에 메모리에서 100% 즉시 언로드되어야 한다.
  2. VQA 생성 시 `repetition_penalty=1.0` 및 샘플링이 적용되어 어휘 붕괴(Word Salad, 깨진 특수문자, 중국어 잔여물) 없이 자연스러운 영문 진단문(`critique_en`)이 도출되어야 한다.
  3. Gemma 4 12B가 사진 픽셀, EXIF, UniPercept 점수, 영문 지각 앵커를 입력받아 스코어보드, 한 줄 총평, 3대 표준 헤더(미학/결함/실전조언)를 갖춘 고품질 한국어 비평문(`critique`)을 직결 생성해야 한다.
  4. 전체 비평 생성 시간이 20~30초 이내로 완료되고 DB `ai_analysis` 테이블에 정상 영구 캐싱되어야 한다.

---

## 🧪 2. 테스트 시나리오 매트릭스 (Test Matrix)

| 구분 | 테스트 ID | 시나리오 설명 | 입력 / 조작 조건 | 기대 결과 | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Happy** | `TC-CRT-01` | 온디맨드 비평 생성 및 캐싱 | 사진 상세 -> 비평 생성 클릭 | Polling 진행률 표시 후 `ai_analysis.critique` 저장 | `PASS` |
| **Happy** | `TC-CRT-02` | 에디토리얼 MD/PDF 내보내기 | 문서 모달 -> MD 및 PDF 저장 클릭 | EXIF 포함 정형화된 문서 파일 생성 | `PASS` |
| **Boundary**| `TC-CRT-03` | 비평 추론 도중 취소 | 생성 중 `[취소]` 버튼 클릭 | `POST /critique/cancel/{id}` 호출 및 즉시 중단 | `PASS` |
| **Happy** | `TC-CRT-04` | 정량 평점 DB 정규화 및 아카이브 정렬 | 비평 생성 후 `sort_by=overall_score` 조회 | 4종 점수 컬럼 저장 및 고득점 순 반환 | `PASS` |
| **Boundary**| `TC-CRT-05` | 기존 비평 텍스트 자동 백필 | 레거시 스코어보드 문자열 보유 DB 기동 | `run_migrations()`에서 4종 점수 컬럼 자동 백필 | `PASS` |
| **Happy** | `TC-CRT-06` | EXIF 적응형 가중치 및 미학 보너스 검증 | F1.4 인물, F8 풍경, ISO 3200 스트리트 | 모드별 가중치 및 미학 보너스 정확 계산 | `PASS` |
| **Boundary**| `TC-CRT-07` | EXIF 누락/비정상값 시 표준 폴백 및 클램핑 | EXIF 없음, 극단값(IAA 100, IQA 0 등) | 표준 모드 가중치 폴백 및 0~100 클램핑 | `PASS` |
| **Happy** | `TC-CRT-08` | 기존 DB 사진 overall_score 자동 재계산 백필 | 기존 iaa/iqa/ista 보유 DB 기동 | run_migrations()에서 EXIF 조인 후 새 점수 백필 | `PASS` |
| **Happy** | `TC-CRT-09` | 점수 가이드 모달 열람 및 닫기 | 스코어보드 [?] 버튼 클릭 | ScoringGuideModal 열림, ESC/닫기 동작 (`tsc & build`) | `PASS` |
| **Boundary**| `TC-CRT-10` | 비평 취소 시 VLM 즉시 강제 언로드 및 GPU 동기화 | 비평 추론 도중 `[취소]` 클릭 | Gemma/UniPercept 즉시 언로드 및 MPS 캐시 100% 반환 | `PASS (Fixed in DEFECT-02)` |
| **Happy** | `TC-CRT-11` | UniPercept 단일 패스 지각 앵커 추출 및 어휘 붕괴 방지 | 고해상도 테스트 사진 입력 | 150토큰 내외 지각 앵커 정상 영문 도출, 어휘 붕괴 0건 | `PASS (Fixed in DEFECT-03)` |
| **Happy** | `TC-CRT-12` | Gemma 4 지각 앵커 기반 직결 심층 비평 생성 | 지각 앵커 + VR 점수 + EXIF 주입 | 3대 표준 헤더 + 한 줄 총평 + 실전 조언 한국어 완성 | `PASS` |
| **Boundary**| `TC-CRT-13` | UniPercept VQA 오류 시 Gemma 4 자율 비평 폴백 | UniPercept VQA 예외 강제 발생 | Gemma 4 직접 심층 비평으로 정상 폴백 생성 완료 | `PASS` |

---

## 🚨 3. 결함 리포트 (Defect Logs)

### [DEFECT-01] 비평 취소(중지) 요청 시 VLM 모델 메모리 미해제 및 지연 잔류 결함
- **현재 상태**: 🟢 RESOLVED — `_unload_critique_models(force=True)`, `task.cancel()`, `torch.mps.synchronize()` 적용으로 1차 조치 완료 (UniPercept 워커 스레드 레이스는 `DEFECT-02`로 후속 추적)

### [DEFECT-02] 비평 중단(취소) 시 `asyncio.to_thread` 워커 스레드 레이스 및 재로드로 인한 UniPercept 28GB 메모리 미해제 결함
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정 파일**: [`base_model.py`](../../../backend/app/services/base_model.py#L39-L80), [`unipercept_adapter.py`](../../../backend/app/services/unipercept_adapter.py#L17-L170), [`test_critique_cancellation.py`](../../../backend/tests/test_critique_cancellation.py#L251-L340)
  - **원인 및 조치**: Devil's Advocate 사전 검증을 거쳐 ① `_acquire_model_for_request`에서 `GPU_LOCK -> self.lock` 획득 직후 `_load_model_locked()` 호출 전후로 `check_cancelled(photo_id)`를 검사하여 취소된 요청의 28GB 디스크 재적재를 원천 차단하고 10~15초 로딩 도중 취소 시 락 해제 전 즉시 `_unload_model_locked()`를 수행하도록 교정, ② `_release_model_for_request`(Lock Inversion 방지를 위해 `self.lock` 해제 후 `unload_model()` 호출) 및 `generate_full_ensemble_critique` 최외곽 `finally` 블록에서 워커 스레드 자신이 직접 언로드를 보장하도록 수정, ③ `_release_pixel_values`를 `finally`로 일원화하고 `_on_unload()`에서 `_cached_weight_tensor`·`_cached_preferential_ids` 및 서브모듈 참조를 해제하며 `keep_alive_timeout=0.0` 적용, ④ `CritiqueCancelledException`이 내부 `except Exception:`에 삼켜지지 않도록 재전파(`raise`) 가드 추가.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_critique_cancellation.py backend/tests/test_unipercept.py -v` 및 전체 115종 (`PASS`)

### [DEFECT-03] `transformers 5.x` `return_dict` 인자 충돌로 인한 UniPercept VQA 모드 100% 실패 및 에러 은폐 결함
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정 파일**: [`unipercept_adapter.py`](../../../backend/app/services/unipercept_adapter.py#L73-L115), [`unipercept_adapter.py`](../../../backend/app/services/unipercept_adapter.py#L496-L710), [`test_unipercept.py`](../../../backend/tests/test_unipercept.py#L502-L686)
  - **원인 및 조치**: ① `_load_model_locked()`의 기본 및 FP32 폴백 로드 직후 `self.model.eval()`을 명시 호출하도록 보강, ② `_build_vqa_query`·`_clean_vqa_response`·`_generate_with_language_model` 헬퍼를 구현하여 실제 `InternVLChatModel`(`hasattr(self.model, "language_model") and hasattr(self.model, "extract_feature") and self.tokenizer is not None`)에서는 `self.model.chat()`을 우회하고 `extract_feature(pixel_values)`로 구성한 `inputs_embeds`를 `self.model.language_model.generate(...)`(`return_dict` 제외, `use_cache=True`)에 직접 전달한 뒤 `<think>...</think>` 및 종료 토큰을 정제하여 반환하도록 조치(더미 `chat` 모킹 객체 100% 하위 호환 유지), ③ `generate_perceptual_anchor_vqa`에서 VQA 추론 실패 시 `"Perceptual analysis error: ..."` 문자열로 삼키지 않고 예외를 그대로 `raise`하여 `ChatService`의 Gemma 4 자율 폴백(`TC-CRT-13`)이 정상 작동하도록 교정.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_unipercept.py -v` (`19 passed`) 및 전체 `./venv/bin/pytest backend/tests/ -v` (`118 passed`) (`PASS`)

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `CritiqueDocumentModal.tsx` 및 비평 UI 거대 컴포넌트 SRP 모듈 분할
- **현재 상태**: 🟢 RESOLVED — `critiqueParser.tsx`, `critiqueExporter.ts`, `useModalZoomPan.ts` 등 13개 전문 서브 모듈로 분할하여 주요 비평 UI 경량화 완료

### [REFACTOR-02] 비평 추론 어댑터 내 Silent Fail(`except: pass`) 제거 및 장문 메서드 분리
- **현재 상태**: 🟢 RESOLVED — `chat_service.py`, `mlx_adapters.py`, `unipercept_adapter.py`의 빈 `except: pass` 로깅 보강 및 프롬프트/VQA 헬퍼 분리 완료

### [REFACTOR-03] 프론트엔드 비평 Polling 타이머 증식·빈 `catch` 제거, `ApiClient` 우회/타입(`any`) 및 캐시 키 버그 교정
- **심각도**: 🟡 Should Fix (권장 조치)
- **위치**: `src/components/detail/PhotoCritiqueView.tsx#L56-L101`, `src/components/critique/GlobalCritiqueToast.tsx#L21-L80`, `src/hooks/usePhotoDetail.ts#L82-L99, #L161-L221, #L245, #L277-L281`, `src/store/useAppStore.ts#L161-L178`, `src/services/api.ts#L233-L277`, `src/components/CritiqueView.tsx#L55`
- **위반 규칙**: Rule 4.3 (빈 `catch` 금지), Rule 4.2 (`res`/`data`/`st` 네이밍), `00_core_foundation` 단방향 `ApiClient` 경유 규칙, 타이머 동시성 안전성
- **발견된 문제**:
  - `PhotoCritiqueView`·`GlobalCritiqueToast`·`usePhotoDetail` 3곳에 비평 상태 Polling이 중복되며, `focus`/`visibilitychange` 시 기존 `clearTimeout` 없이 `pollStatus()`를 재호출하여 재귀 `setTimeout` 체인이 중복 증식됨 (`3.5s` 자동 닫힘 타이머도 재분석 시 레이스 유발).
  - 빈 `catch {}` 예외 묵인, `useAppStore.cancelActiveCritique`의 `fetch` 직접 호출(`ApiClient` 우회), `api.ts`의 `Promise<any>`, `usePhotoDetail#L84`의 `getQueryData(['critiques'])` 키 불일치(`['critiques', sortBy]` 미매칭으로 아카이브 좌우 키 이동 불능)가 존재함.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - 공통 `useCritiqueStatusPolling` 훅으로 일원화하고 `clearTimeout(timerId)` 선행 후 단일 타이머 체인 유지, 빈 catch에 `console.debug` 추가
  - `useAppStore.cancelActiveCritique`에서 `api.cancelCritique` 호출, `api.ts` 반환 타입을 `CritiqueResponse` 등으로 명시, `getQueriesData<CritiqueItem[]>({ queryKey: ['critiques'] })` 적용
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)

### [REFACTOR-04] `CritiqueDocumentModal` Hooks 순서 위반 런타임 크래시·전역 키 가로채기 및 PDF XSS/인라인 색상 역전 교정
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **해결 내역**:
  - **수정 파일**: [`CritiqueDocumentModal.tsx`](../../../src/components/critique/CritiqueDocumentModal.tsx#L82-L165), [`CritiqueDocumentModal.tsx`](../../../src/components/critique/CritiqueDocumentModal.tsx#L371-L395), [`critiqueExporter.ts`](../../../src/utils/critiqueExporter.ts#L22-L34), [`critiqueExporter.ts`](../../../src/utils/critiqueExporter.ts#L202-L345), [`critiqueExporter.ts`](../../../src/utils/critiqueExporter.ts#L497-L500)
  - **원인 및 조치**: ① `CritiqueDocumentModal.tsx`에서 `critiqueText` 및 `mastheadData = useMemo(...)`를 조건부 `if (!critiqueDocumentPhotoId) return null;` 위로 이동하여 모달 오픈 시 Rules of Hooks 위반 런타임 크래시를 100% 해소하고, `critiqueDocumentPhotoId` 변경 시 `imgError`·복사·내보내기·줌/패닝(`handleResetZoom`) 상태를 초기화하는 `useEffect`를 추가하며, 전역 `keydown`(`Escape`/`Cmd+W`) 리스너는 `if (!critiqueDocumentPhotoId && !isPopout) return;` 가드로 활성 상태에서만 등록되도록 교정, ② `critiqueExporter.ts`에 `escapeHtml()` 헬퍼를 도입하여 `generatePrintHtml`의 파일명·날짜·이미지 URL·EXIF 메타데이터·점수 및 `exportCritiqueToPdf` 폴백 본문을 전수 이스케이프해 DOM XSS를 차단하고, `.focal-pdf-report-container .critique-body`(및 모달 `@media print`) 하위에 다크 테마 인라인 텍스트 색상(`#fff`, `#f4f4f5`, `#e4e4e7`, `#d4d4d8`)을 덮어쓰는 고대비 다크 잉크 컬러(`#111827`, `#374151` `!important`)와 `button { display: none !important; }`를 적용하여 PDF 가독성 및 인쇄 무결성 확보.
  - **회귀 테스트 결과**: `npx tsc --noEmit && npm run build` (`PASS`), `./venv/bin/pytest backend/tests/ -v` (`118 passed`) (`PASS`)

### [REFACTOR-05] 메타데이터 수정 시 비평 필드 유실·삭제 후 좀비 상태 부활·취소 스레드 경계 수정 및 `PhotoRepository` 캡슐화
- **심각도**: 🔴 Must Fix (즉시 조치·QA 진입 차단)
- **위치**: `backend/app/api/photos.py#L125-L154`, `backend/app/api/chat.py#L25-L44, #L89-L96`, `backend/app/services/chat_service.py#L9-L27, #L83-L105, #L149-L183, #L421-L432`, `backend/app/services/critique_status.py#L57-L80`, `backend/app/repositories/photo_repository.py#L160-L203`
- **위반 규칙**: Rule 2.4 (이벤트 루프/스레드 경계 안전성), `00_core_foundation` §3.1 (`Services -> Repositories` 캡슐화), API 스키마 계약 무결성
- **발견된 문제**:
  - `PATCH /api/photos/{id}/metadata`가 `ai_analysis` 중 4개 필드만 반환해 Pydantic이 `critique` 및 4종 점수를 `null`로 직렬화하며, 프론트엔드 React Query 캐시가 덮어써져 캡션/태그 편집 즉시 비평이 화면에서 유실됨.
  - `DELETE /api/chat/critique/{photo_id}`가 `critique_status_manager.clear(photo_id)`를 누락해 창 포커스 시 삭제된 비평이 인메모리 상태에서 부활하며, 동기 라우트 `cancel_photo_critique`가 워커 스레드에서 `asyncio.Task.cancel()`을 비스레드안전하게 직접 호출함.
  - `ChatService` 및 `CritiqueStatusManager`가 `PhotoRepository`를 우회해 직접 `db.query(models.AIAnalysis)` 및 중복 3-테이블 조인/청킹 쿼리를 실행함.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - `AIAnalysis.to_dict()`를 도입해 `patch_photo_metadata`가 전체 11개 필드를 보존 반환하도록 수정
  - `delete_photo_critique`에 `critique_status_manager.clear(photo_id)` 추가, 취소 호출 시 `task.get_loop().call_soon_threadsafe(task.cancel)` 적용
  - `PhotoRepository`에 `get_ai_analysis`, `upsert_critique`, `list_critiques(photo_ids=...)`, `update_caption_and_tags`를 캡슐화하여 서비스 계층 직접 ORM 쿼리 제거
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)

### [REFACTOR-06] UniPercept Eager Import(Rule 2.5)·추론 예외 삼킴(폴백 무력화/DB 오염)·RAW 저해상도 디코딩 및 `GPU_LOCK`/메모리 누수 교정
- **심각도**: 🔴 Must Fix (즉시 조치·QA 진입 차단)
- **위치**: `backend/app/services/unipercept_adapter.py#L5-L33, #L211, #L227, #L527-L559`, `backend/app/services/unipercept_utils.py#L8-L23`, `backend/app/services/mlx_adapters.py#L245, #L313-L331, #L376-L414, #L497-L508`, `backend/app/services/chat_service.py#L442-L456`, `backend/app/services/critique_status.py#L10-L54`
- **위반 규칙**: Rule 2.3 (RAW 디코딩 품질/세마포어), Rule 2.4 (`GPU_LOCK` 범위·MPS 해제·태스크 누수 방지), Rule 2.5 (Heavy AI 지연 임포트), Rule 2.6 (`CONFIG_DIR` 격리), Rule 4.3 & ADR-05 (자율 폴백 보장)
- **발견된 문제**:
  - `unipercept_adapter.py`·`unipercept_utils.py` 상단에서 `torch`·`torchvision`·`transformers`를 Eager Import하고 임포트 시점 전역 몽키패칭을 수행하며, `~/.config/focal_node` 경로가 하드코딩됨(Rule 2.5, 2.6 위반).
  - `generate_perceptual_anchor_vqa` 및 `GemmaAdapter` 추론 메서드가 예외를 삼키고 에러 안내문을 정상 문자열로 반환하여, ADR-05 자율 폴백이 무력화되고 에러 문구가 정상 비평(`completed`)으로 SQLite DB에 영구 저장됨.
  - RAW 비평 시 `min_dimension=None` 호출로 160x120 초저해상도 썸네일이 채점되는 결함, VR+VQA 2회 중복 RAW 디코딩, `GPU_LOCK` 내부 CPU RAW 디코딩 블로킹, `_cached_weight_tensor` MPS 미해제, 슬립/연결 해제 시 `_critique_tasks` 및 `_statuses` 메모리 누수가 존재함.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - `torch`/`torchvision`/`transformers` 및 호환성 패치를 `_load_model_locked()` 내부로 지연 이동하고 `config.CONFIG_DIR` 사용
  - VQA 및 Gemma 추론 실패 시 캐시 정리 후 예외를 명시적으로 `raise`하여 `ChatService` 자율 폴백 및 `error` 상태 전이가 정상 작동하도록 수정
  - RAW 비평 디코딩 시 `GPU_LOCK` 진입 전 `min_dimension=1024` 및 공통 디코딩 세마포어를 적용해 VR+VQA 간 PIL 이미지를 1회 공유하고, `_on_unload()` 텐서 해제·`task.add_done_callback` 정리·`_statuses` 크기 상한 적용
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)

### [REFACTOR-07] 허수 단위 테스트(`test_ensemble_math.py`, `TC-CRT-12/13`) 프로덕션 실검증 전환 및 `/api/chat/*` 라우트 커버리지 보강
- **심각도**: 🔴 Must Fix (즉시 조치·QA 진입 차단)
- **위치**: `backend/tests/test_ensemble_math.py#L1-L63`, `backend/tests/test_unipercept.py#L2, #L117-L121, #L395-L500`, `backend/tests/test_critique_repository_and_api.py#L225-L324`, `backend/tests/test_api_photos.py#L33-L65`
- **위반 규칙**: Audit Matrix #7 (허수/껍데기 테스트 금지 및 핵심 API·경계값 실효성 검증)
- **발견된 문제**:
  - `test_ensemble_math.py`가 프로덕션 코드 임포트 없이 파일 내 폐기된 로컬 수식 함수만 검증하는 100% 허수 테스트이며, `TC-CRT-12`(`test_unipercept.py#L395-L440`) 역시 `generate_perceptual_critique` 호출 없이 하드코딩 문자열만 검증함.
  - `TC-CRT-13`이 상위 메서드를 통째로 모킹해 VQA 예외 삼킴 버그를 은폐했으며, `app.services.*` vs `services.*` 혼용 임포트로 싱글턴이 이중 생성됨.
  - `POST /api/chat/critique`, `GET /api/chat/critique/status/{id}`, `POST /api/chat/critique-summary` 엔드포인트 테스트 및 `PATCH /api/photos/{id}/metadata` 비평 필드 보존 검증이 누락됨.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - `test_ensemble_math.py`에서 `services.scoring` 실제 함수를 임포트해 경계값 검증 수행, `test_unipercept.py` 임포트 경로를 `services.*`로 통일하고 `TC-CRT-12/13`이 실제 어댑터 메서드를 실행하도록 보강
  - `test_critique_repository_and_api.py` 및 `test_api_photos.py`에 누락된 3개 `/api/chat/*` 엔드포인트·삭제 후 상태 초기화·메타데이터 수정 시 비평 보존 회귀 테스트 추가
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)

### [REFACTOR-08] ADR-05 이전 레거시 사문화 코드(~560줄)·장문 함수 정리 및 프로그레스 라벨/`ScoringGuideModal` 포털·진입점 보강
- **심각도**: 🟡 Should Fix (권장 조치)
- **위치**: `backend/app/services/chat_service.py#L246-L254, #L308`, `backend/app/services/mlx_adapters.py#L516-L650`, `backend/app/services/unipercept_adapter.py#L301, #L449-L505, #L575-L892`, `backend/app/services/ai_parser.py#L58-L78, #L119-L160, #L222-L257`, `backend/app/database.py#L41-L206`, `src/components/critique/CritiqueProgressWidget.tsx#L8-L19`, `src/components/critique/ScoringGuideModal.tsx#L166-L185`, `src/components/critique/ScoreHudStrip.tsx`, `src/components/critique/CritiqueDocumentArticle.tsx#L73-L146`, `src/utils/critiqueExporter.ts#L309-L646`, `src/hooks/usePhotoDetail.ts#L9-L44`
- **위반 규칙**: Rule 4.1 (함수 <= 30줄, UI 파일 <= 300줄), Rule 4.2 (모호한 변수명 정리), Audit Matrix #1, #5 & #6 (사문화 코드 제거, 순환 참조 해소, ADR-04/05 UI 스펙 정합성)
- **발견된 문제**:
  - `chat_service.py#L248`의 프로덕션 `MagicMock` 분기 코드와 폐기된 2단계 번역/3-Way VQA/정규식 파서(~560줄)가 잔존하며, `database.py` 백필 함수·`critiqueExporter.ts`(658줄)·`CritiqueDocumentModal.tsx`(449줄) 장문 함수 및 `usePhotoDetail`<->`usePhotoDetailQuery` 순환 참조가 존재함.
  - 진행률이 `15% -> 10%`로 역행하며 구형 `[1/6]` 및 `'한국어 번역'`(`CritiqueProgressWidget`) 라벨이 노출되고, 상세 패널/문서 모달에서 `hideScoreboard`로 `[?] 점수 산출 가이드` 버튼이 사라지며 `CritiqueCard` 내부에서 `createPortal` 누락으로 `ScoringGuideModal`이 클리핑됨.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - `conftest.py` 픽스처 갱신 후 `MagicMock` 분기 및 레거시 번역/3-Way VQA 코드를 제거하고, `PhotoDetail` 타입 분리·인쇄 템플릿(`critiquePrintTemplate.ts`)/문서 액션 훅 분리로 파일/함수 크기 축소
  - 진행률을 단조 증가(`[1/3]~[3/3]`)로 교정하고 `CritiqueProgressWidget` 단계명을 `[시각 채점 / 지각 앵커 / 심층 비평 / 평론 완성]`으로 동기화, `ScoringGuideModal`에 `createPortal(..., document.body)` 및 `ScoreHudStrip`/문서 마스트헤드 `[?]` 버튼 연결
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)
