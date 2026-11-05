# 🧪 [03_ai_critique] Verification & Ticket Logs

- **검증 상태**: `🟢 Ready (하이브리드 파이프라인 Step 3 구현 및 TC-CRT-11~13 검증 완료, Step 4 UI 검증 대기)`
- **인수 조건 통과율**: `13 / 13 (100%)`
- **미해결 티켓**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 1건`

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
* **When:** `_calculate_overall_vr_score`가 호출되거나 프론트엔드에서 `[?] 점수 산출 가이드` 버튼이 클릭되면,
* **Then:**
  1. 사진의 EXIF(조리개 F값, ISO)에 따라 [인물/감성], [풍경/건축], [야경/스트리트], [표준] 4대 적응형 가중치가 적용되어야 한다.
  2. $\text{IAA} \ge 75$ 및 $\text{IAA} > \text{IQA}$ 조건에서 미학적 탁월성 보너스($\Delta_{\text{aesthetic}}$)가 정확히 산출 및 가산되어야 한다.
  3. 기존 DB 사진들의 `overall_score`가 `run_migrations()`에서 새 수식으로 일괄 자동 재계산(Backfill)되어야 한다.
  4. 프론트엔드 스코어보드 헤더의 `[?] 점수 산출 가이드` 클릭 시 `ScoringGuideModal`이 오픈되어 4대 가중치 표와 보너스 공식이 안내되어야 한다.

### AC 5. UniPercept 지각 앵커 + Gemma 4 직접 심층 비평 하이브리드 파이프라인 `[To-Be]`
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
| **Boundary**| `TC-CRT-10` | 비평 취소 시 VLM 즉시 강제 언로드 및 GPU 동기화 | 비평 추론 도중 `[취소]` 클릭 | Gemma/UniPercept 즉시 언로드 및 MPS 캐시 100% 반환 | `PASS (Fixed in DEFECT-01)` |
| **Happy** | `TC-CRT-11` | UniPercept 단일 패스 지각 앵커 추출 및 어휘 붕괴 방지 | 고해상도 테스트 사진 입력 | 150토큰 내외 지각 앵커 정상 영문 도출, 어휘 붕괴 0건 | `PASS` |
| **Happy** | `TC-CRT-12` | Gemma 4 지각 앵커 기반 직결 심층 비평 생성 | 지각 앵커 + VR 점수 + EXIF 주입 | 3대 표준 헤더 + 한 줄 총평 + 실전 조언 한국어 완성 | `PASS` |
| **Boundary**| `TC-CRT-13` | UniPercept VQA 오류 시 Gemma 4 자율 비평 폴백 | UniPercept VQA 예외 강제 발생 | Gemma 4 직접 심층 비평으로 정상 폴백 생성 완료 | `PASS` |

---

## 🚨 3. 결함 리포트 (Defect Logs)

### [DEFECT-01] 비평 취소(중지) 요청 시 VLM 모델 메모리 미해제 및 지연 잔류 결함
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🔴 Must Fix (메모리 누수 및 GPU 점유 잔류)
- **해결 내역**:
  - **수정 파일**: [`base_model.py`](../../../backend/app/services/base_model.py#L77-L93), [`chat_service.py`](../../../backend/app/services/chat_service.py#L107-L146), [`chat_service.py`](../../../backend/app/services/chat_service.py#L353-L415), [`test_critique_cancellation.py`](../../../backend/tests/test_critique_cancellation.py#L164-L248)
  - **원인 및 조치**:
    1. `_unload_critique_models(force=True)` 매개변수를 도입하여 비평 취소/예외 발생 시 Gemma의 `active_requests` 수치와 무관하게 즉시 강제 언로드 수행.
    2. `cancel_critique()`에서 `_critique_tasks`의 백그라운드 코루틴 `task.cancel()`을 호출하여 비동기 실행 루프에 즉각 취소 신호 전달.
    3. `base_model._unload_model_locked` 및 `chat_service._clear_device_caches`에 `torch.mps.synchronize()`를 적용하여 Metal 비동기 커맨드 버퍼 큐를 즉시 비우고 GPU 메모리를 OS로 100% 환원.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/test_critique_cancellation.py -v` (8 passed)
