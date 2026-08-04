# [기획 / 향후 구현 예정] 스마트 앨범 (Smart Albums) 기획 및 구현 명세서

## 1. 개요
자주 사용하는 복잡한 검색 조건(자연어 검색어 + 메타데이터 필터)을 저장해두고, 사이드바에서 원클릭으로 불러올 수 있는 기능입니다. 아마추어/전문 사진가들이 특정 조건(예: "별점 4점 이상 + 35mm 환산화각 85mm + 인물 사진")을 매번 세팅하지 않도록 워크플로우를 대폭 단축시킵니다.

---

## 2. 데이터베이스 스키마 (`backend/app/models.py`)
새로운 `SmartAlbum` 테이블을 추가합니다:
- `id` (VARCHAR(64), Primary Key): 고유 식별자 (UUID)
- `name` (VARCHAR(100)): 앨범 이름 (예: "야간 인물 85mm")
- `query_text` (TEXT, Nullable): 자연어 검색어
- `filters` (TEXT, Nullable): JSON 형태의 EXIF 필터 조건 (조리개, ISO, 날짜 범위, 카메라/렌즈 등)
- `created_at` (DATETIME): 생성 일자

---

## 3. 백엔드 서비스 & API 계층 (`services/smart_album_service.py` & `api/smart_albums.py`)
3계층 아키텍처 규격에 따라 `SmartAlbumRepository` 및 `SmartAlbumService`를 통해 다음 엔드포인트들을 노출합니다:
- `GET /api/smart-albums`: 저장된 스마트 앨범 목록 반환
- `POST /api/smart-albums`: 현재 상태의 검색어와 필터 정보를 받아 새로운 스마트 앨범 저장
- `DELETE /api/smart-albums/{id}`: 스마트 앨범 삭제

---

## 4. 프론트엔드 UI (`src/components/`)
### 4.1. 저장 버튼 (ActionBar / SearchFilterMenu)
- 검색 필터나 텍스트 검색어가 하나라도 활성화된 상태일 때, 화면 상단의 액션바 우측에 `[+ Save as Smart Album]` 버튼을 노출합니다.
- 클릭 시 모달창을 띄워 앨범의 이름(name)을 입력받아 POST 요청을 전송합니다.

### 4.2. 사이드바 연동 (`src/components/Sidebar.tsx`)
- 사이드바의 'Folders' 구역 아래에 **'Smart Albums'** 세션을 추가합니다.
- 스마트 앨범을 클릭하면 저장된 `query_text`와 `filters` 값을 전역 상태 스토어(`useAppStore`)에 적용하여 갤러리 검색 결과를 자동 갱신합니다.
