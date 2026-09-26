from factory.catalog import get_template
from factory.content import build_content, lexicon_for
from factory.intake import parse_brief
from factory.reference import ReferenceFindings
from factory.theming import build_style

FULL = {
    "name": "연서치과",
    "industry": "치과",
    "contact": {"phone": "031-712-9040", "address": "성남시 분당구"},
    "site": {"pages": 5, "features": ["form", "process"], "goals": ["예약"]},
    "items": [{"title": "충치 치료"}],
    "business": {"description": "2014년에 문을 연 동네 치과입니다."},
}


def _content(data, template_id):
    brief, _ = parse_brief(data)
    style = build_style(brief, ReferenceFindings())
    return brief, build_content(brief, get_template(template_id), style)


def test_nothing_is_invented_when_the_description_is_missing():
    brief, content = _content({"name": "가게", "industry": "카페"}, "onepage-classic")
    hero = content.pages[0].sections[0]
    assert hero.subheading.startswith("[") and hero.subheading.endswith("]")
    assert any("한 줄 소개" in item for item in content.meta["todo"])


def test_sections_without_material_are_dropped_not_faked():
    _, content = _content({"name": "가게", "industry": "카페"}, "onepage-classic")
    kinds = [s.kind for s in content.pages[0].sections]
    assert "gallery" not in kinds and "testimonials" not in kinds and "faq" not in kinds
    assert any("gallery" in s for s in content.meta["skipped"])


def test_headings_follow_the_industry():
    _, content = _content(FULL, "five-pages-corp")
    labels = [n["label"] for n in content.nav]
    assert "진료 과목" in labels and "병원 소개" in labels
    assert lexicon_for("clinic").items_heading == "진료 과목"


def test_subpage_without_its_main_section_is_not_shipped():
    _, content = _content(FULL, "five-pages-corp")  # 사진이 없다
    files = [p.filename for p in content.pages]
    assert "gallery.html" not in files
    assert all(link["href"] != "gallery.html" for link in content.nav)
    assert any("gallery.html" in s for s in content.meta["skipped"])


def test_one_page_navigation_uses_anchors():
    _, content = _content(FULL, "onepage-classic")
    assert content.nav and all(link["href"].startswith("#") for link in content.nav)


def test_cta_follows_the_stated_goal():
    _, content = _content(FULL, "five-pages-corp")
    assert content.meta["cta_label"] == "예약 문의"
    assert content.meta["cta_href"] == "tel:0317129040"


def test_explicit_cta_wins():
    data = dict(FULL, site={**FULL["site"], "primary_cta": "상담 예약하기"})
    _, content = _content(data, "five-pages-corp")
    assert content.meta["cta_label"] == "상담 예약하기"


def test_requested_process_section_leaves_slots_not_lies():
    _, content = _content(FULL, "five-pages-corp")
    about = next(p for p in content.pages if p.filename == "about.html")
    process = next(s for s in about.sections if s.kind == "process")
    assert all(step["title"].startswith("[") for step in process.data["steps"])
    assert sum("단계 제목" in item for item in content.meta["todo"]) == 3
