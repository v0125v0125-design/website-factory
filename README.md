# website-factory

원페이지·5페이지 홈페이지를 **템플릿으로 찍어 파는** 공장입니다.

고객 정보 한 장(주문서)과 "이런 느낌으로" 라며 받은 레퍼런스 주소를 넣으면,
가장 맞는 템플릿을 고르고 · 레퍼런스에서 읽어 낸 색과 서체를 입혀 ·
그대로 올릴 수 있는 정적 사이트 한 벌을 내놓습니다.

```
주문서(JSON/YAML) ─┐
                   ├─→ 스타일 정하기 ─→ 템플릿 고르기 ─→ 원고 채우기 ─→ 파일 쓰기 ─→ out/<고객>/
레퍼런스(주소/파일) ─┘         ↑                 ↑              ↑
                      색·서체·모서리·여백    쪽수·업종·기능    주문서에 있는 사실만
```

독립 저장소입니다. 파이썬 3.11 과 Jinja2 말고는 필요한 것이 없고,
산출물은 빌드 과정이 없는 정적 파일 한 벌입니다.

---

## 빠른 시작

```bash
pip install -r requirements.txt

python -m factory.cli templates                                  # 찍을 수 있는 템플릿
python -m factory.cli plan  examples/cafe-onepage.json           # 무엇을 지을지만 본다
python -m factory.cli build examples/cafe-onepage.json -o out/bloom
python -m factory.cli serve out/bloom                            # http://127.0.0.1:8765

# 인테리어 마스터 (양산형) — 가상 고객 3곳을 한 번에
python -m factory.cli validate examples/customers/a-gonggan.json   # 규격 검사
python -m factory.cli batch    examples/customers -o out --offline
```

`out/bloom` 이 그대로 상품입니다. 빌드 과정도, 서버도 필요 없습니다.

---

다른 컴퓨터에서 이어서 하실 때와, 무엇을 왜 그렇게 정했는지는
**`문서/작업기록.md`** 를 보십시오.

## 명령

| 명령 | 하는 일 |
| --- | --- |
| `templates` | 템플릿 목록과 각 장의 섹션 구성 |
| `probe <주소\|파일>` | 레퍼런스에서 무엇이 읽히는지만 본다 |
| `validate <주문서>` | SITE_CONFIG_SCHEMA_V1 에 맞는지 본다 (파일을 쓰지 않음) |
| `plan <주문서>` | 고른 템플릿·스타일·근거를 보여 주고 끝 (파일을 쓰지 않음) |
| `build <주문서> -o <폴더>` | 실제로 짓는다 |
| `batch <주문서폴더> -o <폴더>` | 여러 건을 한 번에 — 공장 모드 |
| `serve <폴더>` | 지은 것을 브라우저로 확인 |

자주 쓰는 깃발:

```
--offline            레퍼런스를 가져오지 않는다 (네트워크가 막힌 곳에서)
--template <id>      템플릿을 사람이 직접 고른다
--form-action <주소> 문의폼을 받을 주소 (Formspree 등)
--zip                다 지으면 zip 으로 묶는다
--clean              산출물 폴더를 먼저 비운다
--no-optimize        사진을 줄이지 않고 원본 그대로 쓴다
```

---

## 주문서 쓰는 법

`.json` 과 `.yaml` 둘 다 받습니다. **한글 키를 그대로 써도 됩니다** —
영업 담당자가 받아 적은 말을 옮기기 쉬우라고 별칭을 열어 두었습니다.
`examples/salon-onepage.yaml` 이 한글 키로 쓴 본보기입니다.

```yaml
상호: 스튜디오 온          # business.name  — 이것만은 반드시 있어야 합니다
업종: 미용실               # business.industry — cafe/clinic/salon… 으로 자동 분류
한줄소개: 머리를 자르는 데 한 시간을 씁니다
소개: |
  1인 살롱입니다. 하루에 여섯 분만 받습니다.

연락처:                    # contact
  전화: 02-6402-1180
  주소: 서울 마포구 망원로 8길 17, 1층
  영업시간: 화–토 11:00–20:00
  링크: { 인스타그램: https://instagram.com/... }

홈페이지:                  # site
  페이지: 1                # 1 또는 5
  도메인: studio-on.kr
  목표: [예약, 브랜딩]      # reservation / inquiry / brand / sell / visit / recruit
  기능: [지도, 갤러리, 요금, 예약]   # map / gallery / form / pricing / menu / faq …

브랜드:                    # brand
  주색: "#8e5572"          # 지정하면 레퍼런스보다 이것이 이깁니다
  분위기: [부드러운, 고급]   # soft / luxury / clean / warm / bold …
  서체: sans               # sans | serif

레퍼런스: https://example.com      # 또는 { html_path: 로컬파일.html }

시술:                      # items — 메뉴/서비스/진료/요금 무엇이든 여기로
  - 이름: 커트
    설명: 상담 15분을 포함합니다
    가격: "45,000원"
갤러리: [{ src: photos/1.jpg, alt: 내부 }]
후기:   [{ 내용: "…", 이름: 윤○○ }]
자주묻는질문: [{ 질문: "…", 답: "…" }]
```

