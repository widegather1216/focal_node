# 💾 [01_indexing_storage] Indexing Pipeline, Storage & RAW Media

- **현재 상태 (Lifecycle)**: `🩹 Debugging (DEFECT-01 해결 완료 / DEFECT 10건 잔여 디버깅 진행 중)`
- **구현 진척도**: `[□□□□] 0/4 Steps (Active Iteration)`
- **미해결 티켓 현황**: `🚨 DEFECT: 10건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
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

- **직전 완료 작업**: `2026-11-08 / systematic-debugger / DEFECT-01 해결 완료 (VectorRepository.get_embedding_by_id ndarray 크래시 해소 및 TC-IDX-07 PASS)`
- **해결된 결함 (Resolved Defect)**:
  - `DEFECT-01`: ChromaDB `get(include=["embeddings"])` 반환 `numpy.ndarray`에 대한 직접 불리언 평가 제거, Guard Clause 및 `.tolist()` 변환으로 100% `ValueError` 크래시 방지 및 단일 사진 재인덱싱/유사도 검색 안정화.
- **잔여 우선순위 결함 (Open DEFECT Logs)**:
  - `DEFECT-02`: `VectorRepository.delete` 예외 삼킴으로 인한 `delete_and_commit` 보상 트랜잭션 무력화 및 ChromaDB 좀비 벡터 영구 잔류
  - `DEFECT-03`: `start_indexing` / `sync_database` TOCTOU 동시성 레이스로 인한 중복 인덱서 실행 및 ChromaDB 벡터 영구 소실
  - `DEFECT-04`: `_commit_batch_with_retry` 3회 실패 시 예외 삼킴으로 인한 대규모 사진 유실 및 거짓 정상 완료(`status="idle"`) 위장
  - `DEFECT-05`: `index_single_file_sync` 선행 삭제(Delete-Before-Commit)로 인한 수정 파일 재인덱싱 중단/실패 시 데이터 영구 증발
  - `DEFECT-06`: macOS NFD/NFC 정규화 불일치로 인한 `_identify_zombie_photo_ids`의 한글 폴더 사진 전량 오삭제
  - `DEFECT-07~11`: ExifRead `values=[]` IndexError, 비동기 라우트 동기 DB 쿼리 이벤트 루프 동결, `_pause_loop` 고착, 내보내기 허위 성공 표시, `DELETE /api/folders` 무검증 재귀 삭제
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_backend_hardening.py -k test_tc_idx_07_get_embedding_by_id_ndarray_and_boundary` (PASS)
  - `./venv/bin/pytest backend/tests/` (133 passed)
  - `python3 -B ~/.gemini/config/skills/interactive-feature-planner/scripts/check_wiki_health.py docs` (exit 0)
- **다음 세션 포커스 및 추천 프롬프트**:
  - `DEFECT-02` 해결: `"01_indexing_storage 도메인의 DEFECT-02 티켓 해결해줘"` (VectorRepository.delete 예외 삼킴 제거 및 보상 트랜잭션 SQLite 롤백 복구)
