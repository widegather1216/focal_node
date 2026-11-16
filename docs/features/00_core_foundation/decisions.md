# [Decisions (ADR)] 00. Core Foundation

---

### [ADR-01] PyInstaller `--onedir` 패키징 및 Heavy 모듈 지연 임포트
- **배경**: `--onefile` 번들링 및 상단 `torch`/`mlx` Eager Import 시 앱 초기 기동에 15초 이상 소요됨.
- **결정**: `--onedir` 패키징을 기본으로 채택하고, 무거운 AI 라이브러리는 추론 워커 내부에서 Lazy Import 처리함.
- **영향**: 사이드카 포트 할당 출력 시간을 1초 이내로 단축.

### [ADR-02] UniPercept 8B 즉시 언로드 및 `GPU_LOCK` 직렬화
- **배경**: UniPercept(PyTorch MPS)가 약 28GB 메모리를 점유하여 Gemma 4(MLX)와 동시 상주 시 OOM 및 Metal Command Buffer 충돌 발생.
- **결정**: `GPU_LOCK = threading.RLock()`으로 추론을 직렬화하고, UniPercept는 추론 직후 `finally` 블록에서 즉시 `unload_model()` 및 `torch.mps.empty_cache()`를 호출함.
- **영향**: 32GB 통합 메모리 환경에서도 OOM 없이 안정적인 반복 비평 가능.

### [ADR-03] macOS `.app` 번들 사이드카 정적 배치 (`Contents/Resources/binaries/`)
- **배경**: PyInstaller 6.21 `--onedir` 바이너리가 `.app/Contents/MacOS/` 안에 위치하면 `--contents-directory`를 무시하고 `Contents/Frameworks/`를 강제 참조하며, `_internal` 내 점(`.`) 포함 디렉터리(`.dist-info`, `.dylibs`)로 인해 `Contents/Frameworks/` 직접 배치 시 `codesign`이 실패하고, Tauri `resources`의 심볼릭 링크 역참조 특성으로 PyInstaller `BUNDLE` 교차 링크도 유지할 수 없음.
- **결정**: [`src-tauri/tauri.macos.conf.json`](../../../src-tauri/tauri.macos.conf.json)에서 macOS 전용으로 `externalBin: []` 처리 후 `focal_node_backend`와 `_internal`을 함께 `Contents/Resources/binaries/`에 정적 배치하고, `lib.rs`의 런타임 심볼릭 링크·`DYLD_*` 변조를 제거함.
- **영향**: `/Applications`·DMG·App Translocation 등 `0o555` 비쓰기 번들에서 런타임 변조 없이 기동 및 `codesign --verify --deep --strict` 통과. 단, 향후 Developer ID + Notarization 도입 시 `Contents/Resources/binaries/` 하위 Mach-O(`focal_node_backend`, `Python`, `.dylib`, `.so`)의 안쪽-바깥쪽 사전 서명(`--options runtime --timestamp`) 단계가 필요함.
