# [Doc 10] Focal Node 디자인 시스템 및 UI/UX 테마 가이드
## 「The Neutral Dark Studio (중립 다크 스튜디오)」

본 문서는 **Focal Node (AI 기반 로컬 사진 검색 데스크탑 앱)**의 핵심 가치와 목적에 완벽히 부합하는 단일 디자인 테마인 **「The Neutral Dark Studio」**의 철학, 디자인 토큰(색상, 타이포그래피, 간격), 컴포넌트 규격 및 구현 가이드를 정의합니다.

---

## 🏛️ 1. 디자인 철학 및 목적성 (Design Philosophy)

### 1.1. 앱의 본질적 존재 이유
> **"수만 장의 대용량 사진(RAW 포함) 속에서, 원하는 찰나를 AI 자연어로 0.1초 만에 찾아내는 고성능 로컬 검색 & 아카이브 워크스페이스"**

### 1.2. 3대 핵심 디자인 원칙

1. **Content-First & Invisible UI (사진이 주인공인 투명한 인터페이스)**
   * UI 요소는 사진의 색감, 콘트라스트, 화이트밸런스를 왜곡하지 않도록 철저히 중립적인 무채색 다크 톤 뒤로 물러납니다.
   * 불필요한 장식(폴라로이드 프레임, 빈티지 텍스처 등)을 배제하여 뷰포트의 90% 이상을 실제 사진 픽셀에 할애합니다.

2. **Search-First & High-Throughput (검색 중심 및 대량 고속 탐색)**
   * macOS Spotlight나 Raycast처럼 키보드 중심(`Cmd + K`)으로 즉각 활성화되는 직관적인 검색 경험을 제공합니다.
   * 수천 장을 끊김 없이 훑어볼 수 있도록 여백을 최소화하고, 시각적 노이즈를 제어합니다.

3. **Mechanical Precision (카메라 장비의 정밀함)**
   * 아날로그의 감성은 겉모습의 키치한 장식이 아니라, 라이카나 핫셀블라드 같은 **고급 기계식 카메라의 선명한 조작감과 각인 폰트(Monospace EXIF)**를 통해 고급스럽게 전달합니다.

---

## 🎨 2. 디자인 토큰 및 컬러 시스템 (Color Palette)

사진의 암부와 명부를 가장 정확하게 인지할 수 있는 **Zinc/Neutral Charcoal 계열**의 모노크롬 팔레트를 기본으로 하며, 카메라 렌즈의 레드 도트에서 모티브를 얻은 **원 포인트 액센트(Focal Red)**만 극도로 절제하여 사용합니다.

```
[Background] #09090b (Obsidian Black)
    │
    ├─ [Surface / Sidebar] #121215 (Charcoal)
    │     │
    │     ├─ [Card / Elevated] #18181b (Deep Zinc)
    │     │     │
    │     │     └─ [Border / Divider] #27272a (Subtle Border, 1px)
    │     │
    │     └─ [Accent Focus] #e11d48 (Lens / Focal Red)
    │
    └─ [Text Hierarchy]
          ├─ Primary: #f4f4f5 (Crisp White)
          ├─ Secondary: #a1a1aa (Muted Gray)
          └─ Technical/EXIF: #71717a (Hardware Gray)
```

### 2.1. 컬러 팔레트 상세 규격

| 구분 | Hex 코드 | 용도 및 적용 컴포넌트 |
| :--- | :--- | :--- |
| **Canvas Background** | `#09090b` | 최하단 앱 캔버스 배경 (순수 블랙 대비 눈의 피로 경감) |
| **Surface (Sidebar/Header)** | `#121215` | 사이드바, 상단 글로벌 헤더, 모달 백드롭 |
| **Card / Container** | `#18181b` | 갤러리 썸네일 카드 플레이스홀더, 패널 컨테이너 |
| **Elevated / Hover** | `#27272a` | 마우스 호버 시 배경, 플로팅 툴팁, 팝오버 메뉴 |
| **Subtle Border** | `#27272a` / `rgba(255,255,255,0.08)` | 1px 섬세한 구분선, 카드 경계선 |
| **Active Border** | `#3f3f46` | 포커스된 인풋 창, 선택 대기 상태 |
| **Focal Accent (Red)** | `#e11d48` (Rose-600) | 검색창 포커스 링, 선택된 사진 테두리, 하트(즐겨찾기), 핵심 액션 |
| **AI Magic (Purple/Indigo)**| `#8b5cf6` (Violet-500) | SigLIP AI 검색 하이라이트, Gemma 비평 배지, K-NN 유사도 칩 |
| **Technical Amber (Warning)**| `#f59e0b` (Amber-500) | 인덱싱 진행률, 경고 알림, 뷰파인더 노출 경고 |
| **Success (Green)** | `#10b981` (Emerald-500) | 내보내기 완료, 인덱싱 완료 상태 |

