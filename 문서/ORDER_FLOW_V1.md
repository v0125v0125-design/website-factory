# ORDER FLOW V1

고객이 **신청을 남기고**, 제작이 정해지면 **자료를 보내는** 두 단계 흐름입니다.
회원가입·로그인·결제·관리자 웹은 없습니다. 지금 목적은 하나입니다 —
**실제 신청을 받아볼 수 있는 가장 단순한 시스템.**

| | 주소 |
| --- | --- |
| 판매 홈페이지 | <https://v0125v0125-design.github.io/website-factory/store/> |
| 제작 상담 신청 | <https://v0125v0125-design.github.io/website-factory/store/order/> |
| 제작 자료 입력 | <https://v0125v0125-design.github.io/website-factory/store/materials/> |
| 개인정보 안내 | <https://v0125v0125-design.github.io/website-factory/store/privacy/> |

---

## 1. 전체 흐름

```
당근 · 네이버 · 소개 · 검색
        ↓
판매 홈페이지  /store/
        ↓  샘플을 열어 본다
[이 디자인으로 제작하기]
        ↓  product 와 sample 을 주소에 실어 보낸다
제작 상담 신청  /store/order/?product=START&sample=INTERIOR_01
        ↓  실제 POST
접수                                    ← 여기까지가 STEP 1 (짧게)
        ↓
운영자가 확인하고 연락 · 가능 여부와 일정 · 금액
        ↓  진행하기로 하면
제작 자료 입력 링크 전달  /store/materials/
        ↓  실제 POST (사진은 공유 링크 또는 첨부)
자료 접수                                ← 여기까지가 STEP 2 (충분히)
        ↓
siteConfig 작성 → 사진 배치 → 미리보기 생성
        ↓
고객 확인 → 수정 → 도메인 연결 → 납품
```

**두 폼을 나눈 이유.** 첫 화면에서 로고·사진·서비스·강점을 다 요구하면
광고에서 들어온 사람은 대부분 닫습니다. STEP 1 은 필수 네 칸(업체명·업종·
담당자·연락처)이 전부이고, 나머지는 제작이 정해진 뒤에 받습니다.

---

## 2. ORDER FORM — 제작 상담 신청

`/store/order/` · 템플릿 `storefront/templates/order.html`

| 받는 것 | |
| --- | --- |
| 필수 | 선택 상품 · 선택 디자인 · 업체명 · 업종 · 담당자명 · 연락처 |
| 선택 | 이메일 · 도메인 보유 여부 · 기존 홈페이지 · 간단 요청사항 |
| PREMIUM 일 때만 | 예상 페이지 수 · 필요한 기능 · 참고 사이트 · 예상 예산 · 디자인 방향 |

### 주소로 넘어오는 값

| 파라미터 | 값 | 어디서 |
| --- | --- | --- |
| `product` | `START` · `BUSINESS` · `PREMIUM` | 가격표 버튼, 샘플 카드 |
| `sample` | `INTERIOR_01` · `CLEANING_01` · `COMPANY_01` | 샘플 카드 (밑줄은 공백으로 바뀝니다) |
| `mode` | `recommend` | "아직 고르지 못했습니다" 갈래 |

`product=PREMIUM` 이면 추가 칸이 자동으로 열립니다.
`mode=recommend` 면 같은 폼이 **업체명·업종·연락처·기존 홈페이지·분위기·요청**만
남기고 접힙니다. 이때 `sample` 은 `undecided` 로 기록됩니다.

직접 들어온 손님은 상품과 디자인을 화면에서 고르면 됩니다.

### 판매 페이지의 모든 CTA

| 버튼 | 가는 곳 |
| --- | --- |
| START로 제작하기 | `order/?product=START` |
| BUSINESS로 제작하기 | `order/?product=BUSINESS` |
| PREMIUM 상담 신청 | `order/?product=PREMIUM` |
| 이 디자인으로 제작하기 (샘플 카드) | `order/?product=<카드의 상품>&sample=<카드 제목>` |
| 아직 고르지 못했습니다 | `order/?mode=recommend` |
| 머리·마감·푸터의 제작 신청 | `order/` |

샘플 카드의 링크는 **자바스크립트가 카드 제목을 읽어** 붙입니다. 새 샘플을
`storefront.json` 에 추가하면 주문 화면의 선택지와 카드 링크가 함께 늘어납니다.
손으로 적을 곳은 없습니다 (`test_a_new_sample_shows_up_without_touching_the_form`).

---

## 3. MATERIAL FORM — 제작 자료 입력

`/store/materials/` · 템플릿 `storefront/templates/materials.html`

광고 고객이 바로 쓰는 화면이 아닙니다. 상담을 마치고 **"제작 진행하겠습니다.
아래 자료입력 링크를 작성해 주세요"** 라고 보낼 때 쓰는 주소입니다.

