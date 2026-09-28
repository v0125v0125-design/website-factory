"""MASTER_CLEANING_01 — 청소·홈케어 마스터를 지킨다.

인테리어 마스터와 나눠 쓰는 것은 엔진(factory/)뿐입니다. 화면과 말씨는
따로입니다. 그래서 여기서 보는 것도 인테리어와 다릅니다.

  · 작업 전·후가 실제로 비교되는가 (한 장만 와도 버티는가)
  · "어디까지 갑니까" 가 화면에 있는가
  · 없는 실적을 숫자로 세우지 않는가
  · 고객이 주는 아무 사진이나 받아도 레이아웃이 버티는가
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
TEMPLATE = "master-cleaning-01"
BRIEF = ROOT / "examples" / "customers" / "d-bareungyeol.json"
SECTIONS = ("strengths", "services", "about", "beforeafter", "projects",
            "process", "area", "testimonials", "faq", "contact")


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(BRIEF.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return build_from_file(BRIEF, tmp_path_factory.mktemp("cleaning") / "site", offline=True)


@pytest.fixture(scope="module")
def page(built) -> str:
    return (built.out_dir / "index.html").read_text(encoding="utf-8")


def make(data: dict, out: Path, **kw):
    brief, _ = parse_brief(data, source_path=str(BRIEF))
    return build(brief, out, offline=True, clean=True, **kw)


def html_of(result) -> str:
    return (result.out_dir / "index.html").read_text(encoding="utf-8")


# ── 지어지는가 ────────────────────────────────────────────────────
def test_the_cleaning_master_is_the_one_that_gets_picked(built):
    assert built.plan.template.id == TEMPLATE
    assert built.plan.brief.business.industry == "cleaning"


def test_every_section_lands_on_the_page(page):
    for name in SECTIONS:
        assert f'id="{name}"' in page, name


def test_nothing_was_dropped_for_want_of_material(built):
    assert built.plan.content.meta["skipped"] == []
    assert built.plan.content.meta["todo"] == []


def test_the_page_stays_light(built):
    total = sum(f.stat().st_size for f in built.out_dir.rglob("*") if f.is_file())
    assert total < 400 * 1024, f"{total/1024:.0f}KB"


# ── 작업 전 · 후 ──────────────────────────────────────────────────
def test_pairs_become_sliders_and_plain_cases_stay_out_of_them(page, raw):
    pairs = [p for p in raw["projects"] if p.get("작업전") and p.get("작업후")]
    plain = [p for p in raw["projects"] if not p.get("작업전")]
    assert page.count('class="ba__range"') == len(pairs)
    assert page.count('class="cs__cell"') == len(plain)
    for pair in pairs:                      # 같은 사례가 두 번 나오지 않는다
        assert page.count(">" + pair["name"] + "<") == 1


def test_the_slider_needs_no_library(page):
    assert 'type="range"' in page
    assert 'style="clip-path' not in page    # 값은 CSS 에 있고 HTML 은 --pos 만 준다
    assert "--pos:50%" in page
    assert not re.search(r'<script[^>]+src=', page), "바깥 자바스크립트를 끌어오지 않는다"


def test_one_sided_pairs_still_show_the_photo_they_have(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["projects"][0].pop("작업후")
    result = make(data, tmp_path / "half")
    html = html_of(result)
    assert 'class="ba__view ba__view--one"' in html
    assert html.count('class="ba__range"') == 3
    todo = " ".join(result.plan.content.meta["todo"])
    assert "작업 후 사진" in todo             # 무엇이 모자란지 납품메모에 적힌다


def test_no_before_after_at_all_just_drops_the_section(tmp_path, raw):
    data = copy.deepcopy(raw)
    for project in data["projects"]:
        project.pop("작업전", None)
        project.pop("작업후", None)
    html = html_of(make(data, tmp_path / "nopair"))
    assert 'id="beforeafter"' not in html
    assert 'id="projects"' in html           # 사례는 그대로 남는다
    assert html.count('class="cs__cell"') == len(data["projects"])


# ── 서비스 지역 ───────────────────────────────────────────────────
def test_the_service_area_is_on_the_page_in_three_places(page, raw):
    for name in raw["contact"]["서비스지역"]:
        assert name in page
    assert 'id="area"' in page
    assert raw["contact"]["지역안내"] in page


def test_many_areas_do_not_break_the_band(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["contact"]["서비스지역"] = [f"{n} 전 지역" for n in
                                  ("천안", "아산", "세종", "공주", "청주", "평택", "안성", "당진")]
    html = html_of(make(data, tmp_path / "areas"))
    assert html.count('<li>') >= 8
    for name in data["contact"]["서비스지역"]:
        assert name in html


def test_no_areas_drops_the_band_instead_of_faking_one(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["contact"].pop("서비스지역")
    html = html_of(make(data, tmp_path / "noarea"))
    assert 'id="area"' not in html
    assert 'id="contact"' in html


# ── 거짓말하지 않는가 ─────────────────────────────────────────────
def test_strengths_never_grow_numbers_they_were_not_given(tmp_path, raw):
    """인테리어는 '1,240건' 을 세운다. 청소는 세우지 않는다 — 셀 실적이 없다."""
    data = copy.deepcopy(raw)
    data["strengths"][0]["숫자"] = "9,999"
    data["strengths"][0]["단위"] = "건"
    html = html_of(make(data, tmp_path / "numbers"))
    assert "9,999" not in html


def test_no_developer_words_reach_the_customer(page):
    for word in ("form_action", "--form-action", "지정하십시오", "build_report",
                 "납품메모", "{{", "}}", "Undefined"):
        assert word not in page, word


def test_the_form_says_what_is_true_when_nothing_receives_it(page):
    form = page.split("<form")[1].split(">")[0]
    assert 'data-noaction="1"' in form
    note = page.split('class="ct__sent"')[1].split("</p>")[0]
    assert "전화" in note and "카카오톡" in note
    assert "--form" not in note
    for lie in ("접수되었습니다", "전송되었습니다", "감사합니다"):
        assert lie not in page, lie


def test_a_real_form_target_turns_the_notice_off(tmp_path, raw):
    result = make(raw, tmp_path / "wired", form_action="https://formspree.io/f/abcd")
    html = html_of(result)
    assert 'action="https://formspree.io/f/abcd"' in html
    assert "data-noaction" not in html.split("<form")[1].split(">")[0]
    assert 'class="ct__sent"' not in html


# ── 재료가 모자라도 버티는가 ──────────────────────────────────────
@pytest.mark.parametrize("count", [1, 3, 8, 12])
def test_any_number_of_services_still_lays_out(tmp_path, raw, count):
    data = copy.deepcopy(raw)
    base = data["services"]
    data["services"] = [dict(base[i % len(base)], name=f"서비스 {i + 1}") for i in range(count)]
    html = html_of(make(data, tmp_path / f"svc{count}"))
    assert html.count('class="sv__card"') == count
    assert 'id="services"' in html


@pytest.mark.parametrize("count", [0, 1, 10])
def test_any_number_of_cases_still_lays_out(tmp_path, raw, count):
    data = copy.deepcopy(raw)
    plain = [p for p in data["projects"] if not p.get("작업전")]
    pairs = [p for p in data["projects"] if p.get("작업전")]
    data["projects"] = pairs + [dict(plain[i % len(plain)], name=f"사례 {i + 1}") for i in range(count)]
    html = html_of(make(data, tmp_path / f"case{count}"))
    assert html.count('class="cs__cell"') == count
    assert ('id="projects"' in html) is (count > 0)
    assert 'id="beforeafter"' in html        # 비교는 그대로 남는다


def test_no_reviews_drops_the_section(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["reviews"] = []
    html = html_of(make(data, tmp_path / "norev"))
    assert 'id="testimonials"' not in html
    assert 'id="faq"' in html


def test_no_faq_drops_the_section(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["faq"] = []
    html = html_of(make(data, tmp_path / "nofaq"))
    assert 'id="faq"' not in html
    assert 'id="contact"' in html


def test_no_photos_at_all_still_ships_a_page(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["hero"].pop("image")
    data["about"].pop("사진")
    for row in data["services"]:
        row.pop("사진", None)
    for row in data["projects"]:
        for key in ("사진", "작업전", "작업후"):
            row.pop(key, None)
    html = html_of(make(data, tmp_path / "nophoto"))
    assert 'id="contact"' in html
    assert "<img" not in html or 'class="hr__slot"' in html
    assert 'id="beforeafter"' not in html


def test_a_long_name_and_a_long_headline_do_not_spill(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["company"]["name"] = "주식회사 바른결종합홈케어서비스 천안아산지점"
    data["hero"]["headline"] = "입주청소부터 이사청소 거주청소 상가청소 준공청소까지 " * 2
    html = html_of(make(data, tmp_path / "long"))
    assert data["company"]["name"] in html
    assert "hr__title" in html


# ── 연락 갈래 ─────────────────────────────────────────────────────
def test_without_kakao_no_kakao_button_is_drawn(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["contact"].pop("kakao")
    html = html_of(make(data, tmp_path / "nokakao"))
    assert "pf.kakao.com" not in html
    assert "카카오톡 상담" not in html          # 버튼·링크가 사라진다 (본문 글은 고객 것)
    assert html.count('class="cbar"') == 1
    assert 'style="--n:2"' in html


def test_without_a_phone_the_estimate_button_takes_the_lead(tmp_path, raw):
    data = copy.deepcopy(raw)
    data["contact"].pop("phone")
    html = html_of(make(data, tmp_path / "nophone"))
    assert 'href="tel:' not in html
    assert 'class="is-primary" href="#contact"' in html


def test_every_anchor_the_buttons_point_at_exists(page):
    targets = {m for m in re.findall(r'href="#([a-z-]+)"', page)}
    ids = {m for m in re.findall(r'id="([a-z-]+)"', page)}
    assert targets - ids == set(), targets - ids


# ── 규격 호환 ─────────────────────────────────────────────────────
def test_the_brief_is_valid_under_schema_v1(raw):
    result = schema.validate(raw)
    assert result.ok, result.error_lines()
    assert result.warnings == [], result.warning_lines()


def test_the_new_fields_are_optional(tmp_path, raw):
    """before/after 와 서비스지역이 없어도 옛 주문서가 그대로 지어진다."""
    old = json.loads((ROOT / "examples" / "customers" / "a-gonggan.json").read_text(encoding="utf-8"))
    assert schema.validate(old).ok
    brief, _ = load_brief(ROOT / "examples" / "customers" / "a-gonggan.json")
    assert brief.contact.areas == []
    assert all(not p.is_pair() for p in brief.projects)


def test_a_half_filled_pair_is_flagged_but_not_refused(raw):
    data = copy.deepcopy(raw)
    data["projects"][0].pop("작업후")
    result = schema.validate(data)
    assert result.ok
    assert any("작업 전·후" in line for line in result.warning_lines())


def test_the_interior_master_is_untouched():
    interior = ROOT / "examples" / "customers" / "a-gonggan.json"
    assert schema.validate(json.loads(interior.read_text(encoding="utf-8"))).ok
    assert (ROOT / "templates" / "master-interior-01" / "index.html").is_file()


# ── 고객이 주는 사진 ──────────────────────────────────────────────
def test_odd_customer_photos_survive_the_pipeline(tmp_path, raw):
    """세로 · 가로 · 저해상도 · 어두운 사진. 고객은 좋은 사진만 주지 않는다."""
    Image = pytest.importorskip("PIL.Image", reason="Pillow 가 없으면 건너뜁니다")
    shots = tmp_path / "shots"
    shots.mkdir()
    kinds = {
        "tall.jpg": ((900, 1600), (210, 205, 200)),
        "wide.jpg": ((2400, 800), (230, 230, 228)),
        "small.jpg": ((320, 240), (200, 202, 205)),
        "dark.jpg": ((1200, 900), (26, 28, 30)),
    }
    for name, (size, colour) in kinds.items():
        Image.new("RGB", size, colour).save(shots / name, quality=88)

    data = copy.deepcopy(raw)
    data["hero"]["image"] = str(shots / "tall.jpg")
    data["services"][0]["사진"] = str(shots / "small.jpg")
    data["projects"][0]["작업전"] = str(shots / "dark.jpg")
    data["projects"][0]["작업후"] = str(shots / "wide.jpg")
    result = make(data, tmp_path / "photos")
    images = result.report["images"]

    assert images["warnings"] == []
    assert images["converted"] == 4                # jpg 넉 장이 webp 로
    assert images["bytes_after"] < images["bytes_before"]
    out = result.out_dir / "assets" / "img"
    made = {f.name for f in out.glob("*.webp")}
    assert {"tall.webp", "wide.webp", "small.webp", "dark.webp"} <= made, made
    # 역할별 최대폭을 넘지 않고, 작은 사진을 억지로 키우지도 않는다
    Image = pytest.importorskip("PIL.Image")
    assert Image.open(out / "tall.webp").size[0] <= 1920
    assert Image.open(out / "wide.webp").size[0] <= 1600
    assert Image.open(out / "small.webp").size == (320, 240)
    html = html_of(result)
    assert "assets/img/" in html


def test_photos_are_lazy_below_the_fold_and_eager_at_the_top(page):
    hero = page.split('class="hr__shot"')[1].split("</figure>")[0]
    assert 'fetchpriority="high"' in hero and 'loading="lazy"' not in hero
    below = page.split('id="beforeafter"')[1]
    assert below.count('loading="lazy"') >= 8