비운 칸은 비운 대로 갑니다. 없는 사실을 채워 넣지 않습니다(아래 참조).

---

## 템플릿

| id | 쪽수 | 쓰는 곳 |
| --- | --- | --- |
| `onepage-classic` | 1 | 동네 가게·1인 사업자 |
| `five-pages-corp` | 5 | 설명할 것이 많은 병원·법무·학원 |
| `master-interior-01` | 1 | **인테리어·리모델링·시공 업체 양산형 마스터** — [설계 문서](문서/MASTER_INTERIOR_01.md) |

`master-interior-01` 은 고객 데이터만 갈아 끼워 반복 판매하도록 만든 마스터입니다.
강점 숫자 띠 · 시공 사례 격자(크게 보기) · 진행 절차 · 모바일 하단 문의 바 ·
데스크톱 오른쪽 상담 레일을 갖췄고, 색 버전을 `theme` 한 줄로,
배치 갈래를 `layout` 한 줄로 바꿉니다.

- 색: `charcoal` · `beige` · `black` · `green`
- 배치: 히어로 `left`/`center`, 사례 `mosaic`/`grid`
- 규격: [SITE_CONFIG_SCHEMA_V1](문서/SITE_CONFIG_SCHEMA_V1.md) — 관리자 웹 전까지의 호환 기준
- 사진: 역할별로 줄이고 WebP 로 바꿉니다 (히어로 1920 · 사례 1600 · 카드 900 …)

## 스타일은 이 순서로 정해집니다

0. **테마** — `theme: charcoal` 또는 `theme: { preset, primary, accent, ... }`
1. **주문서에 못 박은 값** — `브랜드.주색`, `모드`, `서체` (테마보다 앞섭니다)
2. **레퍼런스에서 실제로 읽어 낸 값** — `meta theme-color`, 가장 많이 쓰인 색,
   `body` 배경, 구글 폰트 링크, 가장 잦은 `border-radius`, 가장 큰 블록 여백
3. **업종 기본값** — `factory/theming.py` 의 `PRESETS`

앞의 것이 있으면 뒤의 것을 쓰지 않습니다. 무엇을 왜 썼는지는 모두 남깁니다.

```
왜 이 스타일인가
  주색: 레퍼런스 theme-color #8a5a2b
  강조색: 레퍼런스 보조색 #c9a227
  바탕색: 레퍼런스 #fffaf3 를 그대로 씀
  모서리: 레퍼런스 모서리 18px
  간격: 레퍼런스 블록 여백 140px (넉넉함)
```

레퍼런스에서 **가져오는 것은 치수뿐**입니다. 문장·이미지·마크업은 가져오지 않습니다.

색은 뽑은 뒤 반드시 다시 잽니다. 본문 대비 7:1, 흐린 글씨와 버튼 글자 4.5:1 을
넘기도록 밝기를 조정하고, 결과를 `build_report.json` 과 납품 메모에 적습니다.
중간 밝기 파랑처럼 흰 글자도 검은 글자도 안 되는 색은 밝기를 옮겨 통과시킵니다.

---

## 지어내지 않습니다

이 공장이 지키는 한 가지 규칙입니다.

- 고객이 적어 주지 않은 사실(“20년 경력”, “직접 볶은 원두”)은 쓰지 않습니다.
- 재료가 없는 섹션은 **뺍니다**. 사진이 없으면 갤러리 장 자체를 내지 않고
  메뉴에서도 지웁니다. 유도 버튼만 남은 빈 페이지가 팔려 나가는 것보다 낫습니다.
- 사람이 꼭 채워야 하는 자리는 `[한 줄 소개]` 처럼 눈에 띄게 남기고,
  `납품메모.md` 의 체크리스트에 올립니다.
- 5쪽을 주문했는데 4쪽만 나왔다면 보고서에 그렇게 적습니다.