---

## 🔤 3. 타이포그래피 시스템 (Typography)

사진 앱의 UI 텍스트는 **일반 인터페이스 텍스트**와 **카메라 촬영 데이터(EXIF)**의 성격이 명확히 다릅니다.

### 3.1. 폰트 패밀리 분리 (Dual-Font System)
* **인터페이스 폰트 (General UI):** `-apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif`
  * 현대적이고 중립적인 가독성 중심 산세리프.
* **장비/EXIF 폰트 (Technical Monospace):** `"SF Mono", "JetBrains Mono", "Roboto Mono", monospace`
  * 조리개(F1.4), 셔터스피드(1/500s), ISO(100), 화각(35mm), 파일 크기, 해시값 등 정밀한 수치 데이터에 적용하여 카메라 경통의 각인과 같은 기계적 감성을 부여.

### 3.2. 폰트 스케일 및 위계

| 스타일 | 크기 / Line-height | Weight | 적용 대상 |
| :--- | :--- | :--- | :--- |
| **Display Title** | 20px / 28px | 600 (SemiBold) | 뷰 타이틀, 대형 모달 헤더 |
| **Section Header** | 15px / 22px | 600 (SemiBold) | 사이드바 카테고리, 상세 패널 섹션 제목 |
| **Body (Default)** | 13px / 18px | 400 (Regular) | 검색 결과 캡션, 일반 UI 라벨, 설정 항목 |
| **Mono Technical** | 12px / 16px | 500 (Medium) | EXIF 칩(ISO, F, 셔터), 촬영 타임스탬프 |
| **Micro Caption** | 11px / 14px | 400 (Regular) | 보조 설명, 파일 포맷 배지(RAW/JPEG) |

---

## 📐 4. 레이아웃 및 여백 규칙 (Layout & Grid)

### 4.1. 사진 갤러리 그리드 (Edge-to-Edge Grid)
* **그리드 간격 (Gap):** `6px` ~ `8px`로 극도로 촘촘하게 배치.
  * 사진 사이의 불필요한 공백을 줄여 한 화면에 가능한 많은 썸네일을 시각적 노이즈 없이 노출.
* **코너 라운딩 (Border Radius):**
  * 포토 카드: `4px` ~ `6px` (너무 둥글지 않은 절제된 모서리)
  * 버튼 및 칩 배지: `6px`
  * 대형 모달 / 상세 패널: `12px`

### 4.2. 점진적 정보 공개 (Progressive Disclosure)
* **기본 갤러리 상태:** 오직 사진 이미지만 노출 (노이즈 제로).
* **마우스 호버 상태:** 
  * 하단에 얇은 그라데이션 오버레이(`linear-gradient(to top, rgba(0,0,0,0.7), transparent)`)와 함께 초소형 EXIF 뱃지(`F1.8 · 1/250 · 35mm`)가 페이드인.
  * 우측 상단 즐겨찾기(하트) 및 좌측 상단 다중 선택 체크박스 노출.
* **클릭/선택 상태:** 우측 슬라이드 패널(`DetailPanel`) 또는 전체화면 뷰어(`FullscreenViewer`)에서 AI 비평 및 풀 메타데이터 전개.

---

## 🔍 5. 주요 핵심 컴포넌트별 상세 스펙

