# 💾 [01_indexing_storage] Indexing Pipeline, Storage & RAW Media

- **현재 상태 (Lifecycle)**: `📐 Planning (Baseline 완료 / 오프라인·Relocation·2-Pass 인덱싱 Step 1~4 대기)`
- **구현 진척도**: `[□□□□] 0/4 Steps (Active Iteration)`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

로컬 폴더 스캔, SHA-256 해싱, EXIF 추출, 360px 썸네일 캐싱, SigLIP 2 시각 임베딩/제로샷 태깅, Gemma 4 캡션/태그 생성, 파일 이동·이름 변경 자동 재연결(Relocation), 2-Pass 점진적 인덱싱 및 고용량 RAW 인메모리 스트리밍을 담당하는 도메인입니다.

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

### 🚀 Active Iteration: 스마트 오프라인, SHA-256 Relocation & 2-Pass 점진적 인덱싱 `[To-Be]`
- [ ] **Step 1 [DB & Types]**: `models.py`의 `Image`에 `is_offline: Boolean` 컬럼/마이그레이션 추가, `IndexingStatusResponse`에 `phase: "fast_preview" | "ai_enrichment"` 추가 및 `src/types/photo.ts` 동기화
- [ ] **Step 2 [Repo & API]**: `PhotoRepository`에 오프라인 마킹, SHA-256 경로 재연결(`relocate_photo_path`), 미분석 사진 조회(`get_pending_ai_photos`) 및 `POST /api/folders/prune-offline` 엔드포인트 추가
- [ ] **Step 3 [Service & Pipeline]**: `pipeline.py` 및 `indexing_service.py`를 **Pass 1(해시+EXIF+썸네일 즉시 커밋)** ➔ **Pass 2(백그라운드 SigLIP 2+Gemma 4 비동기 보강)** 2-Pass 구조로 분리하고, 파일 이동/이름 변경 시 비평·즐겨찾기 보존 재연결(`relocated`) 및 오프라인 마킹 적용
- [ ] **Step 4 [UI & Integration]**: `PhotoCard.tsx`에 `[Offline]` 및 `[AI 분석 대기]` 배지 렌더링, `IndexingProgressCard.tsx`에 2-Pass 단계 표시 및 `FullscreenViewer.tsx` 원본 연결 안내 표시

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-11-03 / systematic-debugger / REFACTOR-01 해결 완료 (PhotoMetadata 필드 일원화, IndexedFolder 레포지토리 캡슐화, 썸네일 캐시 Silent Fail 제거 및 명시적 예외 로깅)`
- **생성/수정된 핵심 파일**:
  - `src/types/photo.ts`, `src/components/gallery/PhotoCard.tsx`: `focal_length_35mm`, `shutter_speed` 필드 통일
  - `backend/app/repositories/photo_repository.py`: `list_folders()`, `get_folder_by_path()`, `add_folder()` 레포지토리 메서드 신설
  - `backend/app/api/folders.py`, `backend/app/api/indexing.py`: 직접 DB 쿼리 제거 및 `PhotoRepository` 캡슐화
  - `backend/app/services/indexing_service.py`, `backend/app/services/photo.py`, `backend/app/api/photos.py`: `except Exception: pass` 제거 및 `FileNotFoundError`/`OSError` 로깅
  - `backend/tests/test_api_folders.py`: `test_photo_repository_folder_methods` 단위 테스트 추가
- **검증 완료된 테스트 실행 명령어**:
  - `npx tsc --noEmit && npm run build`
  - `./venv/bin/pytest backend/tests/test_api_folders.py backend/tests/test_api_indexing.py backend/tests/test_api_photos.py`
  - `./venv/bin/pytest backend/tests/`
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - 스마트 오프라인, SHA-256 Relocation & 2-Pass 점진적 인덱싱 Step 1 [DB & Types] 구현 대기. Step 3 구현 시 파일 스캔/Relocation 패스를 먼저 수행한 뒤 마지막에 실종 파일을 `is_offline=True`로 마킹해야 함.
