# 기여 가이드 (Contributing Guidelines)

Focal Node 프로젝트에 관심을 가져주셔서 감사합니다! 이 문서는 프로젝트에 기여하는 방법과 절차를 안내합니다.

## 피드백 및 버그 리포트

앱을 사용해 보시고 발견한 버그나, 추가되었으면 하는 기능이 있다면 언제든지 환영합니다. 베타 기간 동안의 소중한 피드백은 앱을 개선하는 데 큰 도움이 됩니다.

1. **이슈(Issues) 탭**으로 이동해주세요.
2. `New issue` 버튼을 클릭합니다.
3. 양식에 맞게 `버그 리포트` 또는 `기능 제안`을 선택하여 내용을 작성해 주세요.

## 코드 기여 (Pull Requests)

직접 코드를 수정하여 기여하고 싶으시다면 다음 절차를 따라주세요:

1. 이 저장소를 Fork 합니다.
2. 새로운 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`).
3. 변경 사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`).
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`).
5. Pull Request를 생성합니다.

### 개발 환경 설정
로컬 개발 환경 설정 방법은 `README.md`의 [로컬 환경 실행 방법] 부분을 참고해주세요.

## 📦 앱 패키징 빌드 방법 (.dmg)

독립 실행형 앱(App Bundle 및 DMG)으로 직접 빌드하여 기여하고 싶으시다면 다음 절차를 따릅니다.
우선 Python 백엔드를 단일 바이너리로 컴파일해야 합니다.

```bash
# 1. PyInstaller로 백엔드 빌드 (가상환경 활성화 상태)
python3 backend/build_backend.py

# 2. 빌드된 바이너리를 Tauri 사이드카 디렉토리로 이동 (Apple Silicon 기준)
cp dist/focal_node_backend src-tauri/binaries/focal_node_backend-aarch64-apple-darwin

# 3. Tauri 앱 빌드
npm run tauri build
```
빌드가 완료되면 `src-tauri/target/release/bundle/dmg/` 경로에 배포용 `.dmg` 파일이 생성됩니다.
