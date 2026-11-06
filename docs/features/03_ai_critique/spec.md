# [Spec & Contracts] 03. On-Demand AI Critique & Editorial Export

---

## 💾 1. 데이터베이스 스키마 및 적응형 평점 명세 (`backend/app/models.py`, `services/scoring.py`)

### 1.1. `[As-Is 기구현]` `ai_analysis` 테이블
```sql
CREATE TABLE ai_analysis (
    image_id VARCHAR(64) PRIMARY KEY REFERENCES images(id) ON DELETE CASCADE,
    caption VARCHAR,                         -- Gemma 4 생성 상세 설명
    tags VARCHAR,                            -- JSON 문자열 배열 ('["street", "night"]')
    aesthetic_tags VARCHAR,                  -- 전문 미적/스타일 태그 JSON 배열
    is_user_edited BOOLEAN DEFAULT 0 NOT NULL, -- 사용자의 캡션/태그 수동 편집 여부
    critique VARCHAR,                        -- UniPercept 8B / Gemma 4 한국어 심층 비평 전문
    critique_updated_at DATETIME,            -- 비평 최종 생성/갱신 일시 (UTC)
    overall_score FLOAT,                     -- 6-Way 지각 앙상블 종합 평점 (0.0 ~ 100.0, idx_ai_analysis_overall_score 인덱스)
    iaa_score FLOAT,                         -- 미학 및 구도 평점 (idx_ai_analysis_iaa_score 인덱스)
    iqa_score FLOAT,                         -- 화질 및 선명도 평점
    ista_score FLOAT,                        -- 구조 및 질감 평점
    critique_en TEXT                         -- UniPercept 8B VQA 영문 비평 앵커 원문
);
```

### 1.2. `[As-Is 기구현]` 미학 주도형 EXIF 적응적 종합 평점 모델 수식
* **EXIF 기반 4대 모드 동적 가중치 분배 (`resolve_perceptual_weights`)**:
  - [모드 A] 浅심도 인물/감성 ($F \le 2.8$): $w_{\text{iaa}} = 0.65, \; w_{\text{iqa}} = 0.25, \; w_{\text{ista}} = 0.10$
  - [모드 B] 팬포커스 풍경/건축 ($F \ge 5.6$): $w_{\text{iaa}} = 0.45, \; w_{\text{iqa}} = 0.30, \; w_{\text{ista}} = 0.25$
  - [모드 C] 야경/스트리트 스냅 ($\text{ISO} \ge 1600$): $w_{\text{iaa}} = 0.70, \; w_{\text{iqa}} = 0.20, \; w_{\text{ista}} = 0.10$
  - [모드 D] 일반 스냅 (표준 모드) (그 외 및 EXIF 누락): $w_{\text{iaa}} = 0.55, \; w_{\text{iqa}} = 0.30, \; w_{\text{ista}} = 0.15$
* **기저 점수**: $S_{\text{base}} = (w_{\text{iaa}} \cdot \text{IAA}) + (w_{\text{iqa}} \cdot \text{IQA}) + (w_{\text{ista}} \cdot \text{ISTA})$
* **미학적 탁월성 보너스 (`calculate_aesthetic_bonus`)**:
  $$\Delta_{\text{aesthetic}} = (\text{IAA} - \text{IQA}) \times 0.25 \times (\text{IAA} / 100) \quad (\text{단, } \text{IAA} > \text{IQA} \text{ and } \text{IAA} \ge 75)$$
* **최종 클램핑**: $\text{overall\_score} = \min(100, \; \max(0, \; \text{round}(S_{\text{base}} + \Delta_{\text{aesthetic}})))$
* **자동 백필 정책**: `run_migrations()`에서 `iaa_score IS NOT NULL`인 기존 레코드를 EXIF 메타데이터와 조인하여 새 수식으로 자동 재계산 완료.

---

## 🤖 2. 온디맨드 2단계 하이브리드 비평 파이프라인 명세 `[As-Is 기구현]`

### 2.1. Stage 1: UniPercept 8B (초고속 정량 채점 & 지각 앵커 추출, ~10초)
1. **VR 3-Way 채점**: IAA, IQA, ISTA 각 0~100점 Logit 기대값 산출 및 EXIF 적응형 종합 점수 계산.
2. **단일 패스 통합 지각 VQA (`UNIPERCEPT_VQA_SINGLE_PASS_PROMPT`)**: 미학적 강점/구도 결함, 광학 화질 저하, 표면 질감을 유기적으로 연결한 3~4문장(약 150~200토큰)의 영문 핵심 지각 앵커(`critique_en`) 추출.
3. **디코딩 파라미터 안정화**: `repetition_penalty=1.0`, `do_sample=True`, `temperature=0.7`, `top_p=0.9`로 어휘 붕괴(Word Salad, 문법 왜곡, 특수문자 깨짐) 원천 차단.
4. **즉시 언로드**: 추론 완료 직후 `finally` 블록에서 UniPercept 모델 언로드, `torch.mps.synchronize()` 및 MPS 캐시 100% 즉시 반환.

