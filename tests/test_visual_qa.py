"""브라우저로 직접 확인하는 검사.

playwright 가 깔려 있을 때만 돈다 (`pip install playwright`). 없으면 건너뛴다 —
공장 자체는 브라우저 없이도 돌아야 하기 때문이다.

여기서 보는 것은 사람이 눈으로 보던 것들이다.
가로 스크롤이 생겼는지, 콘솔에 오류가 났는지, 사진이 실제로 떴는지,
좁은 화면에서 전화 버튼이 손끝에 있는지, 크게 보기가 열리고 닫히는지.
"""

import json
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="playwright 가 없으면 건너뜁니다")
from playwright.sync_api import sync_playwright  # noqa: E402

from factory.pipeline import build_from_file  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
CHROMIUM = [
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/opt/pw-browsers/chromium/chrome-linux/chrome",
]
WIDTHS = {"desktop": (1440, 900), "tablet": (768, 1024), "mobile": (375, 812)}


def _executable() -> str | None:
    return next((path for path in CHROMIUM if Path(path).exists()), None)


@pytest.fixture(scope="module")
def page_url(tmp_path_factory):
    result = build_from_file(
        EXAMPLES / "master-interior-01.json",
        tmp_path_factory.mktemp("visual"),
        offline=True,
        clean=True,
    )
    return (result.out_dir / "index.html").as_uri()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        executable = _executable()
        try:
            instance = pw.chromium.launch(executable_path=executable) if executable else pw.chromium.launch()
        except Exception as exc:  # pragma: no cover - 브라우저가 없는 환경
            pytest.skip(f"크로미움을 띄울 수 없습니다: {exc}")
        yield instance
        instance.close()


def _open(browser, url, width, height):
    page = browser.new_page(viewport={"width": width, "height": height})
    problems: list[str] = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(f"PAGEERROR: {e}"))
    page.goto(url)
    page.wait_for_timeout(400)
    # 인터넷이 막힌 곳에서는 구글 폰트를 못 받는다 — 그건 페이지 잘못이 아니다.
    problems = [p for p in problems if "fonts.googleapis" not in p and "ERR_CERT" not in p
                and "ERR_NAME" not in p and "ERR_INTERNET" not in p]
    return page, problems


@pytest.mark.parametrize("name", list(WIDTHS))
def test_no_sideways_scroll_and_no_console_errors(browser, page_url, name):
    width, height = WIDTHS[name]
    page, problems = _open(browser, page_url, width, height)
    doc_width = page.evaluate("() => document.documentElement.scrollWidth")
    assert doc_width <= width + 1, f"{name}: 가로 스크롤이 생겼습니다 ({doc_width} > {width})"
    assert not problems, f"{name}: {problems}"
    page.close()


@pytest.mark.parametrize("name", list(WIDTHS))
def test_every_photo_actually_loads(browser, page_url, name):
    width, height = WIDTHS[name]
    page, _ = _open(browser, page_url, width, height)
    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(600)
    broken = page.evaluate(
        "() => [...document.images]"
        ".filter(i => i.offsetParent !== null || i.closest('.hero'))"
        ".filter(i => !i.complete || i.naturalWidth === 0)"
        ".map(i => i.getAttribute('src') || '(src 없음)')"
    )
    assert not broken, f"{name}: 깨진 이미지 {broken}"
    page.close()


def test_phone_and_kakao_are_within_reach_on_a_phone(browser, page_url):
    page, _ = _open(browser, page_url, 375, 812)
    bar = page.query_selector(".mbar")
    assert bar and bar.is_visible(), "모바일에서 하단 문의 바가 보이지 않습니다"
    box = bar.bounding_box()
    assert box["y"] + box["height"] <= 812 + 1        # 화면 안에 붙어 있다
    assert box["height"] >= 44                        # 손가락으로 누를 만한 크기
    assert page.query_selector(".mh__toggle").is_visible()
    page.close()


def test_the_desktop_menu_fits_in_one_row(browser, page_url):
    page, _ = _open(browser, page_url, 1440, 900)
    tops = page.eval_on_selector_all(
        ".mh__list li", "els => els.filter(e => e.offsetParent).map(e => e.getBoundingClientRect().top)"
    )
    assert tops, "데스크톱 메뉴가 비어 있습니다"
    assert max(tops) - min(tops) < 4, "메뉴가 두 줄로 접혔습니다 — 항목이 너무 많습니다"
    assert not page.query_selector(".mbar").is_visible()
    page.close()