머리말·버튼 글자처럼 사실 주장이 아닌 말은 업종에 맞춰 바꿉니다
(치과의 “서비스” 는 “진료 과목”, 카페의 “서비스” 는 “메뉴”).

---

## 산출물

```
out/bloom/
├── index.html            (5쪽형이면 about/services/gallery/contact.html 까지)
├── assets/
│   ├── styles.css        토큰으로 찍은 스타일시트
│   ├── favicon.svg        주색과 머리글자로 만든 아이콘
│   └── img/              주문서가 가리킨 사진을 복사해 온 것
├── sitemap.xml · robots.txt
├── netlify.toml · vercel.json · CNAME · .nojekyll
├── build_report.json     기계가 읽는 근거 (템플릿 점수·스타일 근거·대비·빠진 것)
└── 납품메모.md            사람이 읽는 인수인계서
```

올리는 법은 세 가지 중 아무것이나 됩니다.

```bash
netlify deploy --dir=out/bloom --prod
vercel --prod out/bloom
# 또는 일반 웹호스팅에 FTP 로 폴더 내용을 그대로
```

---

## 템플릿 추가하기

`templates/<새이름>/` 을 만들고 `template.json` 과 페이지 파일을 둡니다.
공용 조각은 `templates/_shared/` 에서 자동으로 찾아 쓰므로,
대개 `index.html` 한 줄과 설명서만 있으면 됩니다.

```
templates/my-template/
├── template.json          id·쪽수·업종·분위기·기능·페이지별 섹션
├── index.html             {% extends "base.html" %}
└── assets/styles.css.j2   {% include "assets/_core.css.j2" %} + 이 템플릿만의 손질
```

`template.json` 의 `industries` · `moods` · `features` · `goals` 가 그대로
점수표가 됩니다 (`factory/matching.py`). 쪽수가 가장 무겁고(±50/34),
그다음이 업종(18), 기능 수용률(22), 분위기(최대 18), 목표(최대 12) 순입니다.

섹션 종류는 `hero · about · services · menu · pricing · gallery ·
testimonials · faq · process · contact · cta` 입니다.
새 종류를 만들려면 `templates/_shared/partials/` 에 조각을 넣고
`factory/render.py` 의 `SECTION_PARTIALS` 와
`factory/content.py` 의 `CopyEngine.build_section` 에 등록합니다.

---

## 구조

| 파일 | 맡은 일 |
| --- | --- |
| `factory/intake.py` | 주문서를 읽어 `Brief` 로. 한글 키·업종·분위기 말을 하나로 모은다 |
| `factory/reference.py` | 레퍼런스에서 **사실만** 긁는다. 고르지 않는다 |
| `factory/theming.py` | 무엇을 쓸지 정하고 CSS 토큰 한 벌을 만든다 |
| `factory/colorkit.py` | 색 계산과 대비 검사 (바깥 의존성 없음) |
| `factory/catalog.py` | `templates/` 의 설명서를 읽고 검사한다 |
| `factory/matching.py` | 템플릿 점수와 그 이유 |
| `factory/content.py` | 주문서의 사실로 섹션을 채운다. 없으면 자리를 남긴다 |
| `factory/render.py` | Jinja 로 HTML·CSS·sitemap·JSON-LD 를 쓴다 |
| `factory/package.py` | 호스팅 설정과 zip |
| `factory/pipeline.py` | 위 순서를 엮고 보고서를 쓴다 |
| `factory/cli.py` | 명령줄 |

---

## 시험

```bash
pip install -r requirements-dev.txt
python -m pytest -q          # 175개 (브라우저 검사 16개 포함)
```

지어진 결과물을 실제로 뜯어봅니다 — 템플릿 문법이 새어 나왔는지,
링크가 진짜 파일을 가리키는지, JSON-LD 가 파싱되는지, 모든 업종 기본값이
대비 기준을 넘는지.

---

## 앞으로

- 관리자 웹 — 폼으로 주문서를 채우고 미리보기를 띄우는 곳 (구조는 이미 맞춰 두었습니다)
- 템플릿 늘리기 (요식업 사진 중심형, 전문직 문서 중심형)
- 문의폼 수신함 (Formspree 연동은 `--form-action` 으로 이미 가능)
- 레퍼런스 분석에 스크린샷 기반 판단 더하기 (지금은 CSS 만 읽는다)
- 원고를 사람이 고쳐 넣는 자리를 `content.py` 의 `CopyEngine` 에 열어 두었음
