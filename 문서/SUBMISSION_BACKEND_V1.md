# SUBMISSION_BACKEND_V1

신청을 **실제로 받아 저장하는** 서버입니다. 판매 홈페이지(정적 GitHub Pages)와
완전히 분리되어 있고, 관리자 웹은 아직 없습니다.

```
브라우저 (판매 홈페이지)
   │  POST /api/orders     또는  /api/materials
   ▼
Cloudflare Worker  website-factory-api
   │  검증 → 접수번호 발급 → 중복 확인
   ▼
Cloudflare D1  website-factory   (SQLite)
   │
   └─→ 나중에: 관리자 웹이 같은 D1 을 읽습니다
```

## 1. 지금 상태

| | |
| --- | --- |
| 코드 · 스키마 · 설정 | **완성** (`backend/`) |
| 로컬 구동 · 시험 | **확인됨** — 계정 없이 `npm run dev` 로 돕니다 |
| 실제 배포 | **아직** — Cloudflare 로그인이 필요합니다 (아래 5장) |
| 판매 홈페이지 연결 | 어댑터 준비 완료. `submission` 두 줄만 채우면 켜집니다 |

배포 전까지 판매 홈페이지의 신청 버튼은 **눌리지 않습니다.** 받는 곳이 없는데
접수되었다고 말하지 않기 위해서입니다.

## 2. 파일

```
backend/
  wrangler.toml                     Worker 이름 · D1 연결 · 허용 origin
  package.json                      npm run dev / migrate / deploy
  src/index.js                      Worker 본체 (의존성 없음)
  migrations/
    0001_submission_v1.sql          orders · materials · order_list 뷰
```

## 3. 주소

| | | |
| --- | --- | --- |
| `GET /health` | 살아 있는지 · DB 가 붙었는지 | 누구나 |
| `POST /api/orders` | 제작 상담 신청 · 디자인 추천 | 허용된 origin 만 |
| `POST /api/materials` | 제작 자료 | 허용된 origin 만 |

### 돌려주는 답

```jsonc
// 성공
{ "ok": true, "id": "ORD-20260929-K3F7", "status": "NEW",
  "duplicate": false, "receivedAt": "2026-09-29T…Z" }

// 거절 (4xx) — error 는 손님에게 그대로 보여 줄 수 있는 한국어 한 줄
{ "ok": false, "error": "개인정보 수집·이용에 동의해 주십시오.", "code": "consent" }
```

`code` 는 `missing` · `consent` · `honeypot` · `too_fast` · `too_large` ·
`content_type` · `bad_json` · `server` 중 하나입니다.

## 4. 접수번호

```
ORD-20260929-K3F7      제작 상담 신청
MAT-20260929-P2X8      제작 자료
```

날짜 + 네 글자. 헷갈리는 글자(I·O·0·1)를 뺀 32자에서 뽑아 전화로 불러 주기
쉽습니다. 부딪히면 다시 뽑습니다(최대 5회). **고객에게 그대로 보여 주는 번호**이고,
성공 화면에 크게 표시됩니다.

## 5. 배포 — 사용자가 해야 하는 단계

이 다섯 줄이 전부입니다. 셋째 줄에서 브라우저가 열리고 Cloudflare 로그인을 묻습니다.

```bash
cd backend
npm install                                   # 이미 했다면 건너뜀
npx wrangler login                            # ← 브라우저에서 로그인·승인 (사람이 해야 합니다)
npx wrangler d1 create website-factory        # → database_id 가 나옵니다
#   wrangler.toml 의 database_id = "PLACEHOLDER…" 를 그 값으로 바꿉니다
npx wrangler d1 migrations apply website-factory --remote
npx wrangler deploy                           # → https://website-factory-api.<계정>.workers.dev
```

무료 플랜으로 충분합니다 (Workers 10만 요청/일 · D1 5GB).

