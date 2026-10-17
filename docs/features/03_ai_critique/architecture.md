# [Architecture] 03. On-Demand AI Critique & Editorial Export

---

## 🏛️ 1. 2단계 온디맨드 AI 비평 및 에디토리얼 내보내기 흐름도

```mermaid
flowchart TD
    UI["PhotoCritiqueView / CritiqueView"] -->|POST /api/chat/critique| ChatRouter["backend/app/api/chat.py"]
    UI -.->|JSON Polling: GET /critique/status/{id}| ChatRouter
    UI -.->|취소: POST /critique/cancel/{id}| ChatRouter
    
    ChatRouter --> ChatSvc["ChatService & critique_status.py"]
    ChatSvc --> GPULock["GPU_LOCK (Metal 직렬화)"]
    
    GPULock -->|1단계: engine='unipercept'| UniPercept["UniPerceptAdapter (PyTorch MPS)\n3-Way VR 채점 + 3-Way VQA 영문 비평 후 즉시 언로드"]
    UniPercept -->|2단계: 번역 및 에디토리얼 구조화| Gemma4["GemmaAdapter (Gemma 4 12B-it MLX)\n2-Pass 한국어 직역/정제 & 60초 Keep-alive"]
    GPULock -->|단독: engine='gemma4'| Gemma4
    
    ChatSvc -->|영구 캐싱| PhotoRepo["PhotoRepository\n(SQLite ai_analysis 테이블)"]
    UI -->|모달/팝아웃 열람 및 MD/PDF 생성| DocModal["CritiqueDocumentModal.tsx\n(html2canvas + jsPDF + save_binary_file IPC)"]
```

---

## 🏗️ 2. 도메인 파일 트리 및 단일 책임 (SRP)

```text
backend/app/
├── api/chat.py                        # [기존] 비평 생성, 상태 Polling, 취소, 삭제, 전체 비평 목록, 종합 총평 라우터
├── services/
│   ├── chat_service.py                # [기존] UniPercept -> Gemma 4 순차 비평 파이프라인 오케스트레이션 및 DB 영구 저장
│   ├── critique_status.py             # [기존] 사진별 4단계 비평 진행률(step/progress), 취소 플래그 및 DB Self-Healing 조회
│   ├── mlx_adapters.py                # [기존] GemmaAdapter (MLX 60초 Keep-alive, 2-Pass 번역/구조화 및 종합 총평)
│   ├── unipercept_adapter.py          # [기존] UniPerceptAdapter (PyTorch MPS IAA/IQA/ISTA 채점/비평 및 즉시 언로드)
│   └── unipercept_utils.py            # [기존] InternVL 동적 패치 타일링 및 이미지 전처리 유틸리티

src/
├── types/critique.ts                  # [기존] CritiqueItem, CritiqueSummaryResponse, CritiqueStatus 타입 정의
├── hooks/
│   ├── usePhotoDetail.ts              # [기존] 상세 패널 상태, 비평 Polling/취소/삭제 및 재분석 제어 훅
│   └── usePhotoDetailQuery.ts         # [기존] 단일 사진 상세 정보 TanStack Query 훅
└── components/
    ├── CritiqueView.tsx               # [기존] 전체 비평 아카이브 대시보드 탭
    ├── detail/
    │   ├── PhotoCritiqueView.tsx      # [기존] 우측 패널 내 비평 요청/취소/점수 HUD 뷰
    │   └── PhotoAiAnalysisView.tsx    # [기존] AI 캡션 및 태그 수동 편집 폼
    └── critique/
        ├── CritiqueCard.tsx           # [기존] 개별 비평 요약 카드
        ├── CritiqueSummaryCard.tsx    # [기존] 다중 사진 포트폴리오 종합 비평 카드
        ├── CritiqueContentRenderer.tsx# [기존] 마크다운 비평 본문 및 IAA/IQA/ISTA 스코어보드 렌더러
        ├── CritiqueProgressWidget.tsx # [기존] 4단계 비평 생성 프로그레스 위젯
        ├── GlobalCritiqueToast.tsx    # [기존] 백그라운드 비평 진행 전역 플로팅 토스트
        └── CritiqueDocumentModal.tsx  # [기존/리팩토링대상] 매거진 뷰어(모달/독립 팝아웃 창) 및 MD/PDF 익스포터
```

---

## 🤝 3. 타 도메인 참조 및 경계 계약 (Cross-Domain Dependencies)

* **참조하는 외부 도메인 (Inbound/Read)**:
  - `00_core_foundation`: `GPU_LOCK`, `ai_factory.get_gemma_adapter()`, Tauri `save_binary_file` 및 `reveal_in_finder` IPC 참조.
  - `01_indexing_storage`: `PhotoRepository`(`get_photo_by_id`, `update_critique`, `delete_critique`, `get_all_critiqued_photos`)를 통해 `ai_analysis` 레코드 읽기/쓰기 수행.
* **외부 도메인에 노출하는 계약 (Outbound/Expose)**:
  - `04_studio_ui_analytics`: 우측 상세 패널(`DetailPanel.tsx`) 내 탭 뷰(`PhotoCritiqueView`, `PhotoAiAnalysisView`) 및 전역 플로팅 토스트(`GlobalCritiqueToast`)를 제공합니다.

---

## 🔒 4. 도메인 아키텍처 제약 규칙

1. **비평 엔진 상호 배타적 메모리 수명주기**:
   - `UniPercept 8B`는 3-Way VR 채점 및 VQA 영문 비평 직후 `finally` 블록에서 즉시 가중치를 언로드하고 `torch.mps.empty_cache()`를 실행한 뒤 `Gemma 4` 한국어 번역 단계로 진입해야 합니다.
   - `Gemma 4 (MLX)`는 연속 요청 최적화를 위해 60초 Keep-alive 후 언로드하며, 비평 도중 사용자 취소 또는 예외 발생 시에는 두 모델 모두 즉시 언로드(`_unload_critique_models`)합니다.
2. **거대 모달 컴포넌트 SRP 분할 지침**:
   - `CritiqueDocumentModal.tsx`는 단일 UI 300줄 가이드를 준수하도록 헤더/본문/PDF 익스포터 모듈로 단계적 분리를 지향합니다(`REFACTOR-01`).
