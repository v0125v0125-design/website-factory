/* WEBSITE FACTORY — 신청 접수 backend (SUBMISSION_BACKEND_V1)
 *
 *   GET  /health          살아 있는지
 *   POST /api/orders      제작 상담 신청 · 디자인 추천
 *   POST /api/materials   제작 자료
 *
 * 지키는 것.
 *   · 앞단 검증을 믿지 않는다. 서버에서 다시 본다.
 *   · 개인정보를 로그에 쓰지 않는다. 남기는 것은 접수번호·종류·성패·시각뿐.
 *   · 오류 속내를 손님에게 보내지 않는다. 사람이 읽을 한 줄만 보낸다.
 *   · 폼이 바뀌어도 잃지 않도록 제출 원본(raw_payload)을 통째로 함께 넣는다.
 */

const VERSION = "SUBMISSION_BACKEND_V1";

/* 길이 제한 — 넘으면 자른다. 손님을 막지 않으면서 표를 지킨다. */
const LIMITS = {
  short: 200,      // 상호 · 이름 · 전화 …
  medium: 600,     // 주소 · 참고 주소 …
  long: 4000,      // 요청사항
  json: 40000,     // 묶음 하나 (서비스 목록 등)
};

/* ── 도움말 ─────────────────────────────────────────────────── */

const json = (data, status, origin) =>
  new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...cors(origin),
    },
  });

function allowed(env) {
  return String(env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((one) => one.trim())
    .filter(Boolean);
}

/* Origin 이 목록에 있을 때만 헤더를 돌려준다. `*` 는 쓰지 않는다. */
function cors(origin) {
  if (!origin) return { Vary: "Origin" };
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function text(value, limit) {
  if (value === null || value === undefined) return null;
  const one = String(value).trim();
  if (!one) return null;
  return one.length > limit ? one.slice(0, limit) : one;
}

function packed(value, limit = LIMITS.json) {
  if (value === null || value === undefined) return null;
  const one = JSON.stringify(value);
  if (!one || one === "null" || one === "{}" || one === "[]") return null;
  return one.length > limit ? one.slice(0, limit) : one;
}

/* 사람이 부르기 쉬운 접수번호. 헷갈리는 글자(I·O·0·1)는 뺀다. */
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

function newId(prefix, now) {
  const day =
    now.getUTCFullYear().toString() +
    String(now.getUTCMonth() + 1).padStart(2, "0") +
    String(now.getUTCDate()).padStart(2, "0");
  const bytes = crypto.getRandomValues(new Uint8Array(4));
  let tail = "";
  for (const one of bytes) tail += ALPHABET[one % ALPHABET.length];
  return `${prefix}-${day}-${tail}`;
}

/* 같은 사람이 실수로 두 번 누른 것을 알아보는 지문. 되돌릴 수 없게 해싱한다. */
async function fingerprint(parts) {
  const raw = parts.map((one) => String(one || "").trim().toLowerCase()).join("|");
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(raw));
  return [...new Uint8Array(digest)].slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
}

/* 로그 — 개인정보는 한 글자도 넣지 않는다. */
function note(entry) {
  try {
    console.log(JSON.stringify({ at: new Date().toISOString(), ...entry }));
  } catch (_) {
    /* 로그가 실패해도 접수는 계속됩니다 */
  }
}

/* ── 들어온 요청 다듬기 ─────────────────────────────────────── */

class Refused extends Error {
  constructor(status, message, code) {
    super(message);
    this.status = status;
    this.code = code || "invalid";
  }
}

async function readBody(request, env) {
  const type = (request.headers.get("Content-Type") || "").toLowerCase();
  const ok = type.includes("application/json") || type.includes("text/plain");
  if (!ok) throw new Refused(415, "보낼 수 없는 형식입니다.", "content_type");

  const max = Number(env.MAX_BODY_BYTES || 131072);
  const declared = Number(request.headers.get("Content-Length") || 0);
  if (declared && declared > max) throw new Refused(413, "보내신 내용이 너무 깁니다.", "too_large");

  const body = await request.text();
  if (body.length > max) throw new Refused(413, "보내신 내용이 너무 깁니다.", "too_large");

  try {
    const data = JSON.parse(body);
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      throw new Error("not an object");
    }
    return data;
  } catch (_) {
    throw new Refused(400, "내용을 읽지 못했습니다.", "bad_json");
  }
}