배포가 끝나면 나온 주소로 두 가지를 합니다.

```bash
curl https://website-factory-api.<계정>.workers.dev/health
# {"ok":true,...,"db":"ok"} 가 나와야 합니다
```

```jsonc
// storefront/storefront.json
"submission": {
  "provider": "website_factory",
  "endpoint": "https://website-factory-api.<계정>.workers.dev",
  "successUrl": ""
}
```

```bash
python tools/build_previews.py _site && tools/publish_preview.sh
python tools/doctor.py        # "접수 서버 … DB 연결됨" 이 뜨면 끝입니다
```

## 6. 로컬에서 돌려 보기 (계정 없이)

```bash
cd backend
npm run migrate:local       # 로컬 D1 에 표를 만든다
npm run dev                 # http://127.0.0.1:8787

curl http://127.0.0.1:8787/health
```

판매 홈페이지를 로컬 Worker 에 붙여 보려면 `submission.endpoint` 를
`http://127.0.0.1:8787` 로 두고 짓되, Worker 를 띄울 때 허용 origin 을 늘립니다.

```bash
npx wrangler dev --local --var 'ALLOWED_ORIGINS:http://127.0.0.1:8080'
```

## 7. 표

### `orders`

| 칸 | |
| --- | --- |
| `id` | `ORD-…` (기본키) |
| `status` | `NEW` → `CONTACTED` → `CONFIRMED` / `CANCELLED` |
| `created_at` · `updated_at` · `deleted_at` | **서버 시각**. 앞단이 보낸 시각을 믿지 않습니다 |
| `product` · `sample` · `mode` | START/BUSINESS/PREMIUM · INTERIOR 01 … · order/recommend |
| `company_name` · `industry` · `contact_name` · `phone` · `email` | 찾을 때 쓰는 칸 |
| `domain_status` · `existing_site` · `notes` | |
| `premium_*` | PREMIUM 일 때만 |
| `consent_at` | 개인정보 동의 시각 |
| `fingerprint` | 중복 감지용 해시 (되돌릴 수 없음) |
| **`raw_payload`** | **제출 당시 JSON 전문** |

### `materials`

`id`(`MAT-…`) · `status`(`MATERIAL_RECEIVED`) · `order_id` · `company_name` ·
`contact_name` · `phone` · `design` · `photo_link` · `notes` · `consent_at` ·
`fingerprint` · **`raw_payload`**, 그리고 묶음들:
`company_json` · `brand_json` · `copy_json` · `services_json` · `strengths_json` ·
`projects_json` · `reviews_json` · `faq_json` · `industry_json` · `seo_json`.

**왜 이렇게 나눴나.** 목록에서 검색·정렬할 칸만 컬럼으로 두고, 나머지는 JSON 으로
둡니다. 지나치게 정규화하면 폼이 조금만 바뀌어도 마이그레이션이 필요합니다.
그리고 무슨 일이 있어도 `raw_payload` 에 원본이 통째로 남습니다.

### `order_list` 뷰 — 관리자 웹이 읽을 목록

```sql
SELECT * FROM order_list LIMIT 20;
```

```
ORD-20260929-P7Q3 │ 2026-09-29 │ NEW │ START │ CLEANING 01 │ 바른결 홈케어 │ 010-… │ 자료 1건
```

`material_count` 가 **제작 자료 제출 여부**입니다. `order_id` 로 잇고, 고객이
접수번호를 안 적었으면 업체명으로 잇습니다.

## 8. 데이터 확인하는 법 (관리자 웹 전까지)

```bash
cd backend

# 새 신청 20건
npx wrangler d1 execute website-factory --remote \
  --command "SELECT * FROM order_list LIMIT 20;"

# 한 건의 원본 전문
npx wrangler d1 execute website-factory --remote \
  --command "SELECT raw_payload FROM orders WHERE id='ORD-20260929-K3F7';"

# 상태 바꾸기
npx wrangler d1 execute website-factory --remote \
  --command "UPDATE orders SET status='CONTACTED', updated_at=datetime('now') WHERE id='ORD-…';"

# 실시간 로그 (개인정보는 없습니다)
npx wrangler tail
```

