from factory.reference import ReferenceUnavailable, analyze_html, fetch, probe

SAMPLE = """<!doctype html><html><head><title>Warm</title>
<meta name="theme-color" content="#8a5a2b">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Noto+Sans+KR">
<style>
  body { background: #fffaf3; color: #3b2a1d; font-family: "Playfair Display", serif; }
  .hero { background: #8a5a2b; border-radius: 18px; }
  .btn { background-color: #8a5a2b; border-radius: 18px; }
  .accent { color: #c9a227; }
  section { padding: 128px 0; }
</style></head>
<body><header><a href=#>1</a><a href=#>2</a></header><img src=a><img src=b></body></html>"""


def test_reads_the_facts_it_can_see():
    f = analyze_html(SAMPLE, source="sample")
    assert f.theme_color == "#8a5a2b"
    assert f.body_background == "#fffaf3"
    assert f.dominant_radius() == 18.0
    assert f.max_block_padding == 128.0
    assert "Playfair Display" in f.google_fonts
    assert f.serif_hint is True
    assert f.nav_links == 2 and f.images == 2
    assert f.evidence


def test_page_background_prefers_body_rule():
    # .hero 와 .btn 이 #8a5a2b 를 두 번 쓰지만 바탕색은 body 의 것이다.
    f = analyze_html(SAMPLE, source="sample")
    assert f.page_background() == "#fffaf3"


def test_broken_markup_does_not_explode():
    f = analyze_html("<html><head><style>body{background:#111", source="x")
    assert f.body_background in ("", "#111111")


def test_missing_local_file_is_reported_not_raised(tmp_path):
    f = probe(html_path=str(tmp_path / "nope.html"))
    assert f.problems and not f.fetched


def test_offline_skips_the_network():
    f = probe(url="https://example.com", offline=True)
    assert f.fetched is False
    assert any("오프라인" in p for p in f.problems)


def test_local_file_is_read(tmp_path):
    path = tmp_path / "ref.html"
    path.write_text(SAMPLE, encoding="utf-8")
    f = probe(html_path=str(path))
    assert f.theme_color == "#8a5a2b"


def test_fetch_rejects_non_http():
    try:
        fetch("file:///etc/passwd")
    except ReferenceUnavailable as exc:
        assert "http" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("file:// 을 막아야 합니다")