/* 앞단이 통과시켰어도 여기서 다시 본다. */
function guard(payload, env, required) {
  if (text(payload._gotcha, LIMITS.short)) {
    throw new Refused(400, "신청을 확인하지 못했습니다.", "honeypot");
  }
  const elapsed = Number(payload.elapsedMs || 0);
  const floor = Number(env.MIN_FILL_MS || 3000);
  if (elapsed && elapsed < floor) {
    throw new Refused(429, "조금만 더 확인하신 뒤 다시 보내 주십시오.", "too_fast");
  }
  const missing = required.filter(([, value]) => !value).map(([label]) => label);
  if (missing.length) {
    throw new Refused(422, `${missing.join(" · ")} 을(를) 적어 주십시오.`, "missing");
  }
}

function needConsent(value, message) {
  if (!value) throw new Refused(422, message, "consent");
}

function consentAt(payload, key) {
  const block = payload.consent || {};
  if (block[key] !== true) return null;
  return text(block.at, LIMITS.short) || new Date().toISOString();
}

/* 같은 지문이 최근에 들어왔으면 그 접수번호를 그대로 돌려준다. */
async function recent(env, table, mark, now) {
  if (!mark) return null;
  const window = Number(env.DUPLICATE_WINDOW_MS || 120000);
  const since = new Date(now.getTime() - window).toISOString();
  const found = await env.DB.prepare(
    `SELECT id FROM ${table} WHERE fingerprint = ?1 AND created_at >= ?2 AND deleted_at IS NULL
     ORDER BY created_at DESC LIMIT 1`
  )
    .bind(mark, since)
    .first();
  return found ? found.id : null;
}

/* 접수번호가 부딪히면 다시 뽑는다. */
async function insert(env, prefix, now, run) {
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const id = newId(prefix, now);
    try {
      await run(id);
      return id;
    } catch (error) {
      const message = String(error && error.message);
      if (attempt < 4 && /UNIQUE|PRIMARY KEY|constraint/i.test(message)) continue;
      throw error;
    }
  }
  throw new Error("could not allocate id");
}

/* ── 제작 상담 신청 ─────────────────────────────────────────── */

async function saveOrder(payload, env, now) {
  const lead = payload.lead || {};
  const source = payload.source || {};
  const premium = payload.premium || {};

  const company = text(lead.company, LIMITS.short);
  const industry = text(lead.industry, LIMITS.short);
  const name = text(lead.name, LIMITS.short);
  const phone = text(lead.contact || lead.phone, LIMITS.short);
  const consent = consentAt(payload, "privacy");

  guard(payload, env, [
    ["업체명", company],
    ["업종", industry],
    ["담당자명", name],
    ["연락처", phone],
  ]);
  needConsent(consent, "개인정보 수집·이용에 동의해 주십시오.");

  const mode = text(payload.kind, LIMITS.short) === "recommend" ? "recommend" : "order";
  const mark = await fingerprint(["order", company, phone, source.product, source.sample]);
  const already = await recent(env, "orders", mark, now);
  if (already) return { id: already, status: "NEW", duplicate: true };

  const stamp = now.toISOString();
  const features = Array.isArray(premium.features) ? premium.features.join(", ") : null;

  const id = await insert(env, "ORD", now, (candidate) =>
    env.DB.prepare(
      `INSERT INTO orders (
        id, version, kind, status, created_at, updated_at,
        product, sample, mode,
        company_name, industry, contact_name, phone, email,
        domain_status, existing_site, notes,
        premium_pages, premium_features, premium_reference, premium_budget, premium_direction,
        consent_at, source_page, referrer, fingerprint, raw_payload
      ) VALUES (?1,?2,?3,'NEW',?4,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,
                ?16,?17,?18,?19,?20,?21,?22,?23,?24,?25)`
    )
      .bind(
        candidate,
        text(payload.version, LIMITS.short) || "unknown",
        mode,
        stamp,
        text(source.product, LIMITS.short),
        text(source.sample, LIMITS.short),
        mode,
        company,
        industry,
        name,
        phone,
        text(lead.email, LIMITS.short),
        text(lead.domain, LIMITS.short),
        text(lead.site, LIMITS.medium),
        text(lead.message, LIMITS.long),
        text(premium.pages, LIMITS.short),
        text(features, LIMITS.medium),
        text(premium.reference, LIMITS.medium),
        text(premium.budget, LIMITS.short),
        text(premium.direction, LIMITS.long),
        consent,
        text(source.page, LIMITS.medium),
        text(source.referrer, LIMITS.medium),
        mark,
        JSON.stringify(payload).slice(0, Number(env.MAX_BODY_BYTES || 131072))
      )
      .run()
  );

  return { id, status: "NEW", duplicate: false };
}

/* ── 제작 자료 ──────────────────────────────────────────────── */

