import json

import pytest

from factory.catalog import TemplateError, get_template, load_catalog, load_template
from factory.intake import parse_brief
from factory.matching import choose, rank


def test_catalog_has_both_shapes():
    ids = {t.id: t for t in load_catalog()}
    assert "onepage-classic" in ids and "five-pages-corp" in ids
    assert ids["onepage-classic"].page_count == 1
    assert ids["five-pages-corp"].page_count == 5
    assert len(ids["five-pages-corp"].pages) == 5


def test_every_template_page_has_a_file():
    for template in load_catalog():
        for page in template.pages:
            assert (template.root / page.filename).exists()


def test_manifest_errors_are_explicit(tmp_path):
    (tmp_path / "template.json").write_text(
        json.dumps({"id": "x", "page_count": 2, "pages": [{"title": "홈", "sections": ["hero"]}]}),
        encoding="utf-8",
    )
    with pytest.raises(TemplateError) as exc:
        load_template(tmp_path)
    assert "page_count" in str(exc.value)


def test_missing_page_file_is_caught(tmp_path):
    (tmp_path / "template.json").write_text(
        json.dumps({"id": "x", "pages": [{"slug": "", "title": "홈", "sections": ["hero"]}]}),
        encoding="utf-8",
    )
    with pytest.raises(TemplateError) as exc:
        load_template(tmp_path)
    assert "index.html" in str(exc.value)


def test_unknown_template_id_lists_what_exists():
    with pytest.raises(TemplateError) as exc:
        get_template("없는템플릿")
    assert "onepage-classic" in str(exc.value)


def _brief(pages, industry, **extra):
    data = {"name": "가게", "industry": industry, "site": {"pages": pages, **extra}}
    return parse_brief(data)[0]


def test_one_page_order_picks_the_one_page_template():
    match = choose(_brief(1, "카페"), load_catalog())
    assert match.template.id == "onepage-classic"
    assert any("1쪽" in r for r in match.reasons)


def test_five_page_order_picks_the_five_page_template():
    match = choose(_brief(5, "치과"), load_catalog())
    assert match.template.id == "five-pages-corp"


def test_page_count_outweighs_industry():
    # 카페는 원페이지 템플릿의 업종이지만 5쪽을 주문하면 5쪽짜리가 이긴다.
    match = choose(_brief(5, "카페"), load_catalog())
    assert match.template.page_count == 5


def test_unsupported_feature_is_named_in_penalties():
    brief = _brief(1, "카페", features=["공지"])
    match = choose(brief, load_catalog())
    assert any("공지" in p or "notice" in p for p in match.penalties)


def test_rank_is_stable_and_sorted():
    brief = _brief(1, "카페")
    first = rank(brief, load_catalog())
    second = rank(brief, load_catalog())
    assert [m.template.id for m in first] == [m.template.id for m in second]
    assert first[0].score >= first[-1].score


def test_rank_needs_templates():
    with pytest.raises(ValueError):
        rank(_brief(1, "카페"), [])
