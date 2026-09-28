# SITE_CONFIG_SCHEMA_V1

고객 데이터의 규격입니다. **관리자 웹이 만들어지기 전까지 이 구조가 호환성 기준입니다.**

칸을 **늘리는 것은 됩니다.** 있는 칸의 이름을 바꾸거나 지우거나 다른 뜻으로 쓰면
이미 만든 고객 주문서가 전부 깨집니다. 그때는 `V2` 를 새로 내고 둘을 함께 지원해야 합니다.

검사는 `factory/schema.py` 가 합니다.

```bash
python -m factory.cli validate 주문서.json     # 오류 0 이면 종료코드 0
```

`build` 는 파일에서 주문서를 읽을 때 이 검사를 자동으로 돌립니다.
**오류가 있으면 짓지 않고**, 경고는 짓되 `build_report.json` 과 납품 메모에 남깁니다.

---

## 최상단 칸

| 칸 | 모양 | 필수 | 하는 일 |
| --- | --- | --- | --- |
| `template` | 글 | – | 쓸 템플릿 id (`master-interior-01`). 없으면 공장이 고릅니다 |
| `slug` | 글 | – | 산출물 폴더 이름 |
| `company` | 사전 | **✔** | 업체 정보 |
| `hero` | 사전 또는 글 | – | 첫 화면 |
| `strengths` | 목록 | – | 강점 숫자 |
| `services` | 목록 | – | 시공 범위 |
| `about` | 사전 또는 글 | – | 소개 |
| `projects` | 목록 | – | 시공 사례 |
| `process` | 목록 | – | 진행 절차 |
| `reviews` | 목록 | – | 후기 |
| `faq` | 목록 | – | 자주 묻는 질문 |
| `contact` | 사전 | – | 연락처 |
| `site` | 사전 | – | 쪽수·도메인·기능 |
| `theme` | 사전 또는 글 | – | 색 버전 |
| `layout` | 사전 | – | 배치 갈래 |
| `seo` | 사전 | – | 검색·공유 |
| `gallery` | 목록 | – | 일반 사진 (마스터에서는 잘 안 씁니다) |
| `reference` | 사전 또는 글 | – | 참고 사이트 |
| `brand` | 사전 | – | 로고·색 직접 지정 |

`_` 로 시작하는 칸(`_주의` 등)은 메모로 보고 무시합니다.
모르는 칸이 오면 **경고**하고 가장 비슷한 이름을 알려 줍니다(`projcets` → `projects`).

---

## 칸 안쪽

### company (필수)

| 칸 | 필수 | 비고 |
| --- | --- | --- |
| `name` | **✔** | 상호. **이것만은 없으면 짓지 않습니다** |
| `industry` | 권장 | 없으면 템플릿·말씨·기본 색이 무뎌집니다 |
| `tagline` · `description` · `founded` · `owner` | – | |

### contact

| 칸 | 필수 | 비고 |
| --- | --- | --- |
| `phone` | 권장 | 없으면 전화 버튼과 모바일 하단 바가 빕니다 |
| `address` | 권장 | 지역 검색·지도에 씁니다 |
| `kakao` · `email` · `hours` · `map_url` · `links{}` | – | |
| `areas[]` / `서비스지역` | – | **2026-09-28 추가.** 찾아가는 업종(청소·방역·수리)의 "어디까지 갑니까". 비면 지역 섹션이 통째로 빠집니다 |
| `area_note` / `지역안내` | – | **2026-09-28 추가.** "인근 지역은 상담 후 방문합니다" 같은 한 줄 |

### hero

`headline` · `subline` · `image` · `badges[]` · `cta_label` · `cta_href` · `sub_cta_*`
글 한 줄만 적으면 `headline` 으로 봅니다. 없으면 `company.tagline` → 상호 순으로 대신합니다.

### strengths[] · services[] · process[]

각 항목에 **`name`** 이 있어야 합니다(`이름`·`title`·`제목` 도 됩니다).
그 밖에 `summary`/`설명`, `number`/`숫자`, `unit`/`단위`, `price`/`가격`,
`image`/`사진`, `bullets`/`항목`, `duration`/`기간`.

### projects[]

**`name` 필수.** `category`/`분류`, `location`/`위치`, `size`/`평형`, `year`/`연도`,
`summary`/`설명`, `image`/`사진`, `images[]`/`추가사진`.

**2026-09-28 추가 — `before`/`작업전` 과 `after`/`작업후`.**
둘 다 있는 사례는 **작업 전·후 비교**로 나가고, 보통 사례 목록에서는 빠집니다
(같은 사진을 두 번 보여 주지 않습니다). 한 장만 있으면 그 한 장만 나가고 납품메모에
모자란 쪽을 적습니다. 새 최상단 칸을 만들지 않으려고 사례 한 건 안에 두었습니다 —
관리자 웹에서도 "사례" 하나만 편집하면 되게 하기 위해서입니다.

사진(`image`·`images`·`before`·`after`)이 하나도 없으면 **경고**합니다 —
사례 사진은 홈페이지에서 가장 값이 나가는 자리입니다.

### reviews[]

**`quote`(`내용`) 필수.** `name`/`이름`, `project`/`시공`, `rating`/`별점`(0~5), `role`.

### faq[]

**`question`(`질문`)과 `answer`(`답`) 둘 다 필수.**

### site

`pages`(1 또는 5) · `domain` · `goals[]` · `features[]` · `primary_cta` · `template`

### theme

글 한 줄이면 프리셋 이름: `charcoal` · `beige` · `black` · `green` ·
`sky`(네이비·프레시) · `mist`(그레이·미스트).
뒤의 둘은 2026-09-28 에 늘렸습니다 — 청소·홈케어처럼 밝고 단정해야 하는 업종용입니다.
사전이면 `preset` 위에 `primary` · `accent` · `background` · `surface` · `mode` · `radius` · `font` 을 덮습니다.
모르는 이름은 **경고**하고 기본값으로 갑니다.

### layout

| 칸 | 값 | 기본 |
| --- | --- | --- |
| `hero` | `left` · `center` | `left` |
| `projects` | `mosaic`(첫 칸 크게) · `grid`(고른 격자) | `mosaic` |

### seo

`title`(70자 이하 권장) · `description`(160자 이하 권장) · `og_title` · `og_description` ·
`og_image` · `favicon` · `region`/`지역명` · `keywords[]`

---

## 한글 키

모든 칸은 한글 이름으로도 받습니다. 영업 담당자가 받아 적은 말을 그대로 옮기기 위해서입니다.

```
상호 업종 한줄소개 소개 대표 설립 · 전화 카카오톡 주소 영업시간 지도
강점 시공사례 절차 후기 자주묻는질문 · 분류 위치 평형 연도 사진 추가사진 별점 기간
```

별칭 표는 `factory/intake.py` 의 `_ALIASES` 에 있습니다. 규격 이름과 한글 이름 중
아무것이나 쓰면 되고, 섞어 써도 됩니다.

---

## 규격을 바꿔야 할 때

1. **칸을 더한다** — 그냥 더하면 됩니다. 옛 주문서는 그대로 돕니다.
2. **뜻을 바꾼다 / 지운다** — `V1` 을 건드리지 말고 `SITE_CONFIG_SCHEMA_V2` 를 만드십시오.
   `schema.py` 의 `SCHEMA_VERSION` 과 이 문서를 함께 올립니다.
3. 관리자 웹이 생기면 이 문서가 **폼의 명세서**가 됩니다. 칸 하나가 입력 칸 하나입니다.