아홉 칸으로 나뉘어 있고 왼쪽에 현재 위치가 보입니다.

```
1 접수 확인   업체명 · 담당자 · 연락처 · 접수번호(선택) · 제작할 디자인
2 회사 정보   상호 · 영문명 · 대표 · 대표번호 · 추가 연락처 · 이메일 · 영업시간 ·
              주소 · 카카오톡 · 인스타그램 · 블로그 · 기타 SNS
3 브랜드      로고 유무 · 대표 색상 · 참고 사이트 · 원하는 분위기
4 대표 문구   메인 제목 · 서브 문구 · 업체 소개  (또는 "대신 써 주세요")
5 서비스·강점 줄을 늘리고 줄이는 목록. 서비스 최소 1개
6 업종 자료   1번에서 고른 디자인에 따라 다른 칸이 나타납니다
7 사진        업종별 필요 목록 + 공유 링크(또는 첨부) + 사진 상황
8 후기·질문·검색  받은 후기만 · FAQ · 지역/서비스/키워드
9 보내기      추가 요청사항 · 자료 이용 동의
```

### 업종별로 달라지는 칸

한 파일 안에서 **조건부 구역**으로 갈립니다. 업종마다 폼을 따로 만들지 않습니다.

| 디자인 | 추가 칸 | 사례 줄 |
| --- | --- | --- |
| INTERIOR 01 | 시공 분야 · 시공 지역 | 프로젝트명 · 지역 · 평형 · 설명 |
| CLEANING 01 | 서비스 지역 · 청소 종류 | 작업명 · 지역 · 평형 · 설명 |
| COMPANY 01 | 사업 영역 · 대응 지역 · 회사 연혁 · 인증·보유 장비 | 프로젝트명 · 적용 산업 · 수행 범위 · 설명 |

### 사진 안내

고른 디자인에 맞춰 필요한 사진 목록이 바뀝니다.

| | |
| --- | --- |
| INTERIOR 01 | 대표 1 · 시공 분야 4 · 시공 사례 10장 이상 · 업체 1~2 |
| CLEANING 01 | 대표 1 · 서비스 4 · **작업 전·후 3~5세트** · 작업 사례 6~10 |
| COMPANY 01 | 회사/공장 1 · 사업 영역 3~5 · 제품/설비 4~6 · 수행 사례 6장 이상 |

"아직 없습니다 — 어떤 사진이 필요한지 알려 주세요" 를 고를 수 있습니다.

### 임시 저장

작성 중인 내용은 **이 브라우저의 localStorage 에만** 자동 저장됩니다
(`wf-material-draft-v1`). 창을 닫았다 열어도 이어서 쓸 수 있고, 제출에 성공하면
지워집니다. 화면 위의 "저장된 내용 지우기" 로 직접 비울 수도 있습니다.
서버로 가지 않으므로 다른 기기에서는 이어지지 않습니다.

---

## 4. 접수 창구 (submission provider)

특정 업체에 코드가 묶이지 않도록 **어댑터 한 겹**을 두었습니다.
`storefront/templates/submit.js.j2` 가 그 어댑터이고, 설정은 여기 한 곳입니다.

```jsonc
// storefront/storefront.json
"submission": {
  "provider": "",      // "formspree" | "post" | "" (없음)
  "endpoint": "",      // 받는 주소
  "successUrl": ""     // 성공 후 보낼 주소 (비우면 같은 화면에 접수 안내)
}
```

### 고르는 법

| provider | 보내는 꼴 | 어울리는 곳 |
| --- | --- | --- |
| `formspree` | `multipart/form-data` — 사람이 읽는 평평한 칸 + `payload` 에 JSON 전문 | 이메일로 바로 받고 싶을 때. 파일 첨부는 유료 요금제 |
| `post` | `text/plain` 으로 보낸 JSON 한 덩어리 | 구글 앱스스크립트로 시트에 쌓고 싶을 때 |
| `""` | 보내지 않음 | 아직 정하지 않은 지금 상태 |

`post` 가 `text/plain` 을 쓰는 이유는 사전 요청(preflight)을 만들지 않기
위해서입니다. 앱스스크립트 웹앱이 그대로 받습니다.

### Formspree 로 켜는 법

1. <https://formspree.io> 에서 폼을 만들고 `https://formspree.io/f/xxxxxxx` 를 받습니다.
2. `storefront.json` 에 적습니다.
   ```json
   "submission": { "provider": "formspree", "endpoint": "https://formspree.io/f/xxxxxxx", "successUrl": "" }
   ```
3. `python tools/build_previews.py _site` 로 다시 짓고 올립니다.
4. **받는 곳** — Formspree 대시보드와 가입 메일로 옵니다.

### 구글 시트로 켜는 법

