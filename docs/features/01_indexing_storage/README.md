# 💾 [01_indexing_storage] Indexing Pipeline, Storage & RAW Media

- **현재 상태 (Lifecycle)**: `📐 Planning (Baseline 완료 / 스마트 오프라인 Step 1~4 대기)`
- **구현 진척도**: `[□□□□] 0/4 Steps (Active Iteration)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 1건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

로컬 폴더 스캔, SHA-256 해싱, EXIF 추출, 360px 썸네일 캐싱, SigLIP 2 시각 임베딩/제로샷 태깅, Gemma 4 캡션/태그 생성 및 고용량 RAW 인메모리 스트리밍을 담당하는 도메인입니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### ✅ Current Baseline (As-Is 기구현 완료)
- [x] 로컬 폴더 등록/삭제 및 SHA-256 원자적 해싱
  - 📂 구현: [`indexing.py`](../../../backend/app/api/indexing.py), [`folders.py`](../../../backend/app/api/folders.py), [`indexing_service.py`](../../../backend/app/services/indexing_service.py) | 🧪 테스트: [`test_api_indexing.py`](../../../backend/tests/test_api_indexing.py), [`test_api_folders.py`](../../../backend/tests/test_api_folders.py) (`PASS`)
- [x] EXIF 메타데이터 추출 및 360px sRGB JPEG 썸네일 디스크 캐싱
  - 📂 구현: [`image.py`](../../../backend/app/utils/image.py), [`photo.py`](../../../backend/app/services/photo.py) | 🧪 테스트: [`test_api_photos.py`](../../../backend/tests/test_api_photos.py) (`PASS`)
- [x] SigLIP 2 768차원 임베딩/제로샷 힌트 추출, Gemma 4 캡션/태그 생성 및 ChromaDB + SQLite WAL 보상 트랜잭션
  - 📂 구현: [`pipeline.py`](../../../backend/app/services/pipeline.py), [`taxonomy.py`](../../../backend/app/services/taxonomy.py), [`atomic_transaction.py`](../../../backend/app/repositories/atomic_transaction.py) | 🧪 테스트: [`test_siglip_zero_shot.py`](../../../backend/tests/test_siglip_zero_shot.py) (`PASS`)
- [x] RAW 원본 인메모리 스트리밍(`MAX_CONCURRENT_DECODES=3`), 단일 사진 재분석(`POST /api/photos/{id}/reindex`) 및 다중 사진 SSE 내보내기
  - 📂 구현: [`photos.py`](../../../backend/app/api/photos.py), [`ActionBar.tsx`](../../../src/components/ActionBar.tsx) | 🧪 테스트: [`test_api_photos.py`](../../../backend/tests/test_api_photos.py) (`PASS`)

### 🚀 Active Iteration: 비파괴적 스마트 오프라인 관리 (Ghost Photos) `[To-Be]`
- [ ] **Step 1 [DB & Types]**: `models.py`의 `Image` 모델에 `is_offline: Boolean` 컬럼/마이그레이션 추가 및 `schemas.py`, `src/types/photo.ts`에 `is_offline` 반영
- [ ] **Step 2 [Repo & API]**: `PhotoRepository`에 오프라인 상태 일괄 마킹 및 명시적 정리(`POST /api/folders/prune-offline`) 엔드포인트 추가
- [ ] **Step 3 [Service & State]**: `indexing_service.py`의 자동 삭제(`cleanup_zombie_records`)를 `is_offline=True` 마킹으로 변경
- [ ] **Step 4 [UI & Integration]**: `PhotoCard.tsx`에 `[Offline]` 배지/회색조 필터 적용 및 `FullscreenViewer.tsx` 원본 연결 안내 표시

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-10-17 / clean-code-auditor / 인덱싱 도메인 API 계약(/api/index/*) 교정 및 정적 감사`
- **생성/수정된 핵심 파일**:
  - `docs/features/01_indexing_storage/*`: `pipeline.py` 4단계 구조, `/api/index/*` 경로, `POST /api/photos/{id}/reindex`, `Photo` 타입 명세 동기화
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_api_indexing.py backend/tests/test_api_folders.py backend/tests/test_api_photos.py backend/tests/test_siglip_zero_shot.py`
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `is_offline` Step 1 착수 시 또는 `REFACTOR-01` 해결 시 `src/types/photo.ts`의 레거시 EXIF 필드명(`focal_length_in_35mm`, `exposure_time`)을 백엔드 `schemas.py`(`focal_length_35mm`, `shutter_speed`)와 일치시킬 것.
