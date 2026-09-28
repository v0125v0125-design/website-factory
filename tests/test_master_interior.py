"""MASTER_INTERIOR_01 — 양산형 마스터가 데이터만 바꿔도 버티는지 본다.

고객이 바뀌면 바뀌는 것: 글자 수, 항목 개수, 사진 유무, 색.
그 어느 쪽으로 흔들어도 페이지가 깨지지 않아야 팔 수 있다.
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from factory.intake import parse_brief
from factory.pipeline import build, build_from_file
from factory.theming import THEMES, contrast_audit

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
SAMPLE = EXAMPLES / "master-interior-01.json"
TEMPLATE = "master-interior-01"


class _Ids(HTMLParser):
    """id 와 내부 링크를 모은다."""

    def __init__(self):
        super().__init__()
        self.ids: set[str] = set()
        self.anchors: list[str] = []
        self.images: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("href", "").startswith("#"):
            self.anchors.append(a["href"][1:])
        if tag == "img" and a.get("src"):
            self.images.append(a["src"])


def _parse(html: str) -> _Ids:
    parser = _Ids()
    parser.feed(html)
    return parser


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    return build_from_file(SAMPLE, tmp_path_factory.mktemp("mi"), offline=True, clean=True)


@pytest.fixture(scope="module")
def sample_html(sample):
    return (sample.out_dir / "index.html").read_text(encoding="utf-8")


def _build(data: dict, out, **kwargs):
    brief, _ = parse_brief(data, source_path=str(SAMPLE))
    return build(brief, out, template_id=TEMPLATE, offline=True, clean=True, **kwargs)


def _base(**extra) -> dict:
    data = {
        "company": {"name": "공간인테리어", "industry": "인테리어"},
        "hero": {"headline": "사는 동안 편한 집", "subline": "천안·아산"},
        "contact": {"전화": "041-000-0000", "카카오톡": "https://pf.kakao.com/_x"},
        "site": {"pages": 1},
        "theme": "charcoal",
    }
    data.update(extra)
    return data


# ── 뼈대 ──────────────────────────────────────────────────────────

def test_brief_can_name_its_own_template(sample):
    assert sample.plan.template.id == TEMPLATE
    assert any("주문서가 지정한" in r for r in sample.plan.match.reasons)


def test_sections_are_in_the_planned_order(sample):
    kinds = [s.kind for s in sample.plan.content.pages[0].sections]
    assert kinds == ["hero", "strengths", "services", "about", "projects",
                     "cta", "process", "testimonials", "faq", "contact"]


def test_every_anchor_points_at_something_real(sample_html):
    page = _parse(sample_html)
    for anchor in page.anchors:
        assert anchor in page.ids, f"#{anchor} 가 가리키는 곳이 없습니다"


def test_no_template_syntax_and_no_missing_images(sample, sample_html):
    assert "{{" not in sample_html and "{%" not in sample_html
    for src in _parse(sample_html).images:
        if not src.startswith(("http", "data:")):
            assert (sample.out_dir / src).is_file(), src


def test_phone_and_kakao_reach_the_customer(sample, sample_html):
    assert f'href="{sample.plan.brief.contact.tel_href()}"' in sample_html
    assert "pf.kakao.com" in sample_html


def test_mobile_bar_is_there_with_every_way_to_call(sample_html):
    bar = re.search(r'<nav class="mbar".*?</nav>', sample_html, re.S)
    assert bar, "모바일 하단 바가 없습니다"
    assert bar.group(0).count("<a ") == 3      # 전화 · 카카오톡 · 견적


def test_seo_comes_from_the_seo_block(sample, sample_html):
    assert "<title>천안 인테리어 공간인테리어" in sample_html
    assert 'name="keywords" content="천안 인테리어' in sample_html
    assert 'property="og:image"' in sample_html
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', sample_html, re.S)
    data = json.loads(block.group(1))
    assert data["areaServed"] == ["천안", "아산"]


def test_projects_carry_their_extra_photos(sample_html):
    # 크게 보기가 쓸 사진 목록이 마크업에 실려 있어야 한다.
    assert sample_html.count("data-images=") == 6
    assert "사진 2장" in sample_html


# ── 데이터가 흔들려도 ──────────────────────────────────────────────

@pytest.mark.parametrize("count", [1, 2, 3, 4, 12])
def test_any_number_of_services(count, tmp_path):
    services = [{"name": f"서비스 {n}", "설명": "설명입니다"} for n in range(count)]
    result = _build(_base(services=services), tmp_path / f"svc{count}")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert html.count('class="svc__card"') == count


@pytest.mark.parametrize("count", [1, 2, 5, 9])
def test_any_number_of_projects(count, tmp_path):
    projects = [{"name": f"사례 {n}", "분류": "아파트", "사진": "photos/interior/hero.svg"}
                for n in range(count)]
    result = _build(_base(projects=projects), tmp_path / f"pj{count}")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert html.count('class="pj__cell"') == count


def test_no_reviews_no_faq_no_projects_still_builds(tmp_path):
    result = _build(_base(), tmp_path / "bare")
    kinds = [s.kind for s in result.plan.content.pages[0].sections]
    assert "testimonials" not in kinds and "faq" not in kinds and "projects" not in kinds
    assert "hero" in kinds and "contact" in kinds
    assert any("projects" in s for s in result.plan.content.meta["skipped"])


def test_a_very_long_company_name_does_not_break_the_page(tmp_path):
    long_name = "주식회사 대한민국제일종합인테리어건설시공디자인그룹"
    data = _base()
    data["company"]["name"] = long_name
    result = _build(data, tmp_path / "long")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert long_name in html
    # 제목 글자수는 검색결과에서 잘리지 않도록 잘라 둔다
    title = re.search(r"<title>(.*?)</title>", html).group(1)
    assert len(title) <= 70


def test_very_long_sentences_are_kept_whole(tmp_path):
    long_line = "저희는 " + "정말 " * 60 + "꼼꼼합니다."
    data = _base()
    data["hero"]["subline"] = long_line
    data["company"]["description"] = long_line
    result = _build(data, tmp_path / "wordy")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert long_line in html      # 자르지 않는다 — CSS 가 접는다


def test_a_project_without_photos_is_flagged_not_faked(tmp_path):
    result = _build(_base(projects=[{"name": "사진 없는 사례", "분류": "아파트"}]), tmp_path / "nopic")
    assert any("사진" in item for item in result.plan.content.meta["todo"])
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert "[사진 없는 사례 사진]" in html


# ── 색 버전 ───────────────────────────────────────────────────────

@pytest.mark.parametrize("name", list(THEMES))
def test_every_theme_version_is_readable(name, tmp_path):
    result = _build(_base(theme=name), tmp_path / f"theme-{name}")
    audit = contrast_audit(result.plan.tokens)
    assert audit["text/background"] >= 7.0
    assert audit["text/surface"] >= 7.0
    assert audit["muted/background"] >= 4.5
    assert audit["on-primary/primary"] >= 4.5
    css = (result.out_dir / "assets" / "styles.css").read_text(encoding="utf-8")
    assert f"--color-primary: {result.plan.style.primary};" in css


def test_theme_preset_can_be_overridden_piece_by_piece(tmp_path):
    result = _build(_base(theme={"preset": "black", "accent": "#2FA36B"}), tmp_path / "mix")
    assert result.plan.style.mode == "dark"
    assert result.plan.tokens["color-accent"].lower() == "#2fa36b"


def test_customer_colour_still_beats_the_theme(tmp_path):
    data = _base(theme="black")
    data["brand"] = {"주색": "#7A1F1F"}
    result = _build(data, tmp_path / "brandwins")
    assert result.plan.style.primary == "#7a1f1f"
