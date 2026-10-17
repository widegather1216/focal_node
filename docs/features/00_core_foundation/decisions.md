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