Cloudflare 대시보드 → Workers & Pages → D1 → website-factory 에서 브라우저로도
같은 질의를 할 수 있습니다.

### 내보내기 · 백업

```bash
npx wrangler d1 export website-factory --remote --output backup-$(date +%F).sql
```

D1 은 자체적으로 시점 복구(Time Travel)를 30일까지 제공합니다. 그래도 광고를
시작하면 주 1회 위 명령으로 파일 백업을 따로 두는 편이 안전합니다.

## 9. 보안

| | |
| --- | --- |
| HTTPS | Workers 는 HTTPS 만 받습니다 |
| CORS | `ALLOWED_ORIGINS` 목록에 있는 곳만. **`*` 를 쓰지 않습니다** |
| 메서드 | `/api/*` 는 POST 와 OPTIONS 만 |
| Content-Type | `application/json` · `text/plain` 만 |
| 본문 크기 | 기본 128KB 넘으면 413 |
| 입력 길이 | 칸마다 잘라서 저장 (상호 200 · 요청사항 4000 …) |
| 벌집 | `_gotcha` 가 채워져 있으면 400 |
| 너무 빠른 제출 | 화면을 연 지 3초 안이면 429 |
| SQL | 전부 `?n` 파라미터 바인딩. 문자열을 이어 붙이지 않습니다 |
| 오류 | 속내(스택·SQL·D1 오류)를 손님에게 보내지 않습니다 |
| API 키 | **브라우저에 넣지 않습니다.** 넣을 키 자체가 없습니다 |

CORS 는 인증이 아닙니다 — 브라우저 밖에서 오는 요청은 막지 못합니다. V1 에서는
이것으로 충분하다고 보았고, 스팸이 실제로 들어오면 그때 Turnstile 을 답니다.

### 판매 도메인이 바뀌면

`backend/wrangler.toml` 의 `ALLOWED_ORIGINS` **한 줄만** 고치고 다시 배포합니다.
쉼표로 여러 개를 둘 수 있습니다.

```toml
ALLOWED_ORIGINS = "https://v0125v0125-design.github.io,https://실제도메인.kr"
```

## 10. 로그와 개인정보

로그에 남는 것은 이것뿐입니다.

```json
{"at":"2026-09-29T04:53:23.817Z","id":"MAT-20260929-LUL9","kind":"material","ok":true,"ms":16}
```

전화번호·이메일·상호·전체 payload 는 **한 글자도 찍지 않습니다.**
서버 오류일 때만 오류 메시지 앞 200자를 남기는데, 여기에도 제출 내용은 넣지 않습니다.
`tests/test_submission_backend.py::test_logs_carry_no_personal_details` 가 지킵니다.

### 보관과 삭제

`created_at` · `updated_at` · `deleted_at` 을 처음부터 두었습니다.
개인정보 안내에 적은 보유 기간(`brand.legal.retentionPeriod`)이 지나면
이렇게 지웁니다.

```sql
-- 먼저 가려 두고 (되돌릴 수 있음)
UPDATE orders SET deleted_at = datetime('now')
 WHERE created_at < datetime('now', '-6 months') AND deleted_at IS NULL;

-- 완전히 지울 때
DELETE FROM orders WHERE deleted_at < datetime('now', '-30 days');
```

`order_list` 뷰는 `deleted_at IS NULL` 만 보여 주므로, 가려 두기만 해도 목록에서
사라집니다. 자동 삭제 cron 은 아직 만들지 않았습니다 — 실제 운영이 시작되고
보유 기간이 확정된 뒤에 답니다.

## 11. 중복 제출

