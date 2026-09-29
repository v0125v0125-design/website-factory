"""ORDER FLOW V1 — 신청이 실제로 우리에게 도착하는지 지킨다.

이 파일이 지키는 것은 하나입니다. **보낸 척하지 않는다.**

  · 받는 곳이 설정되어 있지 않으면 버튼이 눌리지 않고 다른 연락 방법을 안내한다
  · 서버가 받았다고 답했을 때만 접수 화면이 뜬다
  · 실패하면 실패라고 말하고 입력을 지우지 않는다

그리고 첫 신청을 짧게 유지하는 것 — 처음부터 제작 자료를 다 받지 않습니다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from storefront.build import build, load

ROOT = Path(__file__).resolve().parent.parent
CHROMIUM = ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
            "/opt/pw-browsers/chromium/chrome-linux/chrome")
WIDTHS = {"desktop": (1440, 900), "tablet": (768, 1024), "mobile": (375, 812)}
PAGES = ("index.html", "order/index.html", "materials/index.html", "privacy/index.html")


@pytest.fixture(scope="module")
def data() -> dict:
    return load()


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    """설정이 비어 있는 그대로 — 실제 판매 페이지와 같은 상태."""
    return build(tmp_path_factory.mktemp("flow"))


@pytest.fixture(scope="module")
def wired(tmp_path_factory) -> Path:
    """받는 곳을 꽂은 상태. 실제 전송 흐름은 여기서 봅니다."""
    filled = load()
    filled["submission"] = {"provider": "post", "endpoint": "https://example.invalid/hook",
                            "successUrl": ""}
    return build(tmp_path_factory.mktemp("flow-wired"), filled)


def read(site: Path, name: str) -> str:
    return (site / name).read_text(encoding="utf-8")


# ── 화면이 있는가 ─────────────────────────────────────────────────
def test_all_four_pages_are_built(site):
    for page in PAGES:
        assert (site / page).is_file(), page
    assert (site / "assets" / "submit.js").is_file()


def test_the_sitemap_lists_the_new_pages(site):
    xml = read(site, "sitemap.xml")
    for folder in ("order", "materials", "privacy"):
        assert f"/{folder}/</loc>" in xml, folder


def test_every_page_carries_the_same_shell(site):
    for page in PAGES:
        html = read(site, page)
        assert "<title>" in html and 'class="hd' in html and 'class="ft' in html, page
        assert 'rel="canonical"' in html, page


# ── 첫 신청은 짧다 ────────────────────────────────────────────────
def test_the_first_step_asks_for_little(data):
    """처음부터 제작 자료를 다 받으면 고객이 지칩니다."""
    required = [f for f in data["order"]["fields"] if f.get("required")]
    assert len(required) <= 6, [f["name"] for f in required]
    names = {f["name"] for f in data["order"]["fields"]}
    assert {"company", "industry", "name", "contact"} <= names
    # 제작 자료용 칸이 첫 신청에 섞여 있으면 안 됩니다
    assert not (names & {"logo", "photos", "services", "strengths", "copy"})


def test_the_two_forms_have_different_jobs(data):
    order_names = {f["name"] for f in data["order"]["fields"]}
    material_ids = {s["id"] for s in data["material"]["sections"]}
    assert "photos" in material_ids and "photos" not in order_names
    assert "services" in material_ids


# ── 구성 자동 전달 ────────────────────────────────────────────────
def test_every_sales_cta_carries_the_picked_product(data):
    for product in data["products"]["items"]:
        href = product["cta"]["href"]
        assert href.startswith("order/?product="), href
        assert href.endswith(product["name"]), href


def test_the_order_page_offers_exactly_the_live_samples(site, data):
    block = read(site, "order/index.html").split('name="sample"')[1].split("</select>")[0]
    live = [s for s in data["samples"]["items"] if s.get("status") == "available"]
    assert live
    for sample in live:
        assert f'value="{sample["title"]}"' in block, sample["title"]
    for sample in data["samples"]["items"]:
        if sample.get("status") != "available":
            assert f'value="{sample["title"]}"' not in block, sample["title"]


def test_a_new_sample_shows_up_without_touching_the_form(tmp_path):
    """샘플을 늘리면 주문 화면 선택지도 저절로 늘어야 합니다."""
    extra = load()
    extra["samples"]["items"].append({
        "slug": "cafe-01", "category": "카페", "title": "CAFE 01", "subtitle": "동네 카페",
        "styleTags": ["따뜻한"], "previewUrl": "https://example.invalid/cafe-01/",
        "previewImage": "assets/samples/interior-01.webp",
        "product": "START", "status": "available",
    })
    html = (build(tmp_path / "grown", extra) / "order" / "index.html").read_text(encoding="utf-8")
    assert 'value="CAFE 01"' in html


# ── 받는 곳이 없으면 ──────────────────────────────────────────────
def test_without_an_endpoint_nothing_claims_to_be_received(site, data):
    assert not data["submission"]["provider"]
    for page in ("order/index.html", "materials/index.html"):
        html = read(site, page)
        assert 'data-role="closed"' in html, page
        for lie in ("접수되었습니다\"", "전송되었습니다"):
            assert lie not in html.split('id="done"')[0], page


def test_the_adapter_refuses_to_send_without_a_setting(site):
    js = read(site, "assets/submit.js")
    assert 'provider: ""' in js and 'endpoint: ""' in js
    assert "function ready()" in js
    assert "button.disabled = true" in js


def test_developer_words_never_reach_the_customer(site):
    for page in PAGES:
        markup = re.sub(r"<script.*?</script>", " ", read(site, page), flags=re.S)
        for word in ("provider", "endpoint", "formspree", "submission", "{{", "}}",
                     "Undefined", "localStorage"):
            assert word not in markup, f"{page}: {word}"


# ── 개인정보 ──────────────────────────────────────────────────────
def test_consent_is_required_on_both_forms(site):
    for page in ("order/index.html", "materials/index.html"):
        html = read(site, page)
        block = html.split('class="agree"')[1]
        assert 'name="agree"' in block and "required" in block.split("</label>")[0], page
        assert 'href="../privacy/"' in block, page


def test_the_consent_box_says_what_and_why(site, data):
    block = read(site, "order/index.html").split('class="agree"')[1].split("</details>")[0]
    for label in ("수집 항목", "이용 목적", "동의 거부"):
        assert label in block, label
    assert data["brand"]["legal"]["retentionPeriod"] in block


def test_the_privacy_page_hides_rows_it_cannot_fill(tmp_path):
    blank = load()
    blank["brand"]["legal"]["retentionPeriod"] = ""
    html = (build(tmp_path / "blank", blank) / "privacy" / "index.html").read_text(encoding="utf-8")
    assert "보유 기간" not in html


def test_no_invented_business_registration_is_shown(site, data):
    assert not data["brand"]["legal"]["registration"]
    for page in PAGES:
        assert "사업자등록번호" not in read(site, page), page


def test_real_business_details_do_appear_once_given(tmp_path):
    filled = load()
    filled["brand"]["legal"].update({
        "businessName": "테스트상회", "owner": "홍길동",
        "registration": "000-00-00000", "address": "서울 어딘가",
    })
    html = (build(tmp_path / "legal", filled) / "index.html").read_text(encoding="utf-8")
    assert "테스트상회" in html and "사업자등록번호 000-00-00000" in html


# ── 봇 막기 ───────────────────────────────────────────────────────
def test_both_forms_carry_a_honeypot(site):
    for page in ("order/index.html", "materials/index.html"):
        assert 'name="_gotcha"' in read(site, page), page


def test_the_adapter_rejects_instant_submissions(site):
    js = read(site, "assets/submit.js")
    assert "MIN_FILL_MS" in js
    assert re.search(r"MIN_FILL_MS\s*=\s*(\d+)", js).group(1) == "3000"


# ── 제작 자료 폼 ──────────────────────────────────────────────────
def test_the_material_form_has_a_block_for_every_master(site, data):
    html = read(site, "materials/index.html")
    live = [s["title"] for s in data["samples"]["items"] if s.get("status") == "available"]
    for title in live:
        assert f'data-for="{title}"' in html, title
        assert title in data["material"]["photoGuides"], f"{title} 사진 안내가 없습니다"
        assert title in data["material"]["industryBlocks"], f"{title} 업종 칸이 없습니다"


def test_the_photo_guide_is_written_per_industry(data):
    guides = data["material"]["photoGuides"]
    assert "기본" in guides
    assert any("전·후" in i["label"] for i in guides["CLEANING 01"]["items"])
    assert any("사업 영역" in i["label"] for i in guides["COMPANY 01"]["items"])
    for name, guide in guides.items():
        assert guide["note"], name
        assert guide["items"], name


def test_the_material_form_never_demands_fake_reviews(site):
    html = read(site, "materials/index.html")
    assert "후기가 없습니다" in html
    assert "실제로 받으신 후기만" in html


def test_upload_falls_back_to_a_link_when_nothing_receives_files(site, data):
    assert data["upload"]["mode"] == "link"
    html = read(site, "materials/index.html")
    assert 'name="photos.link"' in html
    assert 'type="file"' not in html


def test_switching_upload_mode_swaps_the_field(tmp_path):
    attached = load()
    attached["upload"]["mode"] = "attach"
    html = (build(tmp_path / "attach", attached) / "materials" / "index.html").read_text(encoding="utf-8")
    assert 'type="file"' in html
    assert 'name="photos.link"' not in html


# ── 브라우저 ──────────────────────────────────────────────────────
def _executable():
    return next((p for p in CHROMIUM if Path(p).exists()), None)


@pytest.fixture(scope="module")
def browser():
    pytest.importorskip("playwright.sync_api", reason="playwright 가 없으면 건너뜁니다")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        executable = _executable()
        try:
            instance = pw.chromium.launch(executable_path=executable) if executable else pw.chromium.launch()
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"크로미움을 띄울 수 없습니다: {exc}")
        yield instance
        instance.close()


STUB_OK = """
window.__sent = [];
window.fetch = function (url, opts) {
  window.__sent.push({url: url, body: opts.body});
  return Promise.resolve({ok: true, status: 200});
};
"""
STUB_FAIL = """
window.__sent = [];
window.fetch = function () { return Promise.resolve({ok: false, status: 500}); };
"""


def _open(browser, path: Path, width=1440, height=900, query="", stub=""):
    page = browser.new_page(viewport={"width": width, "height": height})
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(f"PAGEERROR: {e}"))
    if stub:
        page.add_init_script(stub)
    page.goto(path.as_uri() + query)
    page.wait_for_timeout(350)
    problems = [p for p in problems if "fonts.googleapis" not in p and "ERR_CERT" not in p
                and "ERR_NAME" not in p and "ERR_INTERNET" not in p]
    return page, problems


@pytest.mark.parametrize("name", list(WIDTHS))
@pytest.mark.parametrize("page_name", PAGES)
def test_every_page_holds_at_every_width(browser, site, name, page_name):
    width, height = WIDTHS[name]
    page, problems = _open(browser, site / page_name, width, height)
    doc_width = page.evaluate("() => document.documentElement.scrollWidth")
    assert doc_width <= width + 1, f"{page_name} @{name}: 가로 스크롤 ({doc_width})"
    assert not problems, f"{page_name} @{name}: {problems}"
    page.close()


@pytest.mark.parametrize("product,sample", [
    ("START", "INTERIOR_01"), ("BUSINESS", "CLEANING_01"), ("PREMIUM", "COMPANY_01"),
])
def test_the_picked_setup_arrives_in_the_order_form(browser, site, product, sample):
    page, _ = _open(browser, site / "order" / "index.html",
                    query=f"?product={product}&sample={sample}")
    assert page.input_value("#o-product") == product
    assert page.input_value("#o-sample") == sample.replace("_", " ")
    assert page.inner_text("#pick-product") == product
    premium_open = not page.evaluate("document.getElementById('premium').hidden")
    assert premium_open is (product == "PREMIUM")
    page.close()


def test_recommend_mode_asks_only_the_short_questions(browser, site):
    page, _ = _open(browser, site / "order" / "index.html", query="?mode=recommend")
    assert "추천" in page.inner_text("[data-role=heading]")
    assert page.evaluate("document.getElementById('pick').hidden")
    shown = page.eval_on_selector_all(".field:not([hidden]) [name]", "els => els.map(e => e.name)")
    assert "product" not in shown and "sample" not in shown
    assert {"company", "industry", "contact"} <= set(shown)
    page.close()


def test_a_closed_shop_locks_the_button_and_says_why(browser, site):
    page, _ = _open(browser, site / "order" / "index.html")
    assert page.evaluate("document.querySelector('#form-order [type=submit]').disabled")
    assert not page.evaluate("document.querySelector('[data-role=closed]').hidden")
    body = page.inner_text("body")
    assert "준비하는 중" in body
    for lie in ("접수되었습니다", "전송되었습니다"):
        assert lie not in body
    page.close()


def _fill_order(page):
    page.fill("#o-company", "테스트인테리어")
    page.fill("#o-industry", "인테리어")
    page.fill("#o-name", "홍길동")
    page.fill("#o-contact", "010-1234-5678")
    page.check("#o-agree")


def test_a_wired_shop_actually_posts_the_order(browser, wired):
    page, _ = _open(browser, wired / "order" / "index.html",
                    query="?product=START&sample=INTERIOR_01", stub=STUB_OK)
    assert not page.evaluate("document.querySelector('#form-order [type=submit]').disabled")

    page.click("#form-order [type=submit]")            # 빈 폼
    page.wait_for_timeout(150)
    assert page.evaluate("window.__sent.length") == 0

    _fill_order(page)
    page.uncheck("#o-agree")                            # 동의 없이
    page.click("#form-order [type=submit]")
    page.wait_for_timeout(150)
    assert page.evaluate("window.__sent.length") == 0
    page.check("#o-agree")

    page.click("#form-order [type=submit]")             # 너무 빠르게
    page.wait_for_timeout(150)
    assert page.evaluate("window.__sent.length") == 0
    assert not page.evaluate("document.querySelector('[data-role=too-fast]').hidden")

    page.wait_for_timeout(3000)
    page.click("#form-order [type=submit]")
    page.wait_for_timeout(400)
    sent = page.evaluate("window.__sent")
    assert len(sent) == 1
    payload = json.loads(sent[0]["body"])
    assert payload["kind"] == "order"
    assert payload["source"]["product"] == "START"
    assert payload["source"]["sample"] == "INTERIOR 01"
    assert payload["lead"]["company"] == "테스트인테리어"
    assert payload["consent"]["privacy"] is True

    done = page.inner_text("#done")
    assert "접수되었습니다" in done and "테스트인테리어" in done and "INTERIOR 01" in done
    for over in ("10분", "즉시"):
        assert over not in done

    # 다시 눌러도 두 번 가지 않는다
    page.evaluate("""() => { const f = document.getElementById('form-order');
      f.hidden = false; f.querySelector('[type=submit]').click(); }""")
    page.wait_for_timeout(300)
    assert page.evaluate("window.__sent.length") == 1
    page.close()


def test_a_filled_honeypot_sends_nothing(browser, wired):
    page, _ = _open(browser, wired / "order" / "index.html", stub=STUB_OK)
    _fill_order(page)
    page.wait_for_timeout(3100)
    page.evaluate("document.querySelector('[name=_gotcha]').value = 'bot'")
    page.click("#form-order [type=submit]")
    page.wait_for_timeout(300)
    assert page.evaluate("window.__sent.length") == 0
    page.close()


def test_a_failed_send_says_so_and_keeps_what_was_typed(browser, wired):
    page, _ = _open(browser, wired / "order" / "index.html", stub=STUB_FAIL)
    _fill_order(page)
    page.wait_for_timeout(3100)
    page.click("#form-order [type=submit]")
    page.wait_for_timeout(500)
    assert page.evaluate("document.getElementById('done').hidden")
    assert not page.evaluate("document.querySelector('[data-role=failure]').hidden")
    assert not page.evaluate("document.querySelector('#form-order [type=submit]').disabled")
    assert page.input_value("#o-company") == "테스트인테리어"
    page.close()


def test_material_rows_can_be_added_and_removed(browser, site):
    page, _ = _open(browser, site / "materials" / "index.html")
    assert page.eval_on_selector_all("[data-rows=services] [data-row]", "e => e.length") == 1
    page.click("[data-add=services]")
    page.click("[data-add=services]")
    page.wait_for_timeout(120)
    assert page.eval_on_selector_all("[data-rows=services] [data-row]", "e => e.length") == 3
    page.eval_on_selector("[data-rows=services] [data-row] .row__x", "el => el.click()")
    page.wait_for_timeout(120)
    assert page.eval_on_selector_all("[data-rows=services] [data-row]", "e => e.length") == 2
    numbers = page.eval_on_selector_all("[data-rows=services] .row__n", "e => e.map(x => x.textContent)")
    assert numbers == ["1", "2"], numbers
    page.close()


@pytest.mark.parametrize("design,label", [
    ("INTERIOR 01", "시공 사례"), ("CLEANING 01", "작업 사례"), ("COMPANY 01", "수행 사례"),
])
def test_the_material_form_follows_the_chosen_design(browser, site, design, label):
    page, _ = _open(browser, site / "materials" / "index.html")
    page.select_option("#m-design", design)
    page.wait_for_timeout(200)
    shown = page.eval_on_selector_all(".ind:not([hidden])", "e => e.map(x => x.getAttribute('data-for'))")
    assert shown == [design]
    assert label in page.inner_text(".ind:not([hidden])")
    assert page.inner_text("#guide-list").strip()
    page.close()


def test_a_long_form_survives_a_reload(browser, site):
    page, _ = _open(browser, site / "materials" / "index.html")
    page.select_option("#m-design", "CLEANING 01")
    page.fill("#m-who-company", "맑은집홈케어")
    page.eval_on_selector("[data-rows=services] [data-row] [data-field=name]",
                          "el => { el.value = '입주청소'; el.dispatchEvent(new Event('input', {bubbles: true})); }")
    page.wait_for_timeout(700)
    page.reload()
    page.wait_for_timeout(500)
    assert page.input_value("#m-who-company") == "맑은집홈케어"
    assert page.input_value("#m-design") == "CLEANING 01"
    names = page.eval_on_selector_all("[data-rows=services] [data-field=name]", "e => e.map(x => x.value)")
    assert "입주청소" in names
    page.close()


def test_sending_the_materials_clears_the_draft(browser, wired):
    page, _ = _open(browser, wired / "materials" / "index.html", stub=STUB_OK)
    page.select_option("#m-design", "COMPANY 01")
    page.fill("#m-who-company", "브릭온테크")
    page.fill("#m-who-name", "김담당")
    page.fill("#m-who-contact", "010-2222-3333")
    page.eval_on_selector("[data-rows=services] [data-row] [data-field=name]",
                          "el => { el.value = '자동화 설비'; el.dispatchEvent(new Event('input', {bubbles: true})); }")
    page.check("#m-agree")
    page.wait_for_timeout(3100)
    page.click("#form-material [type=submit]")
    page.wait_for_timeout(600)
    sent = page.evaluate("window.__sent")
    assert len(sent) == 1
    payload = json.loads(sent[0]["body"])
    assert payload["kind"] == "material"
    assert payload["lead"]["company"] == "브릭온테크"
    assert any(row.get("name") == "자동화 설비" for row in payload["services"])
    for key in ("company", "brand", "copy", "services", "strengths", "projects",
                "reviews", "faq", "seo", "notes", "consent"):
        assert key in payload, key
    assert not page.evaluate("document.getElementById('done').hidden")
    assert not page.evaluate("localStorage.getItem('wf-material-draft-v1')")
    page.close()
