"""SUBMISSION_BACKEND_V1 — 신청이 실제로 DB 에 한 줄로 남는지 지킨다.

여기서 띄우는 Worker 는 **따로 만든 시험용 D1** 을 씁니다(`--persist-to` 가
임시 폴더). 개발 중에 넣은 시험 신청이 진짜 주문 목록에 섞이지 않게 하기
위해서입니다.

wrangler 나 node 가 없는 컴퓨터에서는 살아 있는 검사를 건너뜁니다 —
파일만 보는 검사는 그대로 돕니다.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
ORIGIN = "https://v0125v0125-design.github.io"


# ── 파일만 보는 검사 ──────────────────────────────────────────────
def test_the_backend_ships_everything_needed_to_deploy():
    for name in ("wrangler.toml", "package.json", "src/index.js",
                 "migrations/0001_submission_v1.sql"):
        assert (BACKEND / name).is_file(), name


def test_the_schema_keeps_the_original_payload():
    """폼이 바뀌어도 예전 신청 내용을 잃지 않아야 합니다."""
    sql = (BACKEND / "migrations" / "0001_submission_v1.sql").read_text(encoding="utf-8")
    for table in ("orders", "materials"):
        block = sql.split(f"CREATE TABLE IF NOT EXISTS {table}")[1].split(");")[0]
        assert "raw_payload       TEXT NOT NULL" in block or "raw_payload    TEXT NOT NULL" in block
        for column in ("created_at", "updated_at", "deleted_at", "status", "fingerprint"):
            assert column in block, f"{table}.{column}"


def test_the_admin_list_is_ready_before_the_admin_web_exists():
    sql = (BACKEND / "migrations" / "0001_submission_v1.sql").read_text(encoding="utf-8")
    view = sql.split("CREATE VIEW IF NOT EXISTS order_list AS")[1]
    for column in ("o.id", "o.created_at", "o.status", "o.product", "o.sample",
                   "o.company_name", "o.phone", "material_count"):
        assert column in view, column
    assert "o.deleted_at IS NULL" in view


def test_cors_is_never_a_wildcard():
    worker = (BACKEND / "src" / "index.js").read_text(encoding="utf-8")
    assert '"*"' not in worker.split("function cors")[1].split("}")[0]
    assert "ALLOWED_ORIGINS" in worker
    config = (BACKEND / "wrangler.toml").read_text(encoding="utf-8")
    assert ORIGIN in config
    assert 'ALLOWED_ORIGINS = "*"' not in config


def test_the_endpoint_is_written_in_exactly_one_place():
    """주소를 여기저기 박아 두면 나중에 못 바꿉니다."""
    hits = []
    for path in list((ROOT / "storefront").rglob("*.j2")) + list((ROOT / "storefront").rglob("*.html")):
        if "workers.dev" in path.read_text(encoding="utf-8"):
            hits.append(path.name)
    assert not hits, hits
    adapter = (ROOT / "storefront" / "templates" / "submit.js.j2").read_text(encoding="utf-8")
    assert "CONFIG.endpoint" in adapter
    assert "website_factory" in adapter


def test_no_api_key_is_handed_to_the_browser():
    adapter = (ROOT / "storefront" / "templates" / "submit.js.j2").read_text(encoding="utf-8")
    for word in ("apiKey", "api_key", "Authorization", "secret", "token"):
        assert word not in adapter, word


def test_logs_carry_no_personal_details():
    worker = (BACKEND / "src" / "index.js").read_text(encoding="utf-8")
    logged = re.findall(r"note\(\{([^}]*)\}\)", worker, re.S)
    assert logged
    for block in logged:
        for leak in ("phone", "company", "email", "payload", "lead", "raw"):
            assert leak not in block, f"로그에 {leak}"


def test_sql_is_always_parameter_bound():
    worker = (BACKEND / "src" / "index.js").read_text(encoding="utf-8")
    for statement in re.findall(r"prepare\(\s*`([^`]+)`", worker):
        assert "${" not in statement or "FROM ${table}" in statement, statement[:80]


# ── 살아 있는 Worker 를 상대로 ────────────────────────────────────
def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    """시험 전용 D1 을 가진 Worker 하나. 끝나면 통째로 버립니다."""
    if not shutil.which("node"):
        pytest.skip("node 가 없으면 건너뜁니다")
    if not (BACKEND / "node_modules" / "wrangler").is_dir():
        pytest.skip("backend 에 wrangler 가 없습니다 — cd backend && npm install")

    state = tmp_path_factory.mktemp("d1-test")
    env = {**os.environ, "WRANGLER_SEND_METRICS": "false", "CI": "1", "NO_COLOR": "1"}
    common = ["npx", "wrangler", "d1", "migrations", "apply", "website-factory",
              "--local", "--persist-to", str(state)]
    done = subprocess.run(common, cwd=BACKEND, env=env, capture_output=True, text=True, timeout=300)
    if done.returncode != 0:
        pytest.skip(f"시험용 D1 을 만들지 못했습니다: {done.stderr[-300:]}")

    port = _free_port()
    process = subprocess.Popen(
        ["npx", "wrangler", "dev", "--local", "--persist-to", str(state),
         "--port", str(port), "--ip", "127.0.0.1", "--var", f"ALLOWED_ORIGINS:{ORIGIN}"],
        cwd=BACKEND, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        time.sleep(1)
        if process.poll() is not None:
            pytest.skip("wrangler dev 가 떴다가 죽었습니다")
        try:
            with urllib.request.urlopen(base + "/health", timeout=2) as response:
                if response.status == 200:
                    break
        except Exception:
            continue
    else:
        process.terminate()
        pytest.skip("wrangler dev 가 시간 안에 뜨지 않았습니다")

    yield base
    process.terminate()
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()


def call(base, path, payload=None, origin=ORIGIN, method="POST",
         content_type="application/json", raw=None):
    body = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    request = urllib.request.Request(base + path, data=body, method=method)
    if origin:
        request.add_header("Origin", origin)
    if body is not None:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read() or b"{}"), dict(response.headers)
    except urllib.error.HTTPError as error:
        text = error.read()
        try:
            data = json.loads(text or b"{}")
        except json.JSONDecodeError:
            data = {"raw": text.decode("utf-8", "replace")}
        return error.code, data, dict(error.headers)


def order(**over):
    data = {
        "kind": "order", "version": "ORDER_FLOW_V1", "elapsedMs": 9000,
        "source": {"page": "https://x/store/order/", "product": "START", "sample": "INTERIOR 01"},
        "lead": {"company": "시험인테리어", "industry": "인테리어", "name": "홍길동",
                 "contact": "010-1234-5678"},
        "consent": {"privacy": True, "at": "2026-09-29T00:00:00.000Z"},
    }
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value
    return data


def material(**over):
    data = {
        "kind": "material", "version": "ORDER_FLOW_V1", "elapsedMs": 20000,
        "source": {"page": "https://x/store/materials/", "design": "CLEANING 01"},
        "lead": {"company": "시험홈케어", "name": "김담당", "contact": "010-2222-3333"},
        "services": [{"name": "입주청소", "note": "빈 집"}],
        "photos": {"link": "https://drive.google.com/drive/folders/x"},
        "consent": {"material": True, "at": "2026-09-29T00:00:00.000Z"},
    }
    data.update(over)
    return data


def test_health_says_the_database_is_reachable(api):
    status, body, _ = call(api, "/health", method="GET", origin=None)
    assert status == 200
    assert body["ok"] is True and body["db"] == "ok"
    assert body["version"] == "SUBMISSION_BACKEND_V1"


def test_a_valid_order_gets_a_receipt_number(api):
    status, body, _ = call(api, "/api/orders", order(lead={"company": "접수번호시험"}))
    assert status == 200 and body["ok"] is True
    assert re.fullmatch(r"ORD-\d{8}-[A-Z2-9]{4}", body["id"]), body["id"]
    assert body["status"] == "NEW" and body["duplicate"] is False


def test_a_valid_material_gets_its_own_receipt_number(api):
    status, body, _ = call(api, "/api/materials", material(lead={"company": "자료시험", "name": "김"}))
    assert status == 200 and body["ok"] is True
    assert re.fullmatch(r"MAT-\d{8}-[A-Z2-9]{4}", body["id"]), body["id"]
    assert body["status"] == "MATERIAL_RECEIVED"


def test_receipt_numbers_do_not_repeat(api):
    seen = {call(api, "/api/orders", order(lead={"company": f"중복없음{n}"}))[1]["id"]
            for n in range(6)}
    assert len(seen) == 6, seen


@pytest.mark.parametrize("missing", ["company", "industry", "name", "contact"])
def test_the_server_checks_the_required_fields_itself(api, missing):
    payload = order(lead={"company": f"누락{missing}"})
    payload["lead"][missing] = ""
    status, body, _ = call(api, "/api/orders", payload)
    assert status == 422 and body["ok"] is False and body["code"] == "missing"


def test_an_order_without_consent_is_refused(api):
    status, body, _ = call(api, "/api/orders", order(consent={"privacy": False}))
    assert status == 422 and body["code"] == "consent"
    assert "동의" in body["error"]


def test_a_material_without_consent_is_refused(api):
    status, body, _ = call(api, "/api/materials", material(consent={}))
    assert status == 422 and body["code"] == "consent"


def test_a_filled_honeypot_is_refused(api):
    status, body, _ = call(api, "/api/orders", order(_gotcha="bot"))
    assert status == 400 and body["code"] == "honeypot"


def test_an_instant_submission_is_refused(api):
    status, body, _ = call(api, "/api/orders", order(elapsedMs=200))
    assert status == 429 and body["code"] == "too_fast"


def test_the_same_submission_twice_makes_one_row(api):
    payload = order(lead={"company": "두번눌림", "contact": "010-7777-8888"})
    first_status, first, _ = call(api, "/api/orders", payload)
    second_status, second, _ = call(api, "/api/orders", payload)
    assert first_status == second_status == 200
    assert first["id"] == second["id"]
    assert first["duplicate"] is False and second["duplicate"] is True


def test_only_the_sales_site_may_post(api):
    status, body, headers = call(api, "/api/orders", order(), origin="https://evil.example")
    assert status == 403
    assert "Access-Control-Allow-Origin" not in headers
    assert "code" not in body or body.get("code") != "server"


def test_the_sales_site_gets_its_cors_header_back(api):
    _, _, headers = call(api, "/api/orders", order(lead={"company": "코르스"}))
    assert headers.get("Access-Control-Allow-Origin") == ORIGIN


def test_a_preflight_from_the_sales_site_passes(api):
    status, _, headers = call(api, "/api/orders", method="OPTIONS")
    assert status == 204
    assert headers.get("Access-Control-Allow-Origin") == ORIGIN


def test_a_preflight_from_anywhere_else_is_refused(api):
    status, _, _ = call(api, "/api/orders", method="OPTIONS", origin="https://evil.example")
    assert status == 403


def test_reading_the_submit_endpoint_is_not_allowed(api):
    status, body, _ = call(api, "/api/orders", method="GET")
    assert status == 405 and body["ok"] is False


def test_an_unknown_address_is_a_plain_404(api):
    status, body, _ = call(api, "/api/nope", method="GET")
    assert status == 404 and "없는" in body["error"]


def test_a_wrong_content_type_is_refused(api):
    status, body, _ = call(api, "/api/orders", order(),
                           content_type="application/x-www-form-urlencoded")
    assert status == 415 and body["code"] == "content_type"


def test_broken_json_does_not_crash_the_worker(api):
    status, body, _ = call(api, "/api/orders", raw=b"{nope")
    assert status == 400 and body["code"] == "bad_json"
    assert call(api, "/health", method="GET", origin=None)[0] == 200


def test_an_enormous_payload_is_refused(api):
    payload = order(lead={"company": "큰거"})
    payload["notes"] = "가" * 100000
    status, body, _ = call(api, "/api/orders", payload)
    assert status == 413 and body["code"] == "too_large"


def test_sql_shaped_input_is_stored_as_plain_text(api):
    nasty = "'); DROP TABLE orders;--"
    status, body, _ = call(api, "/api/orders", order(lead={"company": nasty, "contact": "010-5555-1"}))
    assert status == 200 and body["ok"] is True
    # 표가 그대로 살아 있어야 합니다
    assert call(api, "/health", method="GET", origin=None)[1]["db"] == "ok"
    assert call(api, "/api/orders", order(lead={"company": "그다음", "contact": "010-5555-2"}))[0] == 200


def test_korean_and_long_text_survive(api):
    payload = order(lead={"company": "한글 업체명 · 특수문자 ✓", "contact": "010-6666-1",
                          "message": "줄바꿈\n포함 " + "가나다라마바사 " * 300})
    status, body, _ = call(api, "/api/orders", payload)
    assert status == 200 and body["ok"] is True


def test_the_error_body_never_leaks_internals(api):
    for status, body, _ in (
        call(api, "/api/orders", order(consent={"privacy": False})),
        call(api, "/api/orders", raw=b"{nope"),
        call(api, "/api/orders", order(), origin="https://evil.example"),
    ):
        blob = json.dumps(body, ensure_ascii=False)
        for leak in ("stack", "D1_ERROR", "sqlite", "at Object", "node_modules", "SELECT", "INSERT"):
            assert leak not in blob, f"{leak} in {blob[:120]}"