- **발견 일자**: 2026-11-03 (by `clean-code-auditor`)
- **위치**: 
  - `backend/app/services/chat_service.py#L122-L145` (`_unload_critique_models`)
  - `backend/app/services/chat_service.py#L397-L404` (`cancel_critique`)
  - `backend/app/services/base_model.py#L70-L93` (`_unload_model_locked`)
- **재현 조건 (Reproduction Steps)**:
  1. 갤러리에서 고해상도 사진 선택 후 `[AI 비평 생성]` 클릭.
  2. UniPercept 8B 또는 Gemma 4 12B-it VLM이 로드되어 추론(Pass 1 또는 VQA) 중인 상태에서 `[취소]` 버튼 클릭.
  3. 프론트엔드 UI에는 즉시 "비평 생성이 중단되었습니다"가 표시되나, macOS 활성 상태 보기(Activity Monitor)에서 Python 프로세스가 13~28GB의 RAM과 100% GPU를 30~60초간 지속 점유하거나 메모리가 완전히 반환되지 않음.
- **근본 원인 분석 (Root Causes)**:
  1. **`_unload_critique_models()`의 Gemma 언로드 조건 검사 오류 (`chat_service.py#L137-L140`)**:
     - 비평이 돌고 있을 때 Gemma의 `active_requests`는 `1`임.
     - `should_unload = active_reqs <= 0` 가드로 인해 취소 API 핸들러에서 Gemma 언로드가 아예 스킵(무시)됨.
  2. **`asyncio.Task`에 `task.cancel()` 미전달 (`chat_service.py#L397-L404`)**:
     - `cancel_critique()`가 상태 매니저 플래그만 세팅하고 백그라운드 코루틴 `_critique_tasks.get(photo_id)`에 취소 시그널(`task.cancel()`)을 전달하지 않음.
  3. **PyTorch MPS GPU 큐 동기화 누락 (`base_model.py#L79-L86`)**:
     - Apple Silicon Metal은 비동기 커맨드 버퍼로 동작함.
     - `torch.mps.synchronize()` 없이 `torch.mps.empty_cache()`만 부르면 GPU 큐에 남아있는 참조로 인해 메모리가 OS로 즉각 환원되지 않음.
