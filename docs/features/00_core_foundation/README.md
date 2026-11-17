# 🏛️ [00_core_foundation] Core Foundation & System Architecture

- **현재 상태 (Lifecycle)**: `🟢 Sign-Off (DEFECT-01~11 · REFACTOR-01 전수 해결 및 100% PASS)`
- **구현 진척도**: `[■■■■] 4/4 Steps`
- **미해결 티켓 현황**: `🚨 DEFECT: 0건` | `🧐 REFACTOR: 0건` ([`verification.md`](./verification.md) 참조)
- **관련 문서**: [`architecture.md`](./architecture.md) | [`spec.md`](./spec.md) | [`verification.md`](./verification.md) | [`decisions.md`](./decisions.md)

---

## 🎯 1. 도메인 개요 (Overview)

**Focal Node**의 전역 3-Tier 아키텍처, Tauri-FastAPI 동적 포트 브릿지, 하드웨어/런타임 6대 제약사항(`GPU_LOCK`, SQLite WAL, 모델 Keep-alive/즉시 언로드) 및 백그라운드 AI 모델 다운로더를 정의하는 헌법 도메인입니다.

---

## 🗺️ 2. 계층별 구현 로드맵 (Layer-Chunked Roadmap)

### ✅ Baseline (As-Is 기구현 완료)
- [x] **Step 1 [Schema & Config]**: 환경별 데이터 경로 격리(`IS_PROD`), SQLite WAL & 외래키 리스너, 자동 스키마 마이그레이션(`run_migrations`) 및 ChromaDB Self-Healing 초기화
  - 📂 구현: [`config.py`](../../../backend/app/config.py), [`database.py`](../../../backend/app/database.py), [`chroma.py`](../../../backend/app/chroma.py), [`ports.py`](../../../backend/app/core/ports.py)
- [x] **Step 2 [Sidecar Host & System API]**: Tauri 동적 포트(`port=0`) 스폰/IPC 브릿지, 부모 프로세스 감시(`watch_parent`), `/api/health` 및 `/api/system/models/*` 라우트
  - 📂 구현: [`lib.rs`](../../../src-tauri/src/lib.rs), [`main.py`](../../../backend/app/main.py), [`process.py`](../../../backend/app/utils/process.py) | 🧪 테스트: [`test_backend_hardening.py`](../../../backend/tests/test_backend_hardening.py) (`PASS`)
- [x] **Step 3 [AI Lifecycle & Model Downloader]**: `GPU_LOCK` 직렬화, `BaseKeepAliveModel` 60초 타이머, HuggingFace 백그라운드 다운로더 및 진행률 트래커
  - 📂 구현: [`base_model.py`](../../../backend/app/services/base_model.py), [`ai_factory.py`](../../../backend/app/services/ai_factory.py), [`model_downloader.py`](../../../backend/app/services/model_downloader.py) | 🧪 테스트: [`test_model_downloader.py`](../../../backend/tests/test_model_downloader.py), [`test_concurrency_hardening.py`](../../../backend/tests/test_concurrency_hardening.py) (`PASS`)
- [x] **Step 4 [Client Bootstrapping & Splash UI]**: 포트 조회/헬스체크 훅, Tauri 네이티브 이벤트 리스너, 스플래시 및 모델 다운로드 모달
  - 📂 구현: [`App.tsx`](../../../src/App.tsx), [`useBackendInit.ts`](../../../src/hooks/useBackendInit.ts), [`useTauriEvents.ts`](../../../src/hooks/useTauriEvents.ts), [`useModelDownloadStatus.ts`](../../../src/hooks/useModelDownloadStatus.ts), [`AppSplash.tsx`](../../../src/components/common/AppSplash.tsx), [`ModelDownloadModal.tsx`](../../../src/components/ModelDownloadModal.tsx)

---

## 🔄 3. Latest Session Handoff (최근 세션 인계 노트)

- **직전 완료 작업**: `2026-11-17 / systematic-debugger / 00_core_foundation DEFECT-11 해결 및 🟢 Sign-Off 복귀 (532dca1)`
- **조치 요약 (`DEFECT-11` RESOLVED)**:
  - `src-tauri/src/lib.rs` (`#L138-L247`): `validate_export_save_path` 및 헬퍼 4종(`validate_export_raw_input`, `validate_export_filename`, `is_blocked_system_dir`, `ensure_safe_export_target`)을 도입해 상대경로·NUL·`..`/`.`/끝 슬래시·숨김 파일(`.zshrc`, `.env`)·`.pdf`/`.md` 외 확장자·미존재 부모·루트(`/`) 및 보호 시스템 경로(`/System`, `/Library`, `/usr`, `/bin`, `/sbin`, `/etc`, `/private/etc`, `/dev`, `/cores`, `/Applications`, `/private/var/root|db|log`, 대소문자 무구분 `*.app`)·심볼릭 링크 및 비정규 파일 타깃 덮어쓰기를 차단하고 정상 `.pdf`/`.md` 저장 계약(`spec.md#3.1`)은 100% 유지.
  - `src-tauri/tauri.conf.json` (`#L20-L23`): `"csp"` 보안 정책(`script-src 'self'`, `object-src 'none'`, `base-uri 'self'`, `style-src 'self' 'unsafe-inline'`, FastAPI `127.0.0.1:*`/`localhost:*`, `blob:`/`data:`/`ipc:`) 및 `"dangerousDisableAssetCspModification": ["style-src"]`를 적용해 프로덕션 번들 Tauri 자동 `style-src` nonce 주입으로 인한 `'unsafe-inline'` 무효화를 방지.
  - `src-tauri/src/lib.rs` (`#L644-L759`): `test_save_binary_file_rejects_unsafe_paths`, `test_save_binary_file_allows_valid_pdf_and_markdown_exports`, `test_tauri_conf_csp_hardening` 단위 테스트 추가 및 Red ➔ Green 입증.
- **남은 핵심 결함**: 없음 (`🚨 DEFECT: 0건 | 🧐 REFACTOR: 0건` — `00_core_foundation` 12/12 `100% PASS` `🟢 Sign-Off`)
- **검증 명령어**: `cargo test --manifest-path src-tauri/Cargo.toml --lib` (`6 passed`), `./venv/bin/pytest backend/tests/ -q` (`166 passed`), `npx tsc --noEmit && npm run build` (`PASS`), `python3 -B ~/.gemini/config/skills/interactive-feature-planner/scripts/check_wiki_health.py docs` (`exit code 0`)
- **다음 세션 포커스 및 주의사항 (Caveats)**:
  - `00_core_foundation` Sign-Off 완료. 대기 중인 다음 도메인 `04_studio_ui_analytics` Step 3~4 개발 진행 권장 (`"04_studio_ui_analytics 도메인 Step 3 개발 진행해줘"`).
  - (교차 도메인 참고) `01_indexing_storage`의 `folder_manager.py#L50-L65` `purge_photo_records_batch`도 `db.commit()` 전 썸네일/Chroma 선삭제 경합이 존재함.
