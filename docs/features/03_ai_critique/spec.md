# [Spec & Contracts] 03. On-Demand AI Critique & Editorial Export

---

## 💾 1. 데이터베이스 스키마 명세 (`backend/app/models.py`)

### 1.1. `[As-Is 기구현]` `ai_analysis` 기본 테이블
```sql
CREATE TABLE ai_analysis (
    image_id VARCHAR(64) PRIMARY KEY REFERENCES images(id) ON DELETE CASCADE,
    caption VARCHAR,                         -- Gemma 4 생성 상세 설명
    tags VARCHAR,                            -- JSON 문자열 배열 ('["street", "night"]')
    aesthetic_tags VARCHAR,                  -- 전문 미적/스타일 태그 JSON 배열
    is_user_edited BOOLEAN DEFAULT 0 NOT NULL, -- 사용자의 캡션/태그 수동 편집 여부
    critique VARCHAR,                        -- UniPercept 8B / Gemma 4 한국어 심층 비평 전문
    critique_updated_at DATETIME             -- 비평 최종 생성/갱신 일시 (UTC)
);
```

### 1.2. `[To-Be / Migration Required]` 정량 평점 및 영문 원문 정규화 컬럼 추가
* **대상 테이블**: `ai_analysis`
* **추가 컬럼**:
  - `overall_score FLOAT` (`idx_ai_analysis_overall_score` 인덱스 포함, 0.0 ~ 100.0)
  - `iaa_score FLOAT` (`idx_ai_analysis_iaa_score` 인덱스 포함, 미학 및 구도 평점)
  - `iqa_score FLOAT` (화질 및 선명도 평점)
  - `ista_score FLOAT` (구조 및 질감 평점)
  - `critique_en TEXT` (UniPercept 8B가 생성한 VQA 영문 비평 원문)
* **자동 백필(Backfill) 마이그레이션 규칙**: 앱 기동 시 `run_migrations()`에서 컬럼 추가 후 `critique IS NOT NULL AND overall_score IS NULL`인 기존 레코드를 조회하여 `[6-Way 앙상블 비평 스코어보드]` 헤더의 점수를 정규식으로 파싱해 4개 점수 컬럼에 비파괴적으로 백필합니다.

---

## 🌐 2. 백엔드 REST API 계약 (`/api/chat`, `/api/photos`)

* `POST /api/chat/critique` `[As-Is / To-Be 응답 확장]`
  - **Request:** `{ "photo_id": "sha256...", "engine"?: "unipercept" | "gemma4" }` (기본값 `"unipercept"`)
  - **Response 200:**
    ```json
    {
      "critique": "...",
      "critique_en": "...",
      "overall_score": 84.5,
      "iaa_score": 88.0,
      "iqa_score": 81.2,
      "ista_score": 84.3,
      "critique_updated_at": "2026-10-17T12:00:00Z",
      "engine_used": "unipercept",
      "status": "completed"
    }
    ```
* `GET /api/chat/critique/status/{photo_id}` `[As-Is]` *(비동기 4단계 상태 JSON Polling)*
  - **Response 200:** `{ "photo_id": "...", "step": 2, "total_steps": 4, "message": "심층 비평 추론 중...", "progress": 45, "status": "idle" | "processing" | "completed" | "cancelled" | "error", "critique": null, "critique_updated_at": null }`
* `POST /api/chat/critique/cancel/{photo_id}` *(별칭: `POST /api/chat/critique/{photo_id}/cancel`)* `[As-Is]`
  - **Response 200:** `{ "status": "cancelled", "photo_id": "...", "message": "비평 생성이 사용자에 의해 중단되었습니다." }`
* `DELETE /api/chat/critique/{photo_id}` `[As-Is / To-Be 정규화 컬럼 동시 초기화]`
  - **Response 200:** `{ "status": "ok", "photo_id": "..." }` (`critique`, `critique_en`, 4종 평점 및 `critique_updated_at`을 모두 `NULL`로 초기화)
* `GET /api/chat/critiques?sort_by=recent|overall_score|iaa_score` `[To-Be 정렬 파라미터 추가]`
  - **Response 200:** `CritiqueItemResponse[]` (비평이 존재하는 모든 사진 목록, 정규화 4종 평점 및 `critique_en` 포함)
* `POST /api/chat/critique-summary` `[As-Is]`
  - **Request:** `{ "photo_ids": ["sha256...", ...] }`
  - **Response 200:** `{ "summary": "포트폴리오 종합 총평...", "total_critiques_analyzed": 5, "created_at": "..." }`

---

## 💻 3. 프론트엔드 타입 및 에디토리얼 내보내기 계약 (`src/types/critique.ts`)

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
  critique_en?: string | null;    // [To-Be] UniPercept 영문 원문
  overall_score?: number | null;  // [To-Be] 종합 평점 (0~100)
  iaa_score?: number | null;      // [To-Be] 미학 평점 (0~100)
  iqa_score?: number | null;      // [To-Be] 화질 평점 (0~100)
  ista_score?: number | null;     // [To-Be] 구조/질감 평점 (0~100)
  critique_updated_at?: string | null;
}
```
* **클라이언트 사이드 문서 생성 및 멀티윈도우 (`CritiqueDocumentModal.tsx`)**:
  - **독립 팝아웃 윈도우**: Tauri `WebviewWindow` (`/?popout=critique&photoId=...`)를 통해 별도 OS 창으로 에디토리얼 리포트를 분리 열람 가능.
  - **Markdown (`.md`) & PDF (`.pdf`)**: EXIF 메타데이터, 정규화 4종 평점 스코어보드, AI 비평 전문을 결합하여 Tauri `save_binary_file` IPC로 저장.
