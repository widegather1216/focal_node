# [Architecture] 03. On-Demand AI Critique & Editorial Export

---

## 🏛️ 1. 2단계 온디맨드 AI 비평, 정규화 저장 및 에디토리얼 내보내기 흐름도

```mermaid
flowchart TD
    UI["PhotoCritiqueView / CritiqueView"] -->|POST /api/chat/critique| ChatRouter["backend/app/api/chat.py"]
    UI -.->|JSON Polling: GET /critique/status/{id}| ChatRouter
    UI -.->|취소: POST /critique/cancel/{id}| ChatRouter
    
    ChatRouter --> ChatSvc["ChatService & critique_status.py"]
    ChatSvc --> GPULock["GPU_LOCK (Metal 직렬화)"]
    
    GPULock -->|1단계: engine='unipercept'| UniPercept["UniPerceptAdapter (PyTorch MPS)\n3-Way VR 채점 + 단일 패스 통합 지각 VQA(3~4문장 앵커)\n추론 완료 즉시 100% 언로드 (~10초)"]
    UniPercept -->|2단계: 지각 앵커 기반 직접 심층 비평| Gemma4["GemmaAdapter (Gemma 4 12B-it MLX)\n[VR점수 + 지각앵커 + EXIF + 사진] 직결 생성\n한국어 마크다운 리포트 완성 & 60초 Keep-alive (~15초)"]
    GPULock -->|단독: engine='gemma4'| Gemma4
    
    ChatSvc -->|정규화 저장: critique + critique_en + 4종 평점| PhotoRepo["PhotoRepository\n(SQLite ai_analysis 테이블)"]
    UI -->|모달/팝아웃 열람 및 MD/PDF 생성| DocModal["CritiqueDocumentModal.tsx\n(html2canvas + jsPDF + save_binary_file IPC)"]
```

---

## 🏗️ 2. 도메인 파일 트리 및 단일 책임 (SRP)

