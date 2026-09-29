-- SUBMISSION_BACKEND_V1 — 신청과 제작 자료를 받는 첫 표.
--
-- 설계 원칙 두 가지.
--   1. 찾을 때 쓰는 칸만 컬럼으로 둔다. 나머지는 raw_payload 에 원본 그대로.
--      폼이 바뀌어도 예전 신청 내용을 잃지 않기 위해서다.
--   2. 지우는 길을 처음부터 열어 둔다 (deleted_at). 개인정보 보유 기간이
--      지나면 표를 바꾸지 않고 지울 수 있어야 한다.

-- ── 제작 상담 신청 ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
  id                TEXT PRIMARY KEY,            -- ORD-20260929-K3F7
  version           TEXT NOT NULL,               -- ORDER_FLOW_V1
  kind              TEXT NOT NULL,               -- order | recommend
  status            TEXT NOT NULL DEFAULT 'NEW', -- NEW · CONTACTED · CONFIRMED · CANCELLED
  created_at        TEXT NOT NULL,               -- 서버 시각 (ISO8601 UTC)
  updated_at        TEXT NOT NULL,
  deleted_at        TEXT,

  product           TEXT,                        -- START · BUSINESS · PREMIUM
  sample            TEXT,                        -- INTERIOR 01 · … · undecided
  mode              TEXT,                        -- order | recommend

  company_name      TEXT NOT NULL,
  industry          TEXT,
  contact_name      TEXT,
  phone             TEXT,
  email             TEXT,
  domain_status     TEXT,
  existing_site     TEXT,
  notes             TEXT,

  premium_pages     TEXT,
  premium_features  TEXT,                        -- 쉼표로 이은 목록
  premium_reference TEXT,
  premium_budget    TEXT,
  premium_direction TEXT,

  consent_at        TEXT,                        -- 개인정보 동의 시각
  source_page       TEXT,
  referrer          TEXT,
  fingerprint       TEXT,                        -- 중복 제출 감지용 지문
  raw_payload       TEXT NOT NULL                -- 제출 당시 원본 JSON 전문
);

CREATE INDEX IF NOT EXISTS orders_created  ON orders (created_at DESC);
CREATE INDEX IF NOT EXISTS orders_status   ON orders (status, created_at DESC);
CREATE INDEX IF NOT EXISTS orders_finger   ON orders (fingerprint, created_at DESC);
CREATE INDEX IF NOT EXISTS orders_phone    ON orders (phone);

-- ── 제작 자료 ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS materials (
  id             TEXT PRIMARY KEY,               -- MAT-20260929-K3F7
  version        TEXT NOT NULL,
  kind           TEXT NOT NULL,                  -- material
  status         TEXT NOT NULL DEFAULT 'MATERIAL_RECEIVED',
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL,
  deleted_at     TEXT,

  order_id       TEXT,                           -- 고객이 적어 온 접수번호 (있으면)
  company_name   TEXT NOT NULL,
  contact_name   TEXT,
  phone          TEXT,
  design         TEXT,                           -- INTERIOR 01 · CLEANING 01 · COMPANY 01

  -- 아래 묶음은 통째로 JSON 이다. 관리자 웹이 그대로 읽어 siteConfig 를 만든다.
  company_json   TEXT,
  brand_json     TEXT,
  copy_json      TEXT,
  services_json  TEXT,
  strengths_json TEXT,
  projects_json  TEXT,
  reviews_json   TEXT,
  faq_json       TEXT,
  industry_json  TEXT,
  seo_json       TEXT,

  photo_link     TEXT,                           -- 구글 드라이브 등 공유 주소
  photo_state    TEXT,
  notes          TEXT,

  consent_at     TEXT,
  source_page    TEXT,
  fingerprint    TEXT,
  raw_payload    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS materials_created ON materials (created_at DESC);
CREATE INDEX IF NOT EXISTS materials_order   ON materials (order_id);
CREATE INDEX IF NOT EXISTS materials_finger  ON materials (fingerprint, created_at DESC);

-- ── 관리자 웹이 읽을 목록 ─────────────────────────────────────────
-- 주문 한 줄에 "제작 자료를 냈는지" 까지 붙여 둔다.
CREATE VIEW IF NOT EXISTS order_list AS
SELECT
  o.id,
  o.created_at,
  o.status,
  o.product,
  o.sample,
  o.company_name,
  o.industry,
  o.contact_name,
  o.phone,
  o.mode,
  (SELECT COUNT(*) FROM materials m
     WHERE m.deleted_at IS NULL
       AND (m.order_id = o.id
            OR (m.order_id IS NULL AND m.company_name = o.company_name))) AS material_count
FROM orders o
WHERE o.deleted_at IS NULL
ORDER BY o.created_at DESC;
