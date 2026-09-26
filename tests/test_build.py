"""지어진 결과물을 실제로 뜯어보는 시험.

템플릿 문법이 새어 나오지 않았는지, 링크가 실제 파일을 가리키는지,
JSON-LD 가 진짜 JSON 인지 — 납품 전에 사람이 확인하던 것들이다.
"""

import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import pytest

from factory.cli import main
from factory.intake import load_brief
from factory.package import make_zip, write_deploy_configs
from factory.pipeline import build, build_from_file

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []
        self.assets: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        if tag == "img" and a.get("src"):
            self.assets.append(a["src"])
        if tag == "link" and a.get("href"):
            self.assets.append(a["href"])
        if tag == "script" and a.get("src"):
            self.assets.append(a["src"])


def _is_local(url: str) -> bool:
    return not url.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:"))


@pytest.fixture(scope="module")
def cafe(tmp_path_factory):
    out = tmp_path_factory.mktemp("cafe")
    return build_from_file(EXAMPLES / "cafe-onepage.json", out, offline=True, clean=True)


@pytest.fixture(scope="module")
def dental(tmp_path_factory):
    out = tmp_path_factory.mktemp("dental")
    return build_from_file(EXAMPLES / "dental-5page.json", out, offline=True, clean=True)


def test_one_page_build_writes_the_expected_files(cafe):
    for name in ("index.html", "assets/styles.css", "assets/favicon.svg",
                 "sitemap.xml", "robots.txt", "build_report.json", "납품메모.md"):
        assert (cafe.out_dir / name).is_file(), name
    assert len(cafe.plan.content.pages) == 1


def test_five_page_build_makes_the_pages_it_has_material_for(dental):
    assert (dental.out_dir / "index.html").is_file()
    assert (dental.out_dir / "services.html").is_file()
    assert not (dental.out_dir / "gallery.html").exists()   # 사진이 없었다
    assert any("쪽을 냈습니다" in w for w in dental.report["warnings"])


@pytest.mark.parametrize("fixture", ["cafe", "dental"])
def test_no_template_syntax_escapes_into_the_product(fixture, request):
    result = request.getfixturevalue(fixture)
    for path in result.out_dir.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert "{{" not in text and "{%" not in text, path.name
        assert "Undefined" not in text
    css = (result.out_dir / "assets" / "styles.css").read_text(encoding="utf-8")
    assert "{{" not in css and "{%" not in css


@pytest.mark.parametrize("fixture", ["cafe", "dental"])
def test_every_local_link_and_asset_exists(fixture, request):
    result = request.getfixturevalue(fixture)
    for path in result.out_dir.rglob("*.html"):
        parser = _Links()
        parser.feed(path.read_text(encoding="utf-8"))
        for url in parser.hrefs + parser.assets:
            if _is_local(url):
                assert (result.out_dir / url.split("#")[0]).exists(), f"{path.name} → {url}"


@pytest.mark.parametrize("fixture", ["cafe", "dental"])
def test_json_ld_is_valid_json(fixture, request):
    result = request.getfixturevalue(fixture)
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    data = json.loads(block)
    assert data["@type"] == "LocalBusiness"
    assert data["name"] == result.plan.brief.business.name


def test_css_carries_the_decided_tokens(cafe):
    css = (cafe.out_dir / "assets" / "styles.css").read_text(encoding="utf-8")
    assert f"--color-primary: {cafe.plan.style.primary};" in css
    assert f"--radius: {cafe.plan.style.radius};" in css


def test_local_photos_are_copied_next_to_the_page(cafe):
    copied = list((cafe.out_dir / "assets" / "img").iterdir())
    assert copied, "주문서가 가리킨 사진이 산출물로 들어와야 합니다"
    html = (cafe.out_dir / "index.html").read_text(encoding="utf-8")
    assert "assets/img/" in html


def test_report_explains_the_choices(cafe):
    report = cafe.report
    assert report["template"]["reasons"]
    assert report["style"]["evidence"]
    assert report["contrast"]["text/background"] >= 7.0
    assert report["pages"][0]["file"] == "index.html"


def test_handoff_note_lists_what_is_missing(dental):
    note = (dental.out_dir / "납품메모.md").read_text(encoding="utf-8")
    assert "납품 전에 채워야 할 것" in note
    assert "왜 이 템플릿인가" in note


def test_sitemap_uses_the_domain(cafe):
    sitemap = (cafe.out_dir / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://bloomcoffee.kr/" in sitemap


def test_forced_template_overrides_matching(tmp_path):
    brief, _ = load_brief(EXAMPLES / "cafe-onepage.json")
    result = build(brief, tmp_path / "forced", template_id="five-pages-corp", offline=True)
    assert result.plan.template.id == "five-pages-corp"
    assert any("직접 지정" in r for r in result.plan.match.reasons)


def test_form_action_is_wired_when_asked(tmp_path):
    brief, _ = load_brief(EXAMPLES / "dental-5page.json")
    result = build(brief, tmp_path / "form", offline=True, form_action="https://formspree.io/f/x")
    html = (result.out_dir / "contact.html").read_text(encoding="utf-8")
    assert 'action="https://formspree.io/f/x"' in html


def test_deploy_configs_and_zip(cafe, tmp_path):
    written = write_deploy_configs(cafe)
    assert "netlify.toml" in written and "vercel.json" in written and "CNAME" in written
    assert (cafe.out_dir / "CNAME").read_text(encoding="utf-8").strip() == "bloomcoffee.kr"
    json.loads((cafe.out_dir / "vercel.json").read_text(encoding="utf-8"))

    archive = make_zip(cafe.out_dir, tmp_path / "bloom.zip")
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    assert "index.html" in names and "assets/styles.css" in names


def test_cli_build_returns_zero(tmp_path, capsys):
    code = main(["build", str(EXAMPLES / "cafe-onepage.json"), "-o", str(tmp_path / "cli"),
                 "--offline", "--clean", "--quiet"])
    assert code == 0
    assert (tmp_path / "cli" / "index.html").is_file()


def test_cli_plan_does_not_write_anything(tmp_path, capsys):
    code = main(["plan", str(EXAMPLES / "dental-5page.json"), "--offline", "--all"])
    assert code == 0
    output = capsys.readouterr().out
    assert "왜 이 템플릿인가" in output and "five-pages-corp" in output


def test_cli_rejects_a_broken_brief(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text('{"industry": "카페"}', encoding="utf-8")
    assert main(["build", str(path), "-o", str(tmp_path / "x"), "--offline"]) == 2
    assert "상호" in capsys.readouterr().err


def test_cli_batch_builds_every_brief(tmp_path):
    code = main(["batch", str(EXAMPLES), "-o", str(tmp_path / "batch"), "--offline", "--quiet"])
    assert code == 0
    assert (tmp_path / "batch" / "bloom-coffee" / "index.html").is_file()
    built = sorted(p.name for p in (tmp_path / "batch").iterdir())
    assert len(built) == len(list(EXAMPLES.glob("*.json"))) + len(list(EXAMPLES.glob("*.yaml")))


def test_yaml_brief_with_korean_keys_builds(tmp_path):
    result = build_from_file(EXAMPLES / "salon-onepage.yaml", tmp_path / "salon", offline=True)
    assert result.plan.brief.business.industry == "salon"
    assert result.plan.brief.site.pages == 1
    assert [i.title for i in result.plan.brief.items][0] == "커트"
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert "스튜디오 온" in html and "45,000원" in html
