# [Decisions (ADR)] 03. On-Demand AI Critique & Editorial Export

---

### [ADR-01] 2단계 지연 분석 파이프라인 (경량 인덱싱 태깅과 심층 비평의 분리)
- **배경**: 1단계 폴더 인덱싱 시점에 수천 장의 사진에 대해 무거운 다중 패스 심층 비평(UniPercept 8B 6-Pass 채점/비평 + Gemma 4 2-Pass 번역/구조화)까지 전수 실행하면 초기 인덱싱이 수십 시간 지연됨.
- **결정**: 1단계 인덱싱에서는 검색에 필수적인 SigLIP 2 임베딩/제로샷 힌트와 Gemma 4 경량 캡션/태그(`generate_caption_and_tags`)만 추출하고, 고비용 심층 비평은 사용자가 선택한 사진에 대해서만 온디맨드로 수행한 뒤 `ai_analysis.critique`에 영구 캐싱함.
- **영향**: 초기 인덱싱 속도를 유지하면서도 필요한 사진에 최고 품질의 2-모델 협업 전문 비평 제공.

### [ADR-02] 클라이언트 사이드 에디토리얼 PDF/Markdown 생성
- **배경**: 백엔드에서 PDF 렌더링 라이브러리(wkhtmltopdf 등)를 번들링하면 PyInstaller 용량 증가 및 OS 폰트 의존성 문제가 발생함.
- **결정**: 프론트엔드 `CritiqueDocumentModal`에서 브라우저 네이티브 폰트와 `jsPDF`를 활용하여 클라이언트 사이드로 PDF/Markdown을 생성함.
- **영향**: 사이드카 바이너리 경량화 및 화면에 보이는 매거진 타이포그래피와 동일한 PDF 출력 품질 확보.
