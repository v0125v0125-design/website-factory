import pytest

from factory import colorkit
from factory.intake import parse_brief
from factory.reference import ReferenceFindings, analyze_html
from factory.theming import PRESETS, build_style, build_tokens, contrast_audit, preset_for

REFERENCE = """<html><head><meta name="theme-color" content="#8a5a2b">
<style>body{background:#fffaf3}.a{border-radius:18px}.b{color:#c9a227}section{padding:130px 0}</style>
</head><body></body></html>"""


def brief_for(**site):
    data = {"name": "가게", "industry": site.pop("industry", "카페")}
    data.update(site)
    return parse_brief(data)[0]


def test_brief_colour_beats_reference():
    brief = brief_for(brand={"primary_color": "#123456"})
    style = build_style(brief, analyze_html(REFERENCE))
    assert style.primary == "#123456"
    assert style.source == "brief"


def test_reference_colour_is_used_when_brief_is_silent():
    style = build_style(brief_for(), analyze_html(REFERENCE, source="ref"))
    assert style.primary == "#8a5a2b"
    assert style.accent == "#c9a227"
    assert style.radius == "18px"
    assert style.density == "airy"
    assert style.source.startswith("reference")
    assert style.confidence > 0.5


def test_preset_is_the_last_resort():
    style = build_style(brief_for(industry="치과"), ReferenceFindings(problems=["없음"]))
    assert style.primary == PRESETS["clinic"].primary
    assert style.source == "preset:clinic"
    assert style.confidence < 0.5


def test_cream_background_is_carried_over():
    style = build_style(brief_for(), analyze_html(REFERENCE))
    assert style.background == "#fffaf3"
    assert build_tokens(style)["color-background"] == "#fffaf3"


def test_strong_colour_is_not_mistaken_for_a_background():
    loud = """<html><head><style>.hero{background:#c0392b}.hero2{background:#c0392b}</style></head></html>"""
    style = build_style(brief_for(), analyze_html(loud))
    assert style.background == ""       # 붉은 띠를 바탕색으로 쓰지 않는다
    assert style.mode == "light"


def test_dark_reference_switches_mode():
    dark = """<html><head><style>body{background:#12141a}.a{color:#4c6ef5}.b{color:#4c6ef5}</style></head></html>"""
    style = build_style(brief_for(), analyze_html(dark))
    assert style.mode == "dark"
    assert colorkit.is_dark(build_tokens(style)["color-background"])


@pytest.mark.parametrize("industry", list(PRESETS))
def test_every_preset_produces_readable_tokens(industry):
    style = build_style(brief_for(industry=industry), ReferenceFindings())
    audit = contrast_audit(build_tokens(style))
    assert audit["text/background"] >= 7.0
    assert audit["muted/background"] >= 4.5
    assert audit["text/surface"] >= 4.5
    assert audit["on-primary/primary"] >= 4.5


def test_font_preference_is_respected():
    serif = build_style(brief_for(brand={"font_preference": "serif"}), ReferenceFindings())
    assert "Noto Serif KR" in serif.fonts.heading
    sans = build_style(brief_for(brand={"font_preference": "sans"}), ReferenceFindings())
    assert "Noto Sans KR" in sans.fonts.heading and "Serif" not in sans.fonts.heading


def test_preset_lookup_falls_back_to_general():
    assert preset_for("서핑샵") is PRESETS["general"]


def test_photo_overlay_is_dark_enough_at_the_text():
    # 히어로 글은 사진 아래쪽에 놓인다. 그 자리의 덮개가 옅으면
    # 밝은 사진이 왔을 때 흰 글자가 사라진다.
    from factory.theming import build_tokens

    style = build_style(brief_for(), ReferenceFindings())
    overlay = build_tokens(style)["overlay"]
    bottom = float(overlay.rstrip(")").split("rgba(0,0,0,")[-1].split(")")[0].split()[0])
    assert bottom >= 0.78