### 5.1. 자연어 검색바 (The Command Bar)
* **위치:** 메인 갤러리 상단 중앙 플로팅 또는 고정 헤더.
* **디자인:**
  * 배경: `rgba(24, 24, 27, 0.85)` + `backdrop-filter: blur(16px)` (글래스모피즘).
  * 테두리: `1px solid rgba(63, 63, 70, 0.5)`.
  * 포커스 시: 은은한 앰버 또는 로즈 레드 링(`box-shadow: 0 0 0 1px #e11d48`).
  * 우측 숏컷 배지: `⌘K` 또는 `Search with AI...` 플레이스홀더.
  * 하이브리드 필터 토글: 카메라 바디, 렌즈 모델 드롭다운을 컴팩트한 모노톤 칩으로 제공.

### 5.2. EXIF 메타데이터 칩 (Hardware HUD Badges)
* **디자인:**
  * 배경: `rgba(0, 0, 0, 0.6)`
  * 텍스트: `SF Mono`, `#a1a1aa`, `11px`
  * 포맷:
    * `[ ISO 400 ]`
    * `[ 35mm ]` (35mm 환산 모드 토글 가능)
    * `[ ƒ/1.4 ]`
    * `[ 1/1000s ]`
    * `[ SONY α7 IV ]`
  * RAW 파일 표기: 선명한 오렌지/레드 태그 `RAW` (ARW, CR3 등).

### 5.3. AI 비평 & 캡션 패널 (Editorial Critique Card)
* **목적:** Gemma 4 VLM / UniPercept가 분석한 사진의 예술적·기술적 평론 제공.
* **디자인:**
  * 딱딱한 시스템 로그 형식이 아닌, 전시 갤러리의 **큐레이터 평론 카드** 스타일 적용.
  * 구도(Composition), 조명(Lighting), 색감(Color Story) 3대 요소를 얇은 프로그레스 바나 레이더 차트 형태로 시각화.
  * 사용자가 직접 AI 캡션을 인라인으로 수정할 수 있는 정갈한 에디터 인터페이스.

---

## ⚡ 6. 모션 및 인터랙션 가이드 (Motion & Micro-interactions)

데스크탑 네이티브 앱다운 즉각적인 반응성과 묵직한 조작감을 지향합니다.

1. **포토 카드 호버:** 
   * `scale: 1.015` 내외의 극히 미세한 확대 (과도한 팝업 애니메이션 지양).
   * 반응 속도: `150ms ease-out`.
2. **모달 / 패널 전환:**
   * 슬라이드 인: `Framer Motion`의 댐핑 스프링 (`damping: 25, stiffness: 300`).
3. **키보드 네비게이션:**
   * 방향키(`Arrow Keys`): 그리드 내 즉시 초점 이동.
   * `Space`: 빠른 미리보기(Quick Look).
   * `Enter`: 상세 뷰어 열기.
   * `Esc`: 모달/패널 닫기.

---

## 💻 7. 구현 코드 스니펫 (CSS Variables & Tailwind Config)

프론트엔드 스타일 통합 시 참고할 수 있는 기본 CSS 변수 명세입니다:

```css
/* App.css 또는 테마 정의 파일 */
:root {
  /* Canvas & Surface */
  --bg-canvas: #09090b;
  --bg-surface: #121215;
  --bg-card: #18181b;
  --bg-elevated: #27272a;

  /* Borders */
  --border-subtle: #27272a;
  --border-active: #3f3f46;
  --border-focus: #e11d48;

  /* Accents */
  --accent-focal: #e11d48;     /* Leica Red */
  --accent-ai: #8b5cf6;        /* Gemma / SigLIP Magic */
  --accent-amber: #f59e0b;     /* Warning / Film Amber */
  --accent-emerald: #10b981;   /* Success */

  /* Text */
  --text-primary: #f4f4f5;
  --text-secondary: #a1a1aa;
  --text-muted: #71717a;

  /* Fonts */
  --font-ui: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif;
  --font-mono: "SF Mono", "JetBrains Mono", Menlo, monospace;
}
```

---

## ✅ 요약: Focal Node가 추구하는 시각적 인상

> **"소란스럽지 않다. 차분하고 견고하다.  
> 사진을 띄우는 순간 UI는 사라지고, 0.1초 만에 원하는 사진을 찾아내는 정밀한 광학 장비가 된다."**