1. 새 스프레드시트 → 확장 프로그램 → Apps Script.
2. 아래를 붙여 넣고 저장합니다.
   ```javascript
   function doPost(e) {
     const data = JSON.parse(e.postData.contents);
     const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
     sheet.appendRow([new Date(), data.kind, JSON.stringify(data)]);
     return ContentService.createTextOutput(JSON.stringify({ok: true}))
       .setMimeType(ContentService.MimeType.JSON);
   }
   ```
3. 배포 → 새 배포 → 웹 앱 → 실행 계정 **나**, 액세스 **모든 사용자** →
   `https://script.google.com/macros/s/…/exec` 를 받습니다.
4. `"provider": "post"`, `"endpoint"` 에 그 주소를 적고 다시 짓습니다.
5. **받는 곳** — 그 스프레드시트.

### 설정이 없으면 (지금 상태)

- 제출 버튼이 **눌리지 않습니다**(`disabled`).
- "지금은 온라인 접수를 준비하는 중입니다" 와 설정된 연락처를 보여 줍니다.
- 개발자용 말(provider·endpoint·formspree)은 화면에 **한 글자도 나오지 않습니다**.
- 가짜 "접수 완료" 는 어떤 경우에도 뜨지 않습니다.

`test_a_closed_shop_locks_the_button_and_says_why` 와
`test_developer_words_never_reach_the_customer` 가 이걸 지킵니다.

---

## 5. 파일(사진) 받는 법

```jsonc
"upload": { "mode": "link", "maxMB": 25 }
```

| mode | 화면 | 언제 |
| --- | --- | --- |
| `link` (기본) | "사진 공유 링크" 한 칸 — 구글 드라이브·네이버 MYBOX 주소 | **설정 없이 바로 됩니다.** 사진은 파일이 커서 링크가 더 확실합니다 |
| `attach` | 파일 선택 칸 (여러 장) | 받는 곳이 파일 업로드를 지원할 때만 |

`attach` 는 어댑터가 `formspree` 일 때 multipart 로 함께 보냅니다.
자체 백엔드를 새로 만들지 않았습니다.

---

## 6. 들어오는 데이터 모양

두 폼 모두 아래 꼴의 JSON 한 덩어리를 보냅니다. 앞으로 만들 관리자 웹은
이것만 읽으면 됩니다.

```jsonc
{
  "kind": "order" | "recommend" | "material",
  "version": "ORDER_FLOW_V1",
  "submittedAt": "2026-09-29T…Z",
  "source": { "page": "…", "referrer": "…", "product": "START", "sample": "INTERIOR 01" },
  "lead":    { "company", "industry", "name", "contact", "email", "domain", "site", "message" },
  "premium": { "pages", "features": [], "reference", "budget", "direction" },  // order 만
  "company": { "name", "nameEn", "owner", "phone", "email", "hours", "address", … },  // material 만
  "brand":   { "logo", "color", "moods": [], "reference" },
  "copy":    { "help", "headline", "subline", "about" },
  "services":  [{ "name", "note" }],
  "strengths": [{ "name", "note" }],
  "projects":  [{ "title", "place", "size", "note" }],
  "reviews":   [{ "name", "note" }],
  "faq":       [{ "name", "note" }],
  "industry":  { "areas", "region", "kinds", "history", "credentials" },
  "photos":    { "link", "state", "note" },
  "seo":       { "region", "service", "keywords" },
  "notes": "",
  "consent": { "privacy": true, "at": "…" }
}
```

`formspree` 일 때는 여기에 더해 사람이 읽을 평평한 칸(업체명·연락처·선택 상품 …)을
함께 보냅니다. 대시보드와 메일에서 바로 읽으라고 둔 것입니다.

### siteConfig 로 가는 길

고객이 적는 원본 자료와 최종 `SITE_CONFIG_SCHEMA_V1` 을 억지로 같게 만들지
않았습니다. 중간 변환이 한 단계 있습니다. 다만 이름은 최대한 맞춰 두었습니다.

| 제출 데이터 | siteConfig |
| --- | --- |
| `company.*` | `company` · `contact` |
| `copy.headline` · `subline` | `hero.headline` · `hero.subline` |
| `copy.about` | `about.문단` |
| `services[]` | `services[]` (`name` · `설명`) |
| `strengths[]` | `strengths[]` |
| `projects[]` | `projects[]` (`name` · `위치` · `평형` · `설명`) |
| `industry.history` / `credentials` | `about.연혁` / `about.인증` |
| `reviews[]` / `faq[]` | `reviews[]` / `faq[]` |
| `seo.*` | `seo.지역명` · `seo.키워드` |
| `brand.color` · `moods` | `theme` · `brand.분위기` |

---

## 7. 광고를 시작하기 전에 **반드시** 채울 값