```text
backend/app/
├── models.py                          # [기존] AIAnalysis에 overall_score, iaa_score, iqa_score, ista_score, critique_en 컬럼
├── database.py                        # [기존] run_migrations()에 EXIF 조인 기반 overall_score 적응형 일괄 재계산 백필 로직
├── api/chat.py                        # [기존] 비평 생성/Polling/취소/삭제/총평 및 평점 정렬 지원 전체 비평 목록 라우터
├── services/
│   ├── base_model.py                  # [기존] GPU_LOCK 기반 어댑터 베이스 및 비-MPS 안전 캐시 가드(clear_mps_cache/clear_mlx_cache)
│   ├── scoring.py                     # [기존] EXIF 적응형 4대 가중치, 미학적 탁월성 보너스 및 종합 평점 산출 순수 연산 모듈
│   ├── critique_prompts.py            # [신규] ADR-05 Gemma 4/UniPercept 프롬프트 상수 및 EXIF 컨텍스트 포매터
│   ├── critique_db_helpers.py         # [신규] 비평 DB 저장·메타데이터 조회·스코어보드 헤더 빌드 헬퍼
│   ├── chat_service.py                # [기존] 하이브리드 비평 파이프라인 오케스트레이터 (364줄 경량화)
│   ├── critique_status.py             # [기존] 사진별 4단계 비평 진행률(step/progress), 취소 플래그 및 DB Self-Healing 조회 (142줄)
│   ├── ai_parser.py                   # [기존] Gemma JSON 출력 파서 및 활성 프롬프트 재노출 모듈 (137줄 경량화)
│   ├── siglip_adapter.py              # [신규] SigLIP 2 임베딩/제로샷 태깅 전담 어댑터 (124줄)
│   ├── mlx_adapters.py                # [기존] GemmaAdapter 직접 심층 비평/캡션/요약 어댑터 (377줄 경량화)
│   ├── unipercept_runtime.py          # [신규] UniPercept 체크포인트 탐색, VQA 쿼리/응답 정제 및 텐서 추출 헬퍼 (226줄)
│   ├── unipercept_adapter.py          # [기존] 3-Way VR 채점 및 단일 패스 통합 지각 VQA 어댑터 (516줄 경량화)
│   └── unipercept_utils.py            # [기존] UniPercept 단일 패치(448x448) 이미지 전처리 및 점수 토큰 매핑 유틸리티

src/
├── types/critique.ts                  # [기존] CritiqueItem(4종 점수, critique_en), CritiqueResponse/Cancel/Delete 응답 타입
├── utils/
│   ├── activePhotoList.ts             # [신규] 활성 탭(비평 ['critiques'] prefix / 갤러리) 기반 사진 목록 캐시 추출 유틸
│   ├── critiqueMarkdownParser.ts      # [신규] 마크다운 AST 블록 파서, 6-Way 스코어보드 추출 및 텍스트 정제 유틸 (214줄)
│   ├── critiqueParser.tsx             # [기존] 인라인 마크다운 강조 렌더러 및 AST 파서 재노출 모듈 (65줄 경량화)
│   ├── critiquePrintTemplate.ts       # [신규] XSS 이스케이프 HTML 인쇄 템플릿 및 Markdown 내보내기 직렬화 (296줄)
│   ├── critiqueExportHelpers.ts       # [신규] Tauri 저장 다이얼로그/IPC, 이미지 디코딩 대기 및 A4 캔버스 PDF 슬라이싱 (162줄)
│   └── critiqueExporter.ts            # [기존] Markdown/PDF 내보내기 진입점 및 진행 상태 오케스트레이션 (222줄 경량화)
├── hooks/
│   ├── useCritiqueStatusPolling.ts    # [신규] 단일 타이머 체인·inFlight/visibility 가드 통합 비평 상태 Polling & 복구 훅
│   ├── useCritiqueDocumentModal.ts    # [신규] 문서 뷰어 모달 상태·단축키·내보내기/팝아웃 오케스트레이션 훅 (298줄)
│   ├── usePhotoDetail.ts              # [기존] 상세 패널 상태, 비평 요청/취소/삭제 및 재분석 제어 훅 (285줄 경량화)
│   ├── usePhotoDetailQuery.ts         # [기존] 단일 사진 상세 정보 TanStack Query 훅 (순환 참조 해소)
│   └── useModalZoomPan.ts             # [기존] 모달 캔버스 휠 확대/축소 및 드래그 패닝 제어 훅
└── components/
    ├── CritiqueView.tsx               # [기존] 전체 비평 아카이브 대시보드 탭 (헤더 분리 후 223줄 경량화)
    ├── detail/
    │   ├── PhotoCritiqueView.tsx      # [기존] 우측 패널 내 비평 요청/취소 뷰 (ScoreHudStrip 분리, 288줄)
    │   └── PhotoAiAnalysisView.tsx    # [기존] AI 캡션 및 태그 수동 편집 폼
    └── critique/
        ├── CritiqueCardHeader.tsx     # [신규] 비평 카드 상단 썸네일, 평점 배지 및 EXIF 메타데이터 헤더 (150줄)
        ├── CritiqueCard.tsx           # [기존] 개별 비평 요약 카드 본문 및 액션 푸터 (188줄 경량화)
        ├── CritiqueSummaryCard.tsx    # [기존] 다중 사진 포트폴리오 종합 비평 카드
        ├── CritiqueHeader.tsx         # [기존] 비평 보관함 상단 타이틀, 통계 뱃지, 정렬 토글 및 요약 생성 헤더
        ├── CritiqueContentRenderer.tsx# [기존] 마크다운 본문 렌더러 (서브 컴포넌트 분할 후 109줄 경량화)
        ├── CritiqueScoreboardCard.tsx # [기존] 6-Way 지각 앙상블 평점 카드 및 점수 가이드 모달 연결
        ├── ExecutiveSummaryCard.tsx   # [기존] 통합 한 줄 총평 인용구 카드
        ├── OriginalEnglishCritiqueCard.tsx # [기존] UniPercept 8B VQA 영문 원문 토글 카드
        ├── CritiqueBlockItem.tsx      # [기존] 단일 마크다운 AST 블록 렌더러
        ├── ScoreHudStrip.tsx          # [기존] 카메라 LCD HUD 스타일 컴팩트 점수 스트립 & [?] 가이드 연결 (113줄)
        ├── ScoringGuideContent.tsx    # [신규] 3대 지각 지표, 4대 적응형 가중치 및 미학 보너스 본문 뷰 (231줄)
        ├── ScoringGuideModal.tsx      # [기존] createPortal·캡처 단계 Escape 격리 점수 가이드 모달 쉘 (159줄 경량화)
        ├── CritiqueProgressWidget.tsx # [기존] ADR-05 4단계 비평 생성 프로그레스 위젯 (217줄)
        ├── GlobalCritiqueToast.tsx    # [기존] 백그라운드 비평 진행 전역 플로팅 토스트 (212줄)
        ├── CritiqueToolbarExportMenu.tsx # [신규] 문서 뷰어 툴바 복사/MD/PDF/Finder 열기 액션 그룹 (129줄)
        ├── CritiqueDocumentToolbar.tsx# [기존] 매거진 문서 뷰어 상단 툴바 헤더 (200줄 경량화)
        ├── CritiqueDocumentPhotoViewer.tsx # [기존] 매거진 문서 뷰어 좌측 사진 인스펙터 (줌/팬/EXIF HUD)
        ├── CritiqueDocumentArticle.tsx# [기존] 매거진 문서 뷰어 우측 페이퍼 문서 아티클 & 점수 가이드 트리거 (203줄)
        ├── CritiqueExportProgressOverlay.tsx # [기존] PDF/MD 내보내기 진행률 피드백 오버레이
        └── CritiqueDocumentModal.tsx  # [기존] 매거진 뷰어 모달 레이아웃 쉘 (143줄 경량화)
```

