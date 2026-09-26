import json

import pytest

from factory.intake import BriefError, load_brief, normalize_industry, parse_brief, slugify


def test_korean_keys_are_accepted():
    brief, warnings = parse_brief(
        {
            "상호": "연서치과",
            "업종": "치과",
            "contact": {"전화": "031-712-9040", "주소": "성남시 분당구"},
            "site": {"페이지": 5, "기능": ["지도", "문의폼"], "목표": ["예약"]},
            "brand": {"주색": "#0f6f8a", "분위기": ["깔끔", "신뢰"]},
            "레퍼런스": "https://example.com",
        }
    )
    assert brief.business.name == "연서치과"
    assert brief.business.industry == "clinic"
    assert brief.site.pages == 5
    assert brief.site.features == ["map", "form"]
    assert brief.site.goals == ["reservation"]
    assert brief.brand.mood == ["clean", "trustworthy"]
    assert brief.reference.url == "https://example.com"
    assert warnings == []


def test_missing_name_is_fatal():
    with pytest.raises(BriefError) as exc:
        parse_brief({"업종": "카페"})
    assert any("상호" in problem for problem in exc.value.problems)


def test_odd_page_count_is_clamped_with_warning():
    brief, warnings = parse_brief({"name": "가게", "site": {"pages": 3}})
    assert brief.site.pages == 5
    assert any("쪽" in w for w in warnings)


def test_unknown_industry_is_kept_not_guessed():
    assert normalize_industry("서핑샵") == "서핑샵"
    assert normalize_industry("") == "general"
    assert normalize_industry("브런치 카페") == "cafe"


def test_slug_falls_back_for_korean_only_names():
    assert slugify("Yeonseo Dental") == "yeonseo-dental"
    korean = slugify("연서치과")
    assert korean.startswith("site-") and korean == slugify("연서치과")


def test_items_accept_plain_strings_and_dicts():
    brief, _ = parse_brief(
        {"name": "가게", "메뉴": ["아메리카노", {"title": "라떼", "가격": "5,000원"}]}
    )
    assert [i.title for i in brief.items] == ["아메리카노", "라떼"]
    assert brief.items[1].price == "5,000원"


def test_load_brief_reports_bad_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text('{"name": "가게",}', encoding="utf-8")
    with pytest.raises(BriefError):
        load_brief(path)


def test_load_brief_roundtrip(tmp_path):
    path = tmp_path / "brief.json"
    path.write_text(json.dumps({"name": "가게", "industry": "카페"}), encoding="utf-8")
    brief, warnings = load_brief(path)
    assert brief.business.industry == "cafe"
    assert brief.source_path == str(path)
    assert warnings  # 연락처도 레퍼런스도 없으므로 경고가 있어야 한다