- **수정 계획 (Suggested Fix)**:
  ```python
  # 1. chat_service.py: cancel_critique에서 force_unload=True 전달 및 task.cancel() 호출
  def _unload_critique_models(force: bool = False) -> None:
      ...
      should_unload = force or not isinstance(active_reqs, int) or active_reqs <= 0
      if should_unload and hasattr(gemma, "unload_model"):
          gemma.unload_model()

  # 2. base_model.py: torch.mps.synchronize() 추가 및 gc.collect() 2회 실행
  if hasattr(torch, "mps") and hasattr(torch.mps, "synchronize"):
      torch.mps.synchronize()
  gc.collect()
  if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
      torch.mps.empty_cache()
  ```

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `CritiqueDocumentModal.tsx` 및 비평 UI 거대 컴포넌트 SRP 모듈 분할
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🟡 Should Fix (권장)
- **해결 내역**:
  - **신설 및 분리 모듈**:
    - [`critiqueParser.tsx`](../../../src/utils/critiqueParser.tsx): 마크다운 AST 파서 & 6-Way 스코어보드 추출 유틸리티 (292줄)
    - [`critiqueExporter.ts`](../../../src/utils/critiqueExporter.ts): A4 인쇄 HTML 생성, 마크다운 직렬화 및 html2canvas/jsPDF 엔진 (650줄)
    - [`useModalZoomPan.ts`](../../../src/hooks/useModalZoomPan.ts): 모달 휠 줌 및 드래그 패닝 인터랙션 훅 (60줄)
    - [`CritiqueScoreboardCard.tsx`](../../../src/components/critique/CritiqueScoreboardCard.tsx): 6-Way 스코어보드 및 가이드 모달 연결 카드 (182줄)
    - [`ExecutiveSummaryCard.tsx`](../../../src/components/critique/ExecutiveSummaryCard.tsx): 통합 한 줄 총평 인용구 카드 (44줄)
    - [`OriginalEnglishCritiqueCard.tsx`](../../../src/components/critique/OriginalEnglishCritiqueCard.tsx): UniPercept 8B VQA 영문 원문 토글 카드 (93줄)
    - [`CritiqueBlockItem.tsx`](../../../src/components/critique/CritiqueBlockItem.tsx): 개별 마크다운 AST 블록 렌더러 (207줄)
    - [`ScoreHudStrip.tsx`](../../../src/components/critique/ScoreHudStrip.tsx): 카메라 LCD HUD 스타일 컴팩트 점수 스트립 (77줄)
    - [`CritiqueHeader.tsx`](../../../src/components/critique/CritiqueHeader.tsx): 비평 대시보드 타이틀, 통계 뱃지, 정렬 탭, 검색바 및 요약 생성 헤더 (188줄)
    - [`CritiqueDocumentToolbar.tsx`](../../../src/components/critique/CritiqueDocumentToolbar.tsx): 매거진 뷰어 상단 헤더 툴바 (319줄)
    - [`CritiqueDocumentPhotoViewer.tsx`](../../../src/components/critique/CritiqueDocumentPhotoViewer.tsx): 매거진 뷰어 좌측 사진 캔버스 및 EXIF HUD (187줄)
    - [`CritiqueDocumentArticle.tsx`](../../../src/components/critique/CritiqueDocumentArticle.tsx): 매거진 뷰어 우측 페이퍼 문서 아티클 (175줄)
    - [`CritiqueExportProgressOverlay.tsx`](../../../src/components/critique/CritiqueExportProgressOverlay.tsx): 내보내기 진행률 피드백 모달 오버레이 (197줄)
  - **리팩토링 파일**:
    - [`CritiqueDocumentModal.tsx`](../../../src/components/critique/CritiqueDocumentModal.tsx): 1,766줄 ➔ 449줄로 약 75% 경량화 및 최상위 컨테이너 레이아웃 단일 책임 정돈
    - [`CritiqueContentRenderer.tsx`](../../../src/components/critique/CritiqueContentRenderer.tsx): 856줄 ➔ 109줄로 축소 및 하위 호환 re-export 제공
    - [`PhotoCritiqueView.tsx`](../../../src/components/detail/PhotoCritiqueView.tsx): 478줄 ➔ 408줄로 축소 (인라인 `ScoreHudStrip` 분리)
    - [`CritiqueView.tsx`](../../../src/components/CritiqueView.tsx): 375줄 ➔ 223줄로 축소 (헤더 컨트롤 분리)
  - **회귀 검증 결과**: `npm run build` (tsc & vite build `PASS`), pytest 43건 전체 통과 (`PASS`)
