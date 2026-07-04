# Focal Node

Focal Node는 프라이버시를 완벽히 보호하며, 클라우드 전송 없이 로컬에서 동작하는 AI 기반 자연어 사진 검색 데스크탑 애플리케이션입니다.
Apple Silicon(M 시리즈)의 GPU 자원을 활용하여, 수만 장의 사진 속 시각적 정보와 메타데이터를 인덱싱하고 분석합니다.

## ✨ 주요 기능
* **자연어 시맨틱 검색:** "비 오는 날 카페에서 커피 마시는 고양이"와 같은 자연어로 로컬의 사진을 검색합니다.
* **유사 이미지 검색 (Tone & Mood):** 컬러 그레이딩과 분위기(무드)가 비슷한 사진들을 레퍼런스로 즉시 찾아줍니다.
* **100% 로컬 오프라인 처리:** 사진 데이터나 개인정보가 절대로 외부 서버로 전송되지 않습니다.
* **자동 AI 캡션 및 메타데이터 태깅:** 사진의 의미를 파악하여 자동으로 캡션과 태그를 부여합니다.
* **주요 이미지 포맷 지원:** JPEG, PNG, WebP 등의 이미지 포맷을 우선적으로 지원하며 쾌적하게 뷰잉할 수 있습니다.

## 🚀 베타 버전 다운로드 및 피드백

현재 Mac(Apple Silicon) 전용 데스크탑 앱 오픈 베타를 진행 중입니다!
1. **다운로드**: GitHub의 [Releases 페이지](https://github.com/widegather1216/focal_node/releases)에서 최신 `.dmg` 파일을 다운로드 및 설치해 주세요.
2. **피드백**: 앱 사용 중 발견한 버그나 원하시는 기능은 [Issues 탭](https://github.com/your-username/focal_node/issues)에 남겨주시면 감사하겠습니다.

## 🛠 아키텍처
* **Frontend:** Tauri (Rust), React 19, TypeScript, Vite, Zustand
* **Backend (Sidecar):** FastAPI, SQLite, ChromaDB
* **AI Engine:** MLX (Apple Native), PyTorch (MPS)
* **Models:** SigLIP 2 (google/siglip2-base-patch16-224), Gemma 4 E4B-it (mlx-community/gemma-4-e4b-it-4bit)

## 🚀 로컬 환경 실행 방법 (개발자용)

**사전 요구사항:**
* Apple Silicon Mac (M1 이상)
* Node.js v18 이상
* Python 3.10 이상
* Rust (Cargo)

```bash
# 1. 저장소 클론
git clone https://github.com/your-username/focal_node.git
cd focal_node

# 2. Python 백엔드 설정 (가상환경)
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 3. 프론트엔드 종속성 설치
npm install

# 4. 개발 서버 실행 (Tauri 앱 및 Sidecar 동시 기동)
npm run tauri dev
```

> **참고:** 최초 실행 시 백그라운드에서 AI 모델 다운로드 및 초기 세팅이 진행되므로 인터넷 연결 상태에 따라 다소 시간이 걸릴 수 있습니다. 세팅이 완료된 이후부터는 완전한 오프라인으로 작동합니다.

## ⚖️ 라이선스 및 AI 모델 정책

본 프로젝트의 소스코드는 **[MIT License](LICENSE)**에 따라 자유롭게 사용 및 배포가 가능합니다. 

단, 앱 내에서 구동되는 **AI 모델 가중치(Weights)**는 본 저장소에 포함되어 있지 않으며, 구동 시 로컬로 다운로드 됩니다. 각 모델은 다음의 라이선스를 따릅니다:

* **SigLIP 2** (Google): [Apache 2.0 License](https://github.com/google-research/big_vision/blob/main/LICENSE)
* **Gemma** (Google): [Gemma Terms of Use](https://ai.google.dev/gemma/terms) (상업적 이용 및 연구 목적 허용, 약관 준수 필수)

Focal Node는 모델 자체를 재배포하지 않으며, 사용자의 로컬 환경에서 Hugging Face 허브를 통해 모델을 다운로드하여 사용합니다.
