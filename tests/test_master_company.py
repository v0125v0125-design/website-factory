"""MASTER_COMPANY_01 — 기업·B2B 마스터를 지킨다.

인테리어는 결과 이미지를, 청소는 불안 해소를 팝니다. 기업은 **신뢰**를 팝니다.
그래서 여기서 보는 것도 다릅니다.

  · 회사 개요 숫자가 **이 페이지에서 직접 셀 수 있는 것**인가
  · 수행 사례가 표로 읽히는가 · 실제 발주처 이름을 흘리지 않는가
  · 연혁·인증은 고객이 줄 때만 서는가 (공장이 만들어 내지 않는가)
  · 후기가 없어도 화면이 완성되는가
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from factory import schema
from factory.intake import load_brief, parse_brief
from factory.pipeline import build, build_from_file

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = "master-company-01"
BRIEF = ROOT / "examples" / "customers" / "e-brickon.json"
SECTIONS = ("overview", "services", "strengths", "gallery", "projects",
            "process", "about", "faq", "contact")


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(BRIEF.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return build_from_file(BRIEF, tmp_path_factory.mktemp("company") / "site", offline=True)


@pytest.fixture(scope="module")
def page(built) -> str:
    return (built.out_dir / "index.html").read_text(encoding="utf-8")


def make(data: dict, out: Path, **kw):
    brief, _ = parse_brief(data, source_path=str(BRIEF))
    return build(brief, out, offline=True, clean=True, **kw)


def html_of(result) -> str:
    return (result.out_dir / "index.html").read_text(encoding="utf-8")


# ── 지어지는가 ────────────────────────────────────────────────────
def test_the_company_master_is_the_one_that_gets_picked(built):
    assert built.plan.template.id == TEMPLATE
    assert built.plan.brief.business.industry == "manufacturing"


def test_every_section_lands_on_the_page(page):
    for name in SECTIONS:
        assert f'id="{name}"' in page, name


def test_the_page_is_complete_without_reviews(built, page):
    """B2B 샘플에는 후기를 싣지 않는다. 그래도 화면이 비어 보이면 안 된다."""
    assert built.plan.brief.testimonials == []
    assert 'id="testimonials"' not in page
    assert "후기" not in page
    assert built.plan.content.meta["todo"] == []
    assert built.plan.content.meta["skipped"] == ["testimonials: 받은 후기가 없어 뺐습니다"]


def test_reviews_do_appear_when_a_customer_gives_them(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["reviews"] = [{"quote": "납기를 지켰습니다.", "이름": "○○산업", "역할": "생산팀"}]
    html = html_of(make(data, tmp_path / "voices"))
    assert 'id="testimonials"' in html
    assert html.count('class="vo__card"') == 1


def test_the_page_stays_light(built):
    total = sum(f.stat().st_size for f in built.out_dir.rglob("*") if f.is_file())
    assert total < 400 * 1024, f"{total/1024:.0f}KB"


# ── 회사 개요 — 셀 수 있는 것만 ───────────────────────────────────
def test_the_overview_numbers_are_all_countable_on_the_page(page, raw):
    """'누적 고객 1,240곳' 은 확인할 길이 없다. 그런 숫자는 공장이 만들지 않는다."""
    band = page.split('id="overview"')[1].split("</section>")[0]
    assert f">{len(raw['services'])}</b>" in band          # 사업 영역 수
    assert f">{len(raw['process'])}</b>" in band           # 진행 단계 수
    industries = {p["분류"] for p in raw["projects"]}
    assert f">{len(industries)}</b>" in band               # 적용 산업 수
    assert raw["company"]["founded"] in band               # 설립연도는 고객이 준 사실
    for lie in ("누적", "만족도", "불량률", "매출", "업력"):
        assert lie not in band, lie


def test_the_overview_counts_follow_the_data(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["services"] = data["services"][:2]
    data["process"] = data["process"][:3]
    band = html_of(make(data, tmp_path / "count")).split('id="overview"')[1].split("</section>")[0]
    assert ">2</b>" in band and ">3</b>" in band


def test_the_overview_drops_when_there_is_nothing_to_count(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["company"].pop("founded")
    data["services"] = []
    data["process"] = []
    data["projects"] = []
    data["seo"].pop("지역명")
    html = html_of(make(data, tmp_path / "nocount"))
    assert 'id="overview"' not in html
    assert 'id="contact"' in html


# ── 수행 사례 ─────────────────────────────────────────────────────
def test_references_read_as_a_table(page, raw):
    assert page.count('class="rf__row"') == len(raw["projects"])
    head = page.split('class="rf__head"')[1].split("</div>")[0]
    for column in ("적용 산업", "프로젝트", "수행 범위"):
        assert column in head


def test_no_real_company_names_are_borrowed(page):
    """'삼성전자 납품' 같은 차용은 가상 샘플에서 절대 하지 않는다."""
    for brand in ("삼성", "현대", "LG", "SK", "포스코", "한화", "두산", "기아", "LS", "효성"):
        assert brand not in page, brand
    assert "비밀유지" in page          # 발주처를 적지 않는 이유를 화면에서 밝힌다


@pytest.mark.parametrize("count", [0, 1, 8])
def test_any_number_of_references_still_lays_out(tmp_path, raw, count):
    data = copy.deepcopy(raw)
    base = data["projects"]
    data["projects"] = [dict(base[i % len(base)], name=f"사례 {i + 1}") for i in range(count)]
    html = html_of(make(data, tmp_path / f"ref{count}"))
    assert html.count('class="rf__row"') == count
    assert ('id="projects"' in html) is (count > 0)


def test_a_reference_without_a_photo_still_shows(tmp_path, raw):
    data = copy.deepcopy(raw)
    for row in data["projects"]:
        row.pop("사진", None)
    html = html_of(make(data, tmp_path / "nopic"))
    assert html.count('class="rf__row"') == len(data["projects"])
    assert data["projects"][0]["name"] in html


# ── 연혁 · 인증은 만들어 내지 않는다 ──────────────────────────────
def test_certifications_stay_absent_until_a_customer_gives_them(page, raw):
    assert "credentials" not in json.dumps(raw, ensure_ascii=False)
    assert "인증" not in page
    assert "ISO" not in page


def test_certifications_render_once_given(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["about"]["인증"] = [["ISO 9001", "2021.03"], ["보유 설비", "CNC 밀링 4대"]]
    html = html_of(make(data, tmp_path / "cert"))
    assert "인증 · 보유 설비" in html
    assert "ISO 9001" in html and "CNC 밀링 4대" in html


def test_history_renders_as_a_timeline(page, raw):
    for when, what in raw["about"]["연혁"]:
        assert when in page and what in page
    assert page.count('class="co__hist"') == 1


def test_history_disappears_when_empty(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["about"].pop("연혁")
    html = html_of(make(data, tmp_path / "nohist"))
    assert 'class="co__hist"' not in html
    assert 'class="co__facts"' in html      # 회사 개요는 남는다


# ── 재료가 모자라도 버티는가 ──────────────────────────────────────
@pytest.mark.parametrize("count", [1, 4, 10])
def test_any_number_of_business_areas_lays_out(tmp_path, raw, count):
    data = copy.deepcopy(raw)
    base = data["services"]
    data["services"] = [dict(base[i % len(base)], name=f"사업 {i + 1}") for i in range(count)]
    html = html_of(make(data, tmp_path / f"area{count}"))
    assert html.count('class="ba__card"') == count


def test_no_faq_drops_the_section(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["faq"] = []
    html = html_of(make(data, tmp_path / "nofaq"))
    assert 'id="faq"' not in html
    assert 'id="contact"' in html


def test_a_long_company_name_and_headline_do_not_spill(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["company"]["name"] = "주식회사 브릭온테크놀로지산업기계설비 충남지점"
    data["hero"]["headline"] = "설계부터 제작 검사 납품 사후대응까지 한 곳에서 " * 2
    html = html_of(make(data, tmp_path / "long"))
    assert data["company"]["name"] in html
    assert "hr__title" in html


def test_without_a_logo_the_initial_stands_in(page, raw):
    assert "brand" not in raw or not raw.get("brand", {}).get("logo")
    assert 'class="ch__mark"' in page
    assert "<img class=\"ch__logo\"" not in page


def test_a_logo_replaces_the_initial(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["brand"] = {"logo_image": "examples/photos/company/product-2.svg", "logo_text": "브릭온테크"}
    html = html_of(make(data, tmp_path / "logo"))
    assert 'class="ch__logo"' in html
    assert 'class="ch__mark"' not in html


def test_without_a_phone_no_dead_tel_link(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["contact"].pop("phone")
    html = html_of(make(data, tmp_path / "nophone"))
    assert "tel:" not in html
    assert 'id="contact"' in html


def test_b2b_pages_carry_no_consumer_chrome(page):
    """기업형에 카카오톡 상담이나 하단 고정 바를 달지 않는다."""
    for word in ("카카오톡", "class=\"cbar\"", "class=\"mbar\"", "class=\"rail\""):
        assert word not in page, word


def test_every_anchor_the_buttons_point_at_exists(page):
    targets = {m for m in re.findall(r'href="#([a-z-]+)"', page)}
    ids = {m for m in re.findall(r'id="([a-z-]+)"', page)}
    assert targets - ids == set(), targets - ids


# ── 거짓말하지 않는가 ─────────────────────────────────────────────
def test_no_developer_words_reach_the_customer(page):
    for word in ("form_action", "--form-action", "지정하십시오", "build_report",
                 "납품메모", "{{", "}}", "Undefined"):
        assert word not in page, word


def test_no_sample_banner_inside_the_site(page):
    """샘플 사이트 안에서는 '가상 페이지입니다' 배너를 달지 않는다."""
    for word in ("가상 페이지", "데모 업체", "포트폴리오 샘플", "샘플 사이트", "DEMO"):
        assert word not in page, word


def test_the_form_says_what_is_true_when_nothing_receives_it(page):
    form = page.split("<form")[1].split(">")[0]
    assert 'data-noaction="1"' in form
    note = page.split('class="ct__sent"')[1].split("</p>")[0]
    assert "전화" in note and "--form" not in note
    for lie in ("접수되었습니다", "전송되었습니다", "감사합니다"):
        assert lie not in page, lie


def test_a_real_form_target_turns_the_notice_off(tmp_path, raw):
    html = html_of(make(raw, tmp_path / "wired", form_action="https://formspree.io/f/abcd"))
    assert 'action="https://formspree.io/f/abcd"' in html
    assert "data-noaction" not in html.split("<form")[1].split(">")[0]
    assert 'class="ct__sent"' not in html


def test_the_sample_contact_reaches_no_real_third_party(raw):
    contact = raw["contact"]
    assert contact["phone"].endswith("0000")       # 배정되지 않는 끝자리
    assert "email" not in contact and "이메일" not in contact
    assert "kakao" not in contact and "카카오톡" not in contact
    # 주소는 읍·면 단위까지만 — 실제 건물을 특정하지 않는다
    assert not re.search(r"\d+(번길|길|로\s*\d)", contact["address"]), contact["address"]
    assert "가상" in raw["_주의"]


# ── SEO ───────────────────────────────────────────────────────────
def test_the_search_text_names_what_the_company_does_and_where(page, raw):
    assert f'<title>{raw["seo"]["title"]}</title>' in page
    assert raw["seo"]["description"] in page
    for word in raw["seo"]["키워드"]:
        assert word in page
    data = json.loads(page.split('<script type="application/ld+json">')[1].split("</script>")[0])
    assert data["@type"] == "LocalBusiness"
    assert data["name"] == raw["company"]["name"]
    assert data["telephone"] == raw["contact"]["phone"]
    assert "충청" in " ".join(data["areaServed"])


# ── 규격 호환 ─────────────────────────────────────────────────────
def test_the_brief_is_valid_under_schema_v1(raw):
    result = schema.validate(raw)
    assert result.ok, result.error_lines()
    assert result.warnings == [], result.warning_lines()


def test_no_new_top_level_keys_were_invented(raw):
    assert set(raw) <= set(schema.TOP_LEVEL) | {"_주의"}, set(raw) - set(schema.TOP_LEVEL)


def test_the_new_about_fields_are_optional():
    """연혁·인증이 없어도 옛 주문서가 그대로 지어진다."""
    for name in ("a-gonggan.json", "d-bareungyeol.json"):
        path = ROOT / "examples" / "customers" / name
        assert schema.validate(json.loads(path.read_text(encoding="utf-8"))).ok
        brief, _ = load_brief(path)
        assert brief.about.history == [] and brief.about.credentials == []


def test_the_other_two_masters_are_untouched():
    for master in ("master-interior-01", "master-cleaning-01"):
        assert (ROOT / "templates" / master / "index.html").is_file()
        assert (ROOT / "templates" / master / "assets" / "styles.css.j2").is_file()


# ── 고객이 주는 사진 ──────────────────────────────────────────────
def test_odd_customer_photos_survive_the_pipeline(tmp_path, raw):
    Image = pytest.importorskip("PIL.Image", reason="Pillow 가 없으면 건너뜁니다")
    shots = tmp_path / "shots"
    shots.mkdir()
    for name, size in (("tall.jpg", (900, 1600)), ("wide.jpg", (2400, 800)),
                       ("small.jpg", (320, 240)), ("dark.jpg", (1200, 900))):
        Image.new("RGB", size, (200, 204, 208) if "dark" not in name else (24, 28, 32)).save(
            shots / name, quality=88)
    data = copy.deepcopy(raw)
    data["hero"]["image"] = str(shots / "tall.jpg")
    data["services"][0]["사진"] = str(shots / "small.jpg")
    data["gallery"][0] = {"src": str(shots / "wide.jpg"), "caption": "설비"}
    data["projects"][0]["사진"] = str(shots / "dark.jpg")
    result = make(data, tmp_path / "photos")
    images = result.report["images"]
    assert images["warnings"] == []
    assert images["converted"] == 4
    out = result.out_dir / "assets" / "img"
    assert Image.open(out / "tall.webp").size[0] <= 1920
    assert Image.open(out / "small.webp").size == (320, 240)   # 작은 사진을 키우지 않는다


def test_photos_are_eager_at_the_top_and_lazy_below(page):
    hero = page.split('class="hr__shot"')[1].split("</figure>")[0]
    assert 'fetchpriority="high"' in hero and 'loading="lazy"' not in hero
    below = page.split('id="services"')[1]
    assert below.count('loading="lazy"') >= 10
