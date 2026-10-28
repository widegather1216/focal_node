# 🧪 [03_ai_critique] Verification & Ticket Logs

- **검증 상태**: `🟢 Completed (Step 1~4 전 계층 구현 및 3단 검증 완료, 품질 감사 대기)`
- **인수 조건 통과율**: `4 / 4 (100%, AC 1~4 전 시나리오 및 UI/모달 검증 완료)`
- **미해결 티켓**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 3건`

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

---

## 🚨 3. 결함 리포트 (Defect Logs)

*(현재 등록된 OPEN 결함 없음)*

---

## 🧐 4. 코드 품질 감사 리포트 (Audit & Refactoring Logs)

### [REFACTOR-01] `CritiqueDocumentModal.tsx` 및 비평 UI 거대 컴포넌트 SRP 모듈 분할
- **심각도**: 🟡 Should Fix (권장)
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
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)

### [REFACTOR-02] 비평 추론 어댑터 내 Silent Fail(`except: pass`) 제거 및 장문 메서드 분리
- **심각도**: 🟡 Should Fix (권장)
- **위치**: `backend/app/services/chat_service.py#L80-L120`, `backend/app/services/mlx_adapters.py#L323-L640`, `backend/app/services/unipercept_adapter.py#L55-L498`
- **위반 규칙**: Rule 4.1 (함수 30줄 이내) & Rule 4.3 (예외 묵인 `except: pass` 금지)
- **발견된 문제**:
  - `chat_service.py`, `mlx_adapters.py`, `unipercept_adapter.py`의 모델 언로드 및 캐시 클리어 블록에 `except Exception: pass`가 다수 존재하며, `format_and_structure_critique`(87줄) 및 `generate_vqa_critiques_3way`(90줄)가 30줄 가이드를 초과함.
- **권장 개선안 (Suggested Diff)**:
  ```text
  - 프롬프트 생성 빌더 함수를 별도 헬퍼로 추출하여 추론 메서드 길이를 30줄 이내로 축소
  - 빈 except 블록에 명시적 경고 로그(print/logger) 추가
  ```
- **현재 상태**: 🟡 OPEN (`systematic-debugger` 위임 대기)

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