지금 비어 있고, 사용자만 알 수 있는 값입니다. 임의로 만들지 않았습니다.

| 어디에 | 무엇을 | 없으면 |
| --- | --- | --- |
| `submission.provider` · `endpoint` | 신청을 받을 곳 | **신청 버튼이 눌리지 않습니다** |
| `brand.contact.phone` · `kakao` · `email` | 공개 연락처 | 전송이 실패했을 때 손님이 닿을 길이 없습니다 |
| `brand.legal.businessName` · `owner` · `registration` · `address` · `contact` | 사업자 정보 | 푸터와 개인정보 안내에 표시되지 않습니다 (통신판매 고지 의무) |
| `brand.legal.retentionPeriod` | 개인정보 보유 기간 | 동의 안내에서 그 줄이 빠집니다 |
| `seo.noindex` | `false` 로 | 검색에 잡히지 않습니다 |
| `urls.self` | 실제 도메인 | canonical 과 공유 링크가 검수용 주소를 가리킵니다 |

`python tools/doctor.py` 가 비어 있는 것을 알려 줍니다.

---

## 8. 스팸과 중복 막기

| | |
| --- | --- |
| 벌집(honeypot) | 사람 눈에 보이지 않는 `_gotcha` 칸. 채워져 있으면 보내지 않습니다 |
| 너무 빠른 제출 | 화면을 연 지 **3초** 안에 누르면 막고 안내합니다 |
| 중복 제출 | 보내는 동안 버튼이 잠기고 글자가 바뀝니다. 성공하면 폼을 숨기고 다시 보내지 않습니다 |
| 기본 검증 | 필수값과 개인정보 동의가 없으면 브라우저가 먼저 막습니다 |

CAPTCHA 는 넣지 않았습니다. 실제로 스팸이 들어오기 시작하면 그때 답니다.

---

## 9. 개인정보

`/store/privacy/` 한 장에 모아 두었고, 두 폼의 동의 칸에서 펼쳐 볼 수 있습니다.
수집 항목 · 이용 목적 · 보유 기간 · 동의 거부와 그 결과를 적습니다.

보유 기간은 `brand.legal.retentionPeriod` 에서 옵니다. **비어 있으면 그 줄을
아예 빼 버립니다** — 비워 두고 "○○" 로 두는 것보다 없는 편이 낫습니다.

> 이 안내는 실제 사업자 정보가 확정되기 전의 **초안**입니다.
> 광고를 시작하기 전에 사업자 상호·등록번호·연락처를 채우고 한 번 검토해야 합니다.
> 법률 문서라고 주장하지 않습니다.

---

## 10. 새 샘플을 추가할 때

`storefront.json` 의 `samples.items` 에 한 덩어리를 넣고 `status` 를
`available` 로 두면 끝입니다.

```jsonc
{ "slug": "cafe-01", "category": "카페", "title": "CAFE 01",
  "subtitle": "동네 카페 · 베이커리", "styleTags": ["따뜻한"],
  "previewImage": "assets/samples/cafe-01.webp",
  "previewUrl": "https://…/cafe-01/", "product": "START", "status": "available" }
```

- 판매 페이지에 카드가 생기고
- 카드의 "이 디자인으로 제작하기" 가 `order/?product=START&sample=CAFE_01` 로 가고
- 주문 화면의 디자인 선택지에 `CAFE 01` 이 생깁니다.

제작 자료 폼의 업종 칸과 사진 안내를 붙이려면 `material.industryBlocks` 와
`material.photoGuides` 에 같은 제목으로 한 벌 더 적습니다. 안 적어도 **기본**
안내로 동작합니다.

---

## 11. 앞으로 관리자 웹을 붙일 때

지금은 사람이 대시보드/시트에서 보고 손으로 `siteConfig` 를 씁니다.
관리자 웹이 생기면 이렇게 이어집니다.

```
제출 JSON (kind=order)      → 주문 목록 · 상태(상담중/제작확정/납품)
제출 JSON (kind=material)   → 자료 상세 → siteConfig 초안 자동 생성
사진 링크 또는 첨부          → 역할별 배치 (hero/service/project/…)
                            → python -m factory.cli build → 미리보기 URL
                            → 고객 확인 → 수정 → 도메인 연결 → 납품
```

`version` 칸을 넣어 둔 이유가 이것입니다. 폼이 바뀌어도 옛 제출을
그대로 읽을 수 있습니다.

---

## 12. 이번에 만들지 않은 것

결제 · 세금계산서 · 자동 견적 · 회원가입 · 로그인 · 관리자 웹 · CRM ·
주문 상태 페이지 · 자동 카카오 알림 · 자동 이메일 워크플로 · 자동 도메인 연결.

고객 신청을 실제로 받고, 제작 자료를 실제로 받는 구조까지만 만들었습니다.