- **위치**: `src/components/critique/CritiqueDocumentModal.tsx#L1-L1766`, `src/components/critique/CritiqueContentRenderer.tsx#L1-L813`, `src/components/detail/PhotoCritiqueView.tsx#L1-L478`, `src/components/CritiqueView.tsx#L1-L375`
- **위반 규칙**: Single Responsibility Principle (단일 UI 파일 300줄 가이드 초과)
- **발견된 문제**:
  - `CritiqueDocumentModal.tsx`(1,766줄) 내부에 매거진 뷰어 UI, A4 프린트 HTML 템플릿 생성(`generatePrintHtml`), Markdown 직렬화 로직, `html2canvas`/`jsPDF` 렌더링 엔진이 모두 결합되어 유지보수 복잡도가 높음.
  - `CritiqueContentRenderer.tsx`(813줄) 및 `PhotoCritiqueView.tsx`(478줄)에 AST 파서, 스코어보드/영문원문 카드, LCD HUD 등이 결합되어 컴포넌트 분할이 필요함.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - PDF/Markdown 내보내기 순수 유틸리티 및 프린트 HTML 템플릿을 src/utils/critiqueExporter.ts로 분리
  - 스코어보드 파서/서브 섹션(ScoreHudStrip, OriginalEnglishCritiqueCard)을 분리하여 모달/컴포넌트 본체를 300줄 이내로 축소
  ```

### [REFACTOR-02] 비평 추론 어댑터 내 Silent Fail(`except: pass`) 제거 및 장문 메서드 분리
- **현재 상태**: 🟢 RESOLVED (수정 및 회귀 검증 완료)
- **심각도**: 🟡 Should Fix (권장)
- **해결 내역**:
  - **수정 파일**: [`chat_service.py`](../../../backend/app/services/chat_service.py#L75-L125), [`mlx_adapters.py`](../../../backend/app/services/mlx_adapters.py#L42-L635), [`unipercept_adapter.py`](../../../backend/app/services/unipercept_adapter.py#L60-L585)
  - **원인 및 조치**:
    1. `chat_service.py`(`_clear_device_caches`, `updated_at` 파싱), `mlx_adapters.py`(모델 로드, safetensors 링크, OOM 복구, 언로드 캐시 정리), `unipercept_adapter.py`(MPS 프리클리어, 토크나이저/프로세서 로드, 템플릿 로드, VR/VQA 텐서 캐시 클리어)의 모든 빈 `except: pass` 블록에 명시적 디버그/경고 로깅을 추가하여 Silent Fail 완전 제거.
    2. `mlx_adapters.py`의 `format_and_structure_critique`(88줄)에서 프롬프트 빌더(`_build_document_structuring_messages`), 스코어보드 보존(`_preserve_scoreboard_header`), 추론 실행기(`_execute_document_structuring_generation`)를 분리하여 단일 함수 30줄 가이드 충족.
    3. `unipercept_adapter.py`의 `generate_vqa_critiques_3way`(90줄)에서 단계 정의(`_get_vqa_step_definitions`), 단일 단계 실행(`_execute_single_vqa_step`), 전 단계 오케스트레이션(`_execute_all_vqa_steps`)을 추출하여 책임 분리 및 가독성 확보.
  - **회귀 테스트 결과**: `./venv/bin/pytest backend/tests/ -v` (103 passed), `npm run build` (`PASS`)
- **위치**: `backend/app/services/chat_service.py#L80-L120`, `backend/app/services/mlx_adapters.py#L323-L640`, `backend/app/services/unipercept_adapter.py#L55-L498`
- **위반 규칙**: Rule 4.1 (함수 30줄 이내) & Rule 4.3 (예외 묵인 `except: pass` 금지)
- **발견된 문제**:
  - `chat_service.py`, `mlx_adapters.py`, `unipercept_adapter.py`의 모델 언로드 및 캐시 클리어 블록에 `except Exception: pass`가 다수 존재하며, `format_and_structure_critique`(87줄) 및 `generate_vqa_critiques_3way`(90줄)가 30줄 가이드를 초과함.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - 프롬프트 생성 빌더 함수를 별도 헬퍼로 추출하여 추론 메서드 길이를 30줄 이내로 축소
  - 빈 except 블록에 명시적 경고 로그(print/logger) 추가
  ```

### [REFACTOR-03] 비평 Polling 빈 catch 블록 예외 묵인(Rule 4.3) 교정 및 ApiClient 반환 타입 강화
- **심각도**: 🟡 Should Fix (권장)
- **위치**: `src/components/detail/PhotoCritiqueView.tsx#L146-L148`, `src/components/critique/GlobalCritiqueToast.tsx#L53-L55`, `src/hooks/usePhotoDetail.ts#L207-L209`, `src/services/api.ts#L233-L277`, `src/components/CritiqueView.tsx#L56`
- **위반 규칙**: Rule 4.3 (예외 묵인 빈 catch 금지) & Rule 4.2 / 타입 안전성 (`Promise<any>` 지양)
- **발견된 문제**:
  - 백그라운드 비평 Polling 및 sleep/resume 복구 핸들러(`PhotoCritiqueView`, `GlobalCritiqueToast`, `usePhotoDetail`)에서 네트워크/서버 오류 발생 시 빈 `catch {}` 블록으로 예외를 묵인(Silent Fail)하여 백엔드 에러 원인 추적이 차단됨.
  - `src/services/api.ts`의 `getPhotoCritique`, `cancelCritique`, `deleteCritique` 반환 타입이 `Promise<any>`로 느슨하게 정의되어 있으며, `CritiqueView.tsx#L56`에 `catch (err: any)`가 잔재함.
- **권장 개선안 (Suggested Diff)**:
  ```text
  // 빈 catch 블록에 디버그/경고 로깅 추가
  } catch (pollErr) {
    console.debug('[CritiquePolling] Transient status polling notice:', pollErr);
  }
  // api.ts: Promise<any> -> Promise<CritiqueResponse>, Promise<CritiqueCancelResponse>, Promise<{ status: string; photo_id: string }>
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)
