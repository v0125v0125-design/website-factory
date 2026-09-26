import pytest

from factory import colorkit as ck


def test_parse_forms():
    assert ck.parse("#f4a") == (255, 68, 170)
    assert ck.parse("ff44aa") == (255, 68, 170)
    assert ck.parse("rgb(255, 68, 170)") == (255, 68, 170)
    assert ck.parse("rgba(255 68 170 / .5)") == (255, 68, 170)


def test_parse_rejects_nonsense():
    with pytest.raises(ck.ColorError):
        ck.parse("연한 갈색")
    assert ck.is_color("#abc") and not ck.is_color("var(--x)")


def test_contrast_matches_known_values():
    assert ck.contrast("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)
    assert ck.contrast("#ffffff", "#ffffff") == pytest.approx(1.0, abs=0.01)


def test_chroma_separates_cream_from_white():
    # HSL 채도는 크림색을 1.0 으로 보지만 chroma 는 거의 0 으로 본다.
    assert ck.to_hsl(ck.parse("#fffaf3"))[1] > 0.9
    assert ck.chroma("#fffaf3") < 0.1
    assert ck.chroma("#ffffff") == 0.0
    assert ck.chroma("#ff0000") == 1.0


def test_ensure_contrast_reaches_target():
    for base, background in [("#8a5a2b", "#ffffff"), ("#22b8cf", "#101214"), ("#f0f0f0", "#fafafa")]:
        fixed = ck.ensure_contrast(base, background, 4.5)
        assert ck.contrast(fixed, background) >= 4.5


@pytest.mark.parametrize("primary", ["#2f6fed", "#8a5a2b", "#c0392b", "#12b886", "#111827"])
@pytest.mark.parametrize("mode", ["light", "dark"])
def test_palette_always_readable(primary, mode):
    palette = ck.build_palette(primary, mode=mode)
    report = palette.contrast_report()
    assert report["text/background"] >= 7.0
    assert report["muted/background"] >= 4.5
    assert report["on-primary/primary"] >= 4.5
    assert report["primary/background"] >= 3.0


def test_palette_honours_given_background():
    palette = ck.build_palette("#8a5a2b", mode="light", background="#fffaf3")
    assert palette.background == "#fffaf3"
    assert palette.surface != palette.background
    assert ck.contrast(palette.text, palette.background) >= 7.0


def test_scale_goes_light_to_dark():
    steps = ck.scale("#2f6fed", 5)
    assert len(steps) == 5
    assert ck.luminance(ck.parse(steps[0])) > ck.luminance(ck.parse(steps[-1]))
