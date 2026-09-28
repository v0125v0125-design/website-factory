"""판매 홈페이지 — 광고를 태워도 되는 상태인지 지킨다.

이 페이지는 우리 상품을 파는 화면입니다. 고객 템플릿(factory/)과 달리
여기서 거짓말을 하면 그대로 우리 신용이 됩니다. 그래서 세 가지를 못 박습니다.

  · 없는 후기와 없는 실적을 만들지 않는다
  · 받는 곳이 없는데 보낸 척하지 않는다
  · 스스로를 자동생성·공장형으로 부르지 않는다
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from storefront.build import DATA, build, jsonld, load  # noqa: E402

# 우리가 우리를 부르면 안 되는 말 — 고객이 보면 싼 물건이 된다
FORBIDDEN = ("자동생성", "자동 생성", "AI가", "공장형", "복붙", "찍어내", "무제한 수정")
# 손님에게 보이면 안 되는 개발자 말
DEV_WORDS = ("form_action", "--form-action", "storefront.json", "Undefined",
             "{{", "}}", "TODO", "lorem", "Lorem")
# 없는 실적을 있는 척하는 말
FAKE = ("누적 고객", "고객 만족도", "후기", "평점", "★", "재구매율")


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    return build(tmp_path_factory.mktemp("store"))


@pytest.fixture(scope="module")
def page(site: Path) -> str:
    return (site / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def data() -> dict:
    return load()


def _markup(html: str) -> str:
    """스크립트와 구조화 데이터를 뺀 실제 화면 태그."""
    return re.sub(r"<script.*?</script>", " ", html, flags=re.S)


def _text(html: str) -> str:
    """태그를 걷어낸 사람이 읽는 글."""
    body = html.split("<body", 1)[1]
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S)
    return re.sub(r"<[^>]+>", " ", body)


# ── 지어지는가 ────────────────────────────────────────────────────
def test_it_builds_a_whole_static_site(site):
    assert (site / "index.html").is_file()
    assert (site / "assets" / "styles.css").is_file()
    assert (site / "assets" / "samples" / "interior-01.webp").is_file()
    assert (site / "robots.txt").is_file()
    assert (site / "sitemap.xml").is_file()


def test_the_page_stays_light(site):
    total = sum(f.stat().st_size for f in site.rglob("*") if f.is_file())
    assert total < 400 * 1024, f"{total/1024:.0f}KB"


def test_no_template_leftovers(page):
    markup = _markup(page)
    for word in DEV_WORDS:
        assert word not in markup, word


# ── 거짓말하지 않는가 ─────────────────────────────────────────────
def test_we_never_call_ourselves_a_factory(page):
    text = _text(page)
    for word in FORBIDDEN:
        assert word not in text, word


def test_no_invented_reviews_or_numbers(page):
    text = _text(page)
    for word in FAKE:
        assert word not in text, word
    assert "aggregateRating" not in page
    assert '"review"' not in page


def test_the_form_never_pretends_to_have_sent_anything(page, data):
    """받는 곳이 없다. 그러면 접수되었다고 말하지 않는다."""
    assert "<form" in page
    assert "action=" not in page.split("<footer")[0].split("<form")[1].split(">")[0]
    for lie in ("전송되었습니다", "접수되었습니다", "신청이 완료", "곧 연락드리겠습니다"):
        assert lie not in page, lie
    assert "아직 전송되지 않았습니다" in page or data["brand"]["contact"]["phone"]


def test_missing_contact_channels_show_no_dead_buttons(page, data):
    """연락처가 비어 있으면 눌러도 아무 데도 안 가는 버튼을 놓지 않는다."""
    if not any(data["brand"]["contact"].get(k) for k in ("phone", "kakao", "email")):
        markup = _markup(page)
        assert 'href="tel:"' not in markup
        assert "mailto:" not in markup


def test_filled_contact_channels_do_appear(tmp_path):
    filled = load()
    filled["brand"]["contact"] = {"phone": "1544-1234", "kakao": "https://pf.kakao.com/_test",
                                  "email": "hello@example.test"}
    html = (build(tmp_path / "wired", filled) / "index.html").read_text(encoding="utf-8")
    assert 'href="tel:15441234"' in html
    assert "https://pf.kakao.com/_test" in html
    assert "mailto:hello@example.test" in html
    assert "아직 전송되지 않았습니다" not in html


# ── 파는 데 필요한 것이 다 있는가 ─────────────────────────────────
def test_every_price_is_written_on_the_page(page, data):
    for product in data["products"]["items"]:
        assert product["price"] in page
        assert product["name"] in page
    assert "부가세 별도" in page


def test_every_faq_is_rendered(page, data):
    for item in data["faq"]["items"]:
        assert item["q"] in page
        assert item["a"] in page
    assert page.count('class="faq__row"') == len(data["faq"]["items"])


def test_every_process_step_is_rendered(page, data):
    for step in data["process"]["steps"]:
        assert step["title"] in page
    assert page.count('class="step"') == len(data["process"]["steps"])


def test_the_scope_says_what_is_not_included(page, data):
    for word in data["scope"]["excluded"]:
        assert word in page
    assert data["scope"]["note"] in page


def test_available_samples_open_in_a_new_tab(page, data):
    for sample in data["samples"]["items"]:
        if sample.get("status") != "available":
            assert sample["title"] in page          # 준비 중이라고 적되 링크는 걸지 않는다
            continue
        assert sample["previewUrl"] in page
    opened = re.findall(r'<a[^>]+target="_blank"[^>]*>', page)
    assert opened, "샘플을 새 창으로 여는 링크가 없다"
    for tag in opened:
        assert 'rel="noopener"' in tag, tag


def test_preparing_samples_are_marked_not_linked(page, data):
    preparing = [s for s in data["samples"]["items"] if s.get("status") != "available"]
    assert page.count('class="card__soon"') == len(preparing)
    assert page.count("chip--soon") == len(preparing)


def test_the_anchors_the_buttons_point_at_all_exist(page):
    targets = set(re.findall(r'href="#([a-z-]+)"', page))
    ids = set(re.findall(r'id="([a-z-]+)"', page))
    assert targets - ids == set(), targets - ids


# ── 검색과 공유 ───────────────────────────────────────────────────
def test_search_engines_are_blocked_while_this_is_a_review_address(site, page, data):
    assert data["seo"]["noindex"] is True
    assert 'content="noindex, nofollow"' in page
    assert "Disallow: /" in (site / "robots.txt").read_text(encoding="utf-8")


def test_turning_noindex_off_opens_robots_and_sitemap(tmp_path):
    public = load()
    public["seo"]["noindex"] = False
    out = build(tmp_path / "public", public)
    robots = (out / "robots.txt").read_text(encoding="utf-8")
    assert "Allow: /" in robots and "Sitemap:" in robots
    assert 'content="index, follow"' in (out / "index.html").read_text(encoding="utf-8")


def test_canonical_and_og_point_at_this_address(page, data):
    base = data["urls"]["self"]
    assert f'rel="canonical" href="{base}"' in page
    assert f'property="og:url" content="{base}"' in page
    assert f'content="{base}{data["seo"]["ogImage"]}"' in page


def test_structured_data_matches_what_the_page_says(data):
    parsed = json.loads(jsonld(data).replace("<\\/", "</"))
    kinds = [node["@type"] for node in parsed["@graph"]]
    assert kinds == ["WebSite", "Service", "FAQPage"]
    offers = parsed["@graph"][1]["offers"]
    assert [o["price"] for o in offers] == ["169000", "349000", "790000"]
    assert all(o["priceCurrency"] == "KRW" for o in offers)
    assert len(parsed["@graph"][2]["mainEntity"]) == len(data["faq"]["items"])


def test_the_script_tag_cannot_be_broken_out_of(data):
    assert "</" not in jsonld(data)


# ── 한 장에서만 고친다 ────────────────────────────────────────────
def test_all_copy_lives_in_one_file(tmp_path):
    """브랜드명을 한 곳에서 바꾸면 화면이 따라와야 한다."""
    renamed = load()
    renamed["brand"]["name"] = "테스트상호"
    renamed["brand"]["shortName"] = "TS"
    html = (build(tmp_path / "renamed", renamed) / "index.html").read_text(encoding="utf-8")
    assert '<span class="hd__mark">TS</span>테스트상호' in html
    assert '<p class="ft__brand">테스트상호</p>' in html
    # seo.title 은 검색 결과에 그대로 나가는 문장이라 따로 적습니다 — 함께 고쳐야 합니다.
    assert renamed["seo"]["title"] == load()["seo"]["title"]


def test_the_theme_colour_comes_only_from_the_data(tmp_path):
    themed = load()
    themed["theme"]["accent"] = "#123456"
    css = (build(tmp_path / "themed", themed) / "assets" / "styles.css").read_text(encoding="utf-8")
    assert "--accent: #123456" in css


def test_the_data_file_is_valid_json_with_the_blocks_the_page_needs():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for key in ("brand", "theme", "urls", "seo", "nav", "hero", "reasons", "samples",
                "products", "scope", "process", "trust", "faq", "order", "quote",
                "advice", "closing"):
        assert key in data, key


# ── 미리보기 묶음에 실린다 ────────────────────────────────────────
def test_the_preview_bundle_carries_the_storefront(tmp_path):
    out = tmp_path / "_site"
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_previews.py"), str(out)],
                   cwd=ROOT, check=True, capture_output=True, text=True)
    store = out / "store"
    assert {child.name for child in store.iterdir()} == {"index.html", "assets"}
    html = (store / "index.html").read_text(encoding="utf-8")
    assert 'content="noindex, nofollow"' in html
    assert 'href="store/"' in (out / "index.html").read_text(encoding="utf-8")


def test_the_preview_bundle_rewrites_the_storefront_address(tmp_path, monkeypatch):
    monkeypatch.setenv("PREVIEW_BASE", "https://preview.example.test/factory")
    out = tmp_path / "_site"
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_previews.py"), str(out)],
                   cwd=ROOT, check=True, capture_output=True, text=True,
                   env={**dict(__import__("os").environ),
                        "PREVIEW_BASE": "https://preview.example.test/factory"})
    html = (out / "store" / "index.html").read_text(encoding="utf-8")
    assert 'href="https://preview.example.test/factory/store/"' in html
    assert "https://preview.example.test/factory/gonggan-interior/" in html
    assert "v0125v0125-design.github.io" not in html
