# [Spec & Contracts] 03. On-Demand AI Critique & Editorial Export

---

## 💾 1. 데이터베이스 스키마 명세 (`backend/app/models.py`)

### 1.1. `[As-Is 기구현]` `ai_analysis` 테이블
```sql
CREATE TABLE ai_analysis (
    image_id VARCHAR(64) PRIMARY KEY REFERENCES images(id) ON DELETE CASCADE,
    caption VARCHAR,                         -- Gemma 4 생성 상세 설명
    tags VARCHAR,                            -- JSON 문자열 배열 ('["street", "night"]')
    aesthetic_tags VARCHAR,                  -- 전문 미적/스타일 태그 JSON 배열
    is_user_edited BOOLEAN DEFAULT 0 NOT NULL, -- 사용자의 캡션/태그 수동 편집 여부
    critique VARCHAR,                        -- UniPercept 8B / Gemma 4 심층 에디토리얼 비평 전문
    critique_updated_at DATETIME             -- 비평 최종 생성/갱신 일시 (UTC)
);
```

---

## 🌐 2. 백엔드 REST API 계약 (`/api/chat`, `/api/photos`) `[As-Is 기구현]`

* `POST /api/chat/critique`
  - **Request:** `{ "photo_id": "sha256...", "engine"?: "unipercept" | "gemma4" }` (기본값 `"unipercept"`)
  - **Response 200:** `{ "critique": "...", "critique_updated_at": "...", "engine_used": "unipercept", "status": "completed" }`
* `GET /api/chat/critique/status/{photo_id}` *(비동기 4단계 상태 JSON Polling)*
  - **Response 200:** `{ "photo_id": "...", "step": 2, "total_steps": 4, "message": "심층 비평 추론 중...", "progress": 45, "status": "idle" | "processing" | "completed" | "cancelled" | "error", "critique": null, "critique_updated_at": null }`
* `POST /api/chat/critique/cancel/{photo_id}` *(별칭: `POST /api/chat/critique/{photo_id}/cancel`)*
  - **Response 200:** `{ "status": "cancelled", "photo_id": "...", "message": "비평 생성이 사용자에 의해 중단되었습니다." }`
* `DELETE /api/chat/critique/{photo_id}`
  - **Response 200:** `{ "status": "deleted", "photo_id": "..." }` (`ai_analysis.critique` 및 `critique_updated_at` 초기화)
* `GET /api/chat/critiques`
  - **Response 200:** `CritiqueItemResponse[]` (비평이 존재하는 모든 사진 및 비평 전문 목록)
* `POST /api/chat/critique-summary`
  - **Request:** `{ "photo_ids": ["sha256...", ...] }`
  - **Response 200:** `{ "summary": "포트폴리오 종합 총평...", "total_critiques_analyzed": 5, "created_at": "..." }`
* `PATCH /api/photos/{id}/metadata`
  - **Request:** `{ "caption": "수정된 설명", "tags": ["portrait", "85mm"] }`
  - **Response 200:** `{ "status": "success", "id": "...", "ai_analysis": AIAnalysisSchema }` (`is_user_edited = true` 자동 설정)

---

## 💻 3. 프론트엔드 타입 및 에디토리얼 내보내기 계약 (`src/types/critique.ts`)

```typescript
export interface CritiqueStatus {
  photo_id: string;
  step: number;
  total_steps: number;
  message: string;
  progress: number;
  status: 'idle' | 'processing' | 'completed' | 'cancelled' | 'error';
  critique?: string | null;
  critique_updated_at?: string | null;
}
```
* **클라이언트 사이드 문서 생성 및 멀티윈도우 (`CritiqueDocumentModal.tsx`)**:
  - **독립 팝아웃 윈도우**: Tauri `WebviewWindow` (`/?popout=critique&photoId=...`)를 통해 별도 OS 창으로 에디토리얼 리포트를 분리 열람 가능.
  - **Markdown (`.md`)**: 사진 파일명, 촬영 EXIF 테이블, AI 비평 전문을 정형화된 Markdown으로 직렬화하여 Tauri `save_binary_file` IPC로 저장.
  - **PDF (`.pdf`)**: 오프스크린 A4 템플릿(`generatePrintHtml`)을 `html2canvas`로 2x Retina 캡처한 뒤 `jsPDF` 다중 페이지로 분할하여 `save_binary_file` IPC로 저장.