def test_the_mobile_menu_opens_and_closes(browser, page_url):
    page, _ = _open(browser, page_url, 375, 812)
    menu = page.query_selector("#site-menu")
    before = menu.bounding_box()["y"]
    page.click(".mh__toggle")
    page.wait_for_timeout(400)
    assert menu.bounding_box()["y"] > before, "메뉴가 내려오지 않았습니다"
    assert page.get_attribute(".mh__toggle", "aria-expanded") == "true"
    page.close()


def test_project_photos_open_large_and_close_with_escape(browser, page_url):
    page, _ = _open(browser, page_url, 1440, 900)
    page.click(".pj__open")
    page.wait_for_timeout(300)
    assert page.query_selector("#lightbox").is_visible()
    assert page.get_attribute("#lb-img", "src")
    page.click("[data-next]")
    page.wait_for_timeout(200)
    assert "2 / 2" in page.inner_text("#lb-count")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    assert not page.query_selector("#lightbox").is_visible()
    page.close()


def test_category_chips_narrow_the_grid(browser, page_url):
    page, _ = _open(browser, page_url, 1440, 900)
    shown = lambda: page.eval_on_selector_all(  # noqa: E731
        "#pj-grid .pj__cell", "els => els.filter(e => !e.hidden).length"
    )
    total = shown()
    page.click('.pj__chip[data-filter="상가"]')
    page.wait_for_timeout(200)
    assert 0 < shown() < total
    page.click('.pj__chip[data-filter="*"]')
    page.wait_for_timeout(200)
    assert shown() == total
    page.close()


# ── 양산한 세 고객도 같은 눈으로 본다 ─────────────────────────────

CUSTOMERS = EXAMPLES / "customers"


@pytest.fixture(scope="module")
def customer_urls(tmp_path_factory):
    root = tmp_path_factory.mktemp("visual-customers")
    urls = {}
    for path in sorted(CUSTOMERS.glob("*.json")):
        # 이 파일은 인테리어 마스터를 보는 눈이다. 청소 마스터는 제 파일에서 본다.
        if json.loads(path.read_text(encoding="utf-8")).get("template") != "master-interior-01":
            continue
        result = build_from_file(path, root / path.stem, offline=True, clean=True)
        urls[path.stem] = (result.out_dir / "index.html").as_uri()
    return urls


@pytest.mark.parametrize("width,height", [(1440, 900), (768, 1024), (375, 812)])
def test_each_customer_site_holds_at_every_width(browser, customer_urls, width, height):
    for name, url in customer_urls.items():
        page, problems = _open(browser, url, width, height)
        doc_width = page.evaluate("() => document.documentElement.scrollWidth")
        assert doc_width <= width + 1, f"{name} @{width}: 가로 스크롤 ({doc_width})"
        assert not problems, f"{name} @{width}: {problems}"
        # 아래쪽 사진은 지연 로딩이므로 끝까지 내려가 본 다음에 센다
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(700)
        broken = page.evaluate(
            "() => [...document.images].filter(i => i.offsetParent !== null || i.closest('.hero'))"
            ".filter(i => !i.complete || i.naturalWidth === 0).length"
        )
        assert broken == 0, f"{name} @{width}: 깨진 사진 {broken}장"
        page.close()


def test_the_quick_contact_rail_never_covers_the_content(browser, customer_urls):
    for name, url in customer_urls.items():
        page, _ = _open(browser, url, 1440, 900)
        gap = page.evaluate("""() => {
          const rail = document.querySelector('.rail');
          const card = document.querySelector('.strip__card') || document.querySelector('.wrap');
          if (!rail || getComputedStyle(rail).display === 'none') return 999;
          return Math.round(rail.getBoundingClientRect().left - card.getBoundingClientRect().right);
        }""")
        assert gap >= 0, f"{name}: 상담 레일이 본문을 덮습니다 ({gap}px)"
        page.close()


def test_layout_variations_render_differently(browser, customer_urls):
    seen = set()
    for name, url in customer_urls.items():
        page, _ = _open(browser, url, 1440, 900)
        shape = page.evaluate("""() => {
          const hero = document.querySelector('.hero');
          const first = document.querySelector('#pj-grid .pj__cell');
          const r = first ? first.getBoundingClientRect() : {width:0, height:0};
          return {align: getComputedStyle(hero).textAlign,
                  cell: Math.round(r.width) + 'x' + Math.round(r.height)};
        }""")
        seen.add((shape["align"], shape["cell"]))
        page.close()
    assert len(seen) >= 2, f"세 고객의 화면 모양이 사실상 같습니다: {seen}"


# ── 청소 마스터도 같은 눈으로 본다 ────────────────────────────────
# 인테리어와 화면이 다르므로 보는 것도 다르다: 비교 손잡이, 서비스 지역,
# 그리고 두 마스터가 나란히 놓였을 때 같은 사이트로 보이지 않는지.

CLEANING = EXAMPLES / "customers" / "d-bareungyeol.json"