---

## 🤝 3. 타 도메인 참조 및 경계 계약 (Cross-Domain Dependencies)

* **참조하는 외부 도메인 (Inbound/Read)**:
  - `00_core_foundation`: `GPU_LOCK`, `ai_factory.get_gemma_adapter()`, Tauri `save_binary_file` 및 `reveal_in_finder` IPC 참조.
  - `01_indexing_storage`: `PhotoRepository`를 통해 `ai_analysis` 레코드 읽기/쓰기 수행.
* **외부 도메인에 노출하는 계약 (Outbound/Expose)**:
  - `02_search_curation`: `ai_analysis`의 정규화 평점 컬럼(`overall_score`, `iaa_score`, `iqa_score`, `ista_score`)을 노출하여 점수 기반 검색 및 스마트 앨범 조건 설정을 지원합니다.
  - `04_studio_ui_analytics`: 우측 상세 패널(`DetailPanel.tsx`) 내 탭 뷰(`PhotoCritiqueView`, `PhotoAiAnalysisView`) 및 전역 플로팅 토스트(`GlobalCritiqueToast`)를 제공합니다.

---

## 🔒 4. 도메인 아키텍처 제약 규칙

1. **비평 엔진 상호 배타적 메모리 수명주기**:
   - `UniPercept 8B`는 3-Way VR 채점 및 단일 패스 통합 지각 VQA 직후 `finally` 블록에서 즉시 가중치를 언로드하고 `torch.mps.synchronize()` 및 `empty_cache()`를 실행한 뒤 `Gemma 4` 직접 비평 작성 단계로 진입해야 합니다.
   - `Gemma 4 (MLX)`는 연속 요청 최적화를 위해 60초 Keep-alive 후 언로드하며, 비평 도중 사용자 취소 또는 예외 발생 시에는 두 모델 모두 즉시 언로드(`_unload_critique_models`)합니다.
2. **정량 평점 및 한/영 원문 정규화 원칙**:
   - 산출된 6-Way 앙상블 평점(`overall_score`, `iaa_score`, `iqa_score`, `ista_score`)과 UniPercept 영문 원문(`critique_en`)은 문자열 파싱에 의존하지 않도록 전용 DB 컬럼에 분리 저장하며, 기존 사용자의 데이터를 위해 기동 마이그레이션 시 레거시 비평 본문에서 점수를 자동 추출해 백필합니다.
