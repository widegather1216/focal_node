# 💾 [01_indexing_storage] Indexing Pipeline, Storage & RAW Media

- **현재 상태 (Lifecycle)**: `🩹 Debugging (DEFECT-01~04 해결 완료 / DEFECT 7건 잔여 디버깅 진행 중)`
- **구현 진척도**: `[□□□□] 0/4 Steps (Active Iteration)`
- **미해결 티켓 현황**: `🚨 DEFECT: 7건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
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

- **직전 완료 작업**: `2026-11-10 / systematic-debugger + atomic-commit-crafter / DEFECT-04 해결 및 원자적 커밋 완료 (6ffe113, 6cba0eb / TC-IDX-10 PASS)`
- **Recent Commits (2026-11-10 21:04)**:
  - `6ffe113` - `fix(indexing): propagate batch commit errors and isolate run lifecycle`
  - `6cba0eb` - `fix(ui): surface indexing errors in tauri bridge and progress card`
- **해결된 결함 (Resolved Defect)**:
  - `DEFECT-04`: `_commit_batch_with_retry`에서 세션 롤백 후 3회 실패 시 예외를 재전파하도록 수정하고, `IndexingStateManager`에 `run_id` 세대 격리·원자적 `finalize_run`·`error_message`를 도입해 예외 및 `BaseException` 발생 시 후속 청크 실행과 거짓 완료 로그(`Background indexing completed.`/`Sync completed.`) 발행을 차단하고 `status="error"`로 전이하도록 조치. Tauri `indexing-error` 이벤트, Zustand `reportIndexingError`/`dismissIndexingError`, `useIndexingStatus` `'error'` 분기, `IndexingProgressCard` 에러 전용 UI까지 전 계층 정합성을 보완함.
  - `DEFECT-03`: `IndexingStateManager`에 원자적 상태 선점 메서드 `try_start_indexing()`을 도입하여 락 내부에서 즉시 `"processing"`을 선점하고 중복 요청을 400 거부하도록 조치. 경로/DB 작업 예외 발생 시 `reset_status()` 안전 롤백 및 `run_indexing_background` startup 시 `initialize_background_run()`으로 상태가 순간적으로 `idle`로 풀리는 레이스를 원천 차단하여 중복 인덱서 실행 및 ChromaDB 벡터 영구 소실 해소.
  - `DEFECT-02`: `VectorRepository.delete`에서 ChromaDB `collection.delete` 실패 시 예외를 삼키던 결함을 제거하고 `logger.error` 후 `raise`로 재전파. `CompensatingTransactionManager.delete_and_commit`이 예외를 감지하여 SQLite `commit`을 방지하고 `rollback`을 수행함으로써 SQLite만 삭제되고 ChromaDB에 좀비 벡터가 영구 잔류하는 정합성 붕괴 완전 해소.
  - `DEFECT-01`: ChromaDB `get(include=["embeddings"])` 반환 `numpy.ndarray`에 대한 직접 불리언 평가 제거, Guard Clause 및 `.tolist()` 변환으로 100% `ValueError` 크래시 방지 및 단일 사진 재인덱싱/유사도 검색 안정화.
- **잔여 우선순위 결함 (Open DEFECT Logs)**:
  - `DEFECT-05`: `index_single_file_sync` 선행 삭제(Delete-Before-Commit)로 인한 수정 파일 재인덱싱 중단/실패 시 데이터 영구 증발
  - `DEFECT-06`: macOS NFD/NFC 정규화 불일치로 인한 `_identify_zombie_photo_ids`의 한글 폴더 사진 전량 오삭제
  - `DEFECT-07~11`: ExifRead `values=[]` IndexError, 비동기 라우트 동기 DB 쿼리 이벤트 루프 동결, `_pause_loop` 고착, 내보내기 허위 성공 표시, `DELETE /api/folders` 무검증 재귀 삭제
- **검증 완료된 테스트 실행 명령어**:
  - `./venv/bin/pytest backend/tests/test_backend_hardening.py -k test_tc_idx_10` (PASS)
  - `./venv/bin/pytest backend/tests/` (136 passed)
  - `npx tsc --noEmit && npm run build` (PASS)
  - `cargo check --manifest-path src-tauri/Cargo.toml` (PASS)
  - `python3 -B ~/.gemini/config/skills/interactive-feature-planner/scripts/check_wiki_health.py docs` (exit 0)
- **다음 세션 포커스 및 추천 프롬프트**:
  - `DEFECT-05` 해결: `"01_indexing_storage 도메인의 DEFECT-05 티켓 해결해줘"` (`index_single_file_sync` 재인덱싱 중단 시 기존 레코드 보존)