@pytest.fixture(scope="module")
def cleaning_url(tmp_path_factory):
    result = build_from_file(
        CLEANING, tmp_path_factory.mktemp("visual-cleaning"), offline=True, clean=True
    )
    return (result.out_dir / "index.html").as_uri()


@pytest.mark.parametrize("name", list(WIDTHS))
def test_cleaning_holds_at_every_width(browser, cleaning_url, name):
    width, height = WIDTHS[name]
    page, problems = _open(browser, cleaning_url, width, height)
    doc_width = page.evaluate("() => document.documentElement.scrollWidth")
    assert doc_width <= width + 1, f"{name}: 가로 스크롤 ({doc_width} > {width})"
    assert not problems, f"{name}: {problems}"
    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(800)
    broken = page.evaluate(
        "() => [...document.images].filter(i => !i.complete || i.naturalWidth === 0).length"
    )
    assert broken == 0, f"{name}: 깨진 사진 {broken}장"
    page.close()


@pytest.mark.parametrize("name", list(WIDTHS))
def test_the_before_after_handle_actually_moves(browser, cleaning_url, name):
    width, height = WIDTHS[name]
    page, _ = _open(browser, cleaning_url, width, height)
    before = page.evaluate(
        "() => getComputedStyle(document.querySelector('.ba__view')).getPropertyValue('--pos').trim()"
    )
    page.eval_on_selector(".ba__range", "el => { el.value = 15; el.dispatchEvent(new Event('input')); }")
    page.wait_for_timeout(120)
    after = page.evaluate(
        "() => getComputedStyle(document.querySelector('.ba__view')).getPropertyValue('--pos').trim()"
    )
    assert before == "50%" and after == "15%", f"{name}: {before} → {after}"
    # 손잡이는 사진 위 전체를 덮어야 손가락으로 끌 수 있다
    box = page.evaluate("""() => {
      const r = document.querySelector('.ba__range').getBoundingClientRect();
      const v = document.querySelector('.ba__view').getBoundingClientRect();
      return Math.round(r.width) === Math.round(v.width) && Math.round(r.height) === Math.round(v.height);
    }""")
    assert box, f"{name}: 비교 손잡이가 사진을 덮지 않습니다"
    page.close()


def test_the_estimate_is_always_one_tap_away_on_a_phone(browser, cleaning_url):
    page, _ = _open(browser, cleaning_url, 375, 812)
    bar = page.evaluate("""() => {
      const b = document.querySelector('.cbar');
      if (!b || getComputedStyle(b).display === 'none') return null;
      const r = b.getBoundingClientRect();
      return {bottom: Math.round(window.innerHeight - r.bottom), links: b.querySelectorAll('a').length,
              tall: Math.round(r.height)};
    }""")
    assert bar, "휴대폰 화면에 하단 문의 바가 없습니다"
    assert bar["bottom"] == 0 and bar["links"] == 3
    assert bar["tall"] >= 44, f"손끝에 닿기엔 낮습니다 ({bar['tall']}px)"
    page.close()


def test_the_two_masters_do_not_look_like_the_same_site(browser, page_url, cleaning_url):
    """색만 바꾼 같은 템플릿이면 둘을 나란히 팔 수 없다."""
    shapes = {}
    for name, url in (("interior", page_url), ("cleaning", cleaning_url)):
        page, _ = _open(browser, url, 1440, 900)
        shapes[name] = page.evaluate("""() => {
          const head = document.querySelector('header');
          const hero = document.querySelector('.hero, .hr');
          const rail = document.querySelector('.rail');
          return {
            headClass: head.className.split(' ')[0],
            heroClass: hero.className.split(' ')[0],
            heroHeight: Math.round(hero.getBoundingClientRect().height),
            heroBg: getComputedStyle(hero).backgroundColor,
            hasRail: !!(rail && getComputedStyle(rail).display !== 'none'),
            sections: [...document.querySelectorAll('main section[id]')].map(s => s.id),
          };
        }""")
        page.close()
    assert shapes["interior"]["headClass"] != shapes["cleaning"]["headClass"]
    assert shapes["interior"]["heroClass"] != shapes["cleaning"]["heroClass"]
    assert shapes["interior"]["hasRail"] and not shapes["cleaning"]["hasRail"]
    only_cleaning = set(shapes["cleaning"]["sections"]) - set(shapes["interior"]["sections"])
    assert {"beforeafter", "area"} <= only_cleaning, only_cleaning
    # 첫 화면의 덩치가 크게 다르다 — 인테리어는 사진으로 덮고, 청소는 글로 바로 말한다
    assert abs(shapes["interior"]["heroHeight"] - shapes["cleaning"]["heroHeight"]) > 120