### 2.2. Stage 2: Gemma 4 12B (지각 앵커 기반 한국어 심층 비평 직접 직결, ~15초)
1. **직접 생성 및 살 덧붙이기 (Enrichment)**: 사진 픽셀 + EXIF + UniPercept VR 점수 + 영문 지각 앵커를 종합하여 셔터/조리개/초점거리 조작, 조명 각도, 라이트룸 보정 커브/HSL 조정 등 실전 조언을 풍부하게 확장.
2. **3단계 표준 리포트 양식 엄수**:
   - 최상단 `[6-Way 앙상블 비평 스코어보드]`
   - 스코어보드 직후 `> **한 줄 총평**: ...`
   - `## 1. [시각적 미학 및 EXIF 광학 진단]`
   - `## 2. [구도 및 화질 결함과 왜곡 위치 지적]`
   - `## 3. [현장 재촬영 및 보정 실전 기술 조언]`
3. **자율 폴백 (Safety Net)**: UniPercept VQA 실패 시 Gemma 4 자율 비평 파이프라인으로 무중단 자동 전환.

---

## 🌐 3. 백엔드 REST API 계약 (`/api/chat`, `/api/photos`) `[As-Is 기구현]`

* `POST /api/chat/critique`: `{ "photo_id": "sha256...", "engine"?: "unipercept" | "gemma4" }` ➔ `CritiqueResponse` (4종 점수, 심층비평문, 영문앵커 반환)
* `GET /api/chat/critique/status/{photo_id}`: 비동기 4단계 진행률(`step`, `progress`, `status`) Polling
* `POST /api/chat/critique/cancel/{photo_id}`: 진행 중인 비평 생성 즉시 중단 및 모델 강제 언로드 (`force=True`)
* `DELETE /api/chat/critique/{photo_id}`: 비평 텍스트 및 4종 평점 `NULL` 초기화
* `GET /api/chat/critiques?sort_by=recent|overall_score|iaa_score`: 평점순 정렬 지원 비평 목록 반환
* `POST /api/chat/critique-summary`: 다중 사진 포트폴리오 에디토리얼 종합 총평 생성

---

## 💻 4. 프론트엔드 타입 및 UI 계약 (`src/types/critique.ts`) `[As-Is 기구현]`

```typescript
export interface CritiqueItem {
  photo_id: string;
  file_name: string;
  file_path: string;
  capture_date?: string | null;
  camera_model?: string | null;
  lens_model?: string | null;
  f_number?: number | null;
  shutter_speed?: string | null;
  iso?: number | null;
  critique: string;
  critique_en?: string | null;    // UniPercept 영문 원문 지각 앵커
  overall_score?: number | null;  // 종합 평점 (0~100)
  iaa_score?: number | null;      // 미학 평점 (0~100)
  iqa_score?: number | null;      // 화질 평점 (0~100)
  ista_score?: number | null;     // 구조/질감 평점 (0~100)
  critique_updated_at?: string | null;
}
```

### 4.1. 한/영 원문 토글 및 마크다운 AST 렌더러 (`CritiqueContentRenderer.tsx`)
* `OriginalEnglishCritiqueCard.tsx`: UniPercept 8B VQA 영문 앵커 토글 렌더러 (`RAW EN` 배지).
* `critiqueParser.tsx`: 6-Way 스코어보드 추출, `determineThemeType` 테마 분류(`aesthetic`/`defect`/`advice`/`camera`/`structure`), 인라인 볼드/코드 렌더링.

### 4.2. 에디토리얼 내보내기 & 팝아웃 (`CritiqueDocumentModal.tsx`)
* Tauri 멀티윈도우 팝아웃(`/?popout=critique&photoId=...`) 및 Markdown/PDF 내보내기 지원.
* 마크다운 내보내기(`exportCritiqueToMarkdown`) 시 영문 원문(`critique_en`) 부록 자동 첨부.

### 4.3. 점수 산출 기준 안내 모달 (`ScoringGuideModal.tsx`)
* `CritiqueContentRenderer.tsx` 스코어보드 헤더 우측의 `[?] 점수 산출 가이드` 버튼 클릭 시 오픈.

---

## 🔮 5. [To-Be] 신규 개발 예정 명세

(현재 예정된 추가 변경사항 없음 — 전 계층 Step 1~4 구현 완료)