앞단의 버튼 잠금만 믿지 않습니다. 서버가 `kind + 업체명 + 연락처 + 상품 + 디자인`
으로 지문을 만들고(SHA-256, 되돌릴 수 없음), **2분 안에** 같은 지문이 다시 오면
새 줄을 만들지 않고 **먼저 만든 접수번호를 그대로** 돌려줍니다.

고객 화면에는 똑같이 성공으로 보입니다. 손님을 혼내지 않으면서 표에는 한 줄만
남습니다. 창을 늘리고 싶으면 `DUPLICATE_WINDOW_MS` 를 바꿉니다.

## 12. 파일 업로드

**이번에는 받지 않습니다.** 제작 자료 폼은 지금처럼 공유 링크(구글 드라이브 ·
네이버 MYBOX)를 한 칸으로 받고, 그 주소가 `photo_link` 에 저장됩니다.

나중에 직접 받으려면 Cloudflare R2 를 붙입니다.

```toml
[[r2_buckets]]
binding = "PHOTOS"
bucket_name = "website-factory-photos"
```

`POST /api/uploads` 를 하나 더 만들어 R2 에 넣고, 그 키를 `materials` 에
`photo_keys` 컬럼으로 추가하면 됩니다. 마이그레이션 `0002_*.sql` 한 장이면 됩니다.

## 13. 관리자 웹을 붙일 때

D1 은 그대로 두고 **읽는 화면만** 만들면 됩니다.

```
GET  /admin/orders          order_list 뷰를 그대로
GET  /admin/orders/:id      orders + 붙은 materials
PATCH /admin/orders/:id     status 변경
```

관리자 화면에는 **반드시 인증을 답니다** — Cloudflare Access 를 Worker 앞에
붙이는 것이 가장 간단합니다(코드 변경 없음). 지금 `/api/*` 에 인증이 없는 것은
누구나 신청을 넣을 수 있어야 하기 때문이고, 읽는 쪽은 다릅니다.

제작 자료 → siteConfig 매핑은 `문서/ORDER_FLOW_V1.md` 6장에 표로 있습니다.

## 14. 시험

`tests/test_submission_backend.py` 33건.

- 파일만 보는 것 — 배포 파일이 다 있는가 · `raw_payload` 를 두었는가 ·
  `deleted_at` 이 있는가 · 관리자 목록 뷰가 있는가 · CORS 에 `*` 가 없는가 ·
  주소가 한 곳에만 있는가 · 브라우저에 키를 주지 않는가 · **로그에 개인정보가
  없는가** · SQL 을 문자열로 잇지 않는가
- 실제로 띄워 보는 것 — health · 정상 주문 · 정상 자료 · 접수번호 모양과 중복 ·
  필수값 넷 · 동의 없음 · 벌집 · 너무 빠름 · 같은 제출 두 번 · 허용 안 된 origin ·
  CORS 헤더 · 사전요청 · GET 금지 · 없는 주소 · 잘못된 Content-Type · 깨진 JSON ·
  너무 큰 본문 · SQL 처럼 생긴 입력 · 한글과 긴 글 · **오류에 속내가 없는가**

살아 있는 검사는 **시험 전용 D1**(임시 폴더)에 붙습니다. 개발 중 시험 신청이
진짜 주문 목록에 섞이지 않습니다. `wrangler` 가 없는 컴퓨터에서는 건너뜁니다.

판매 홈페이지 쪽은 `tests/test_order_flow.py` 가 봅니다 — 어댑터가 올바른 주소로
쏘는지, 접수번호를 보여 주는지, 서버가 거절하면 성공 화면이 뜨지 않는지,
연결이 끊겼을 때 개발자 말이 새지 않는지.

## 15. 이번에 만들지 않은 것

관리자 웹 · 로그인 · 결제 · 고객 주문조회 · 자동 이메일 · 카카오 알림 ·
파일 직접 업로드 · CRM · 자동 삭제 cron.
