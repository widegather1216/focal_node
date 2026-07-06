# 스마트 앨범 (Smart Albums) 구현 기획서

## 1. 개요
자주 사용하는 복잡한 검색 조건(자연어 검색어 + 메타데이터 필터)을 저장해두고, 사이드바에서 원클릭으로 불러올 수 있는 기능입니다. 아마추어/전문 사진가들이 특정 조건(예: "별점 4점 이상 + 화각 85mm + 인물 사진")을 매번 세팅하지 않도록 워크플로우를 대폭 단축시킵니다.

## 2. 데이터베이스 스키마 (`backend/app/models.py`)
새로운 `SmartAlbum` 테이블을 추가합니다.
- `id`: 고유 식별자 (UUID, String 64)
- `name`: 앨범 이름 (예: "야간 인물 85mm")
- `query_text`: 자연어 검색어 (String, nullable)
- `filters`: JSON 형태의 EXIF 필터 조건 (String, JSON)
- `created_at`: 생성 일자

## 3. 백엔드 API (`backend/app/api/smart_albums.py`)
다음 엔드포인트들을 신설합니다:
- `GET /api/smart-albums`: 저장된 스마트 앨범 목록 반환
- `POST /api/smart-albums`: 현재 상태의 검색어와 필터 정보를 받아 새로운 스마트 앨범으로 DB에 저장
- `DELETE /api/smart-albums/{id}`: 앨범 삭제

## 4. 프론트엔드 UI (`src/components/`)
### 4.1. 저장 버튼 (ActionBar / SearchFilterMenu)
- 검색 필터나 텍스트 검색어가 하나라도 활성화된 상태일 때, 화면 상단의 액션바 우측에 `[+ Save as Smart Album]` 버튼을 노출합니다.
- 클릭 시 모달창을 띄워 앨범의 이름(name)을 입력받아 POST 요청을 보냅니다.

### 4.2. 사이드바 연동 (Sidebar.tsx)
- 사이드바의 'Folders' 영역 아래에 **'Smart Albums'** 구역을 추가합니다.
- 백엔드에서 앨범 목록을 불러와 리스트 형태로 렌더링합니다.
- 앨범을 클릭하면, 저장되어 있던 `query_text`와 `filters` 값을 전역 상태 스토어(`useAppStore`)에 덮어씌웁니다.
- 스토어 값이 업데이트되면 기존 검색 로직이 자동으로 트리거되어, 즉시 해당 조건의 사진들이 갤러리에 나타납니다.

## 5. 단계별 개발 가이드
1. `models.py`에 `SmartAlbum` 모델 추가 후 DB 마이그레이션 적용 (ALTER TABLE 혹은 자동 생성 쿼리).
2. `smart_albums.py` 라우터 작성 및 `main.py`에 등록.
3. Zustand(`useAppStore.ts`)에 스마트 앨범 목록을 관리하는 상태 및 fetch/post/delete 액션 추가.
4. `Sidebar.tsx` 및 `ActionBar.tsx`에 UI 구현 및 테스트.