async function saveMaterial(payload, env, now) {
  const lead = payload.lead || {};
  const source = payload.source || {};
  const photos = payload.photos || {};

  const company = text(lead.company, LIMITS.short);
  const name = text(lead.name, LIMITS.short);
  const phone = text(lead.contact || lead.phone, LIMITS.short);
  const consent = consentAt(payload, "material");

  guard(payload, env, [
    ["업체명", company],
    ["담당자명 또는 연락처", name || phone],
  ]);
  needConsent(consent, "제출 자료를 제작에 사용하는 데 동의해 주십시오.");

  const mark = await fingerprint(["material", company, phone, lead.orderId]);
  const already = await recent(env, "materials", mark, now);
  if (already) return { id: already, status: "MATERIAL_RECEIVED", duplicate: true };

  const stamp = now.toISOString();
  const id = await insert(env, "MAT", now, (candidate) =>
    env.DB.prepare(
      `INSERT INTO materials (
        id, version, kind, status, created_at, updated_at,
        order_id, company_name, contact_name, phone, design,
        company_json, brand_json, copy_json, services_json, strengths_json,
        projects_json, reviews_json, faq_json, industry_json, seo_json,
        photo_link, photo_state, notes, consent_at, source_page, fingerprint, raw_payload
      ) VALUES (?1,?2,'material','MATERIAL_RECEIVED',?3,?3,?4,?5,?6,?7,?8,
                ?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20,?21,?22,?23,?24,?25)`
    )
      .bind(
        candidate,
        text(payload.version, LIMITS.short) || "unknown",
        stamp,
        text(lead.orderId, LIMITS.short),
        company,
        name,
        phone,
        text(source.design || lead.design, LIMITS.short),
        packed(payload.company),
        packed(payload.brand),
        packed(payload.copy),
        packed(payload.services),
        packed(payload.strengths),
        packed(payload.projects),
        packed(payload.reviews),
        packed(payload.faq),
        packed(payload.industry),
        packed(payload.seo),
        text(photos.link, LIMITS.medium),
        text(photos.state, LIMITS.short),
        text(payload.notes, LIMITS.long),
        consent,
        text(source.page, LIMITS.medium),
        mark,
        JSON.stringify(payload).slice(0, Number(env.MAX_BODY_BYTES || 131072))
      )
      .run()
  );

  return { id, status: "MATERIAL_RECEIVED", duplicate: false };
}

/* ── 길잡이 ─────────────────────────────────────────────────── */

const ROUTES = {
  "/api/orders": { save: saveOrder, kind: "order" },
  "/api/materials": { save: saveMaterial, kind: "material" },
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    const list = allowed(env);
    const okOrigin = !origin || list.includes(origin);
    const echo = okOrigin ? origin : null;

    if (url.pathname === "/health") {
      if (request.method !== "GET" && request.method !== "HEAD") {
        return json({ ok: false, error: "이 주소는 조회만 됩니다." }, 405, echo);
      }
      let db = "unknown";
      try {
        await env.DB.prepare("SELECT 1").first();
        db = "ok";
      } catch (_) {
        db = "down";
      }
      return json(
        { ok: db === "ok", service: "website-factory-api", version: VERSION, db,
          time: new Date().toISOString() },
        db === "ok" ? 200 : 503,
        echo
      );
    }

    const route = ROUTES[url.pathname];
    if (!route) return json({ ok: false, error: "없는 주소입니다." }, 404, echo);

    if (request.method === "OPTIONS") {
      if (!okOrigin) return json({ ok: false, error: "허용되지 않은 곳에서 왔습니다." }, 403, null);
      return new Response(null, { status: 204, headers: cors(origin) });
    }
    if (request.method !== "POST") {
      return json({ ok: false, error: "이 주소는 제출만 받습니다." }, 405, echo);
    }
    if (!okOrigin) {
      note({ kind: route.kind, ok: false, code: "origin" });
      return json({ ok: false, error: "허용되지 않은 곳에서 왔습니다." }, 403, null);
    }

    const started = Date.now();
    try {
      const payload = await readBody(request, env);
      const result = await route.save(payload, env, new Date());
      note({ id: result.id, kind: route.kind, ok: true, duplicate: result.duplicate,
             ms: Date.now() - started });
      return json({ ok: true, ...result, receivedAt: new Date().toISOString() }, 200, echo);
    } catch (error) {
      if (error instanceof Refused) {
        note({ kind: route.kind, ok: false, code: error.code, ms: Date.now() - started });
        return json({ ok: false, error: error.message, code: error.code }, error.status, echo);
      }
      // 속내는 서버에만 남기고 손님에게는 한 줄만 보냅니다.
      note({ kind: route.kind, ok: false, code: "server",
             detail: String(error && error.message).slice(0, 200), ms: Date.now() - started });
      return json(
        { ok: false, error: "지금은 접수하지 못했습니다. 잠시 후 다시 시도해 주십시오.", code: "server" },
        500,
        echo
      );
    }
  },
};
