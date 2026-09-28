"""판매 가능한가 — 규격·사진·양산·극단값을 한자리에서 본다.

여기 있는 것은 전부 "실제 고객에게 돈을 받고 넘길 때" 걸리는 것들이다.
휴대폰으로 찍은 8MB 사진, 서른 자짜리 상호, 후기가 아직 없는 신생 업체,
카카오톡을 안 쓰는 사장님 — 하나라도 깨지면 그날 납품이 멈춘다.
"""

import json
from pathlib import Path

import pytest

from factory import images, schema
from factory.cli import main
from factory.intake import BriefError, load_brief, parse_brief
from factory.pipeline import build, build_from_file

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
CUSTOMERS = EXAMPLES / "customers"
TEMPLATE = "master-interior-01"
PHOTO = EXAMPLES / "photos" / "interior" / "hero.svg"


# ── SITE_CONFIG_SCHEMA_V1 ─────────────────────────────────────────

def test_every_shipped_example_matches_the_schema():
    for path in list(EXAMPLES.glob("*.json")) + list(EXAMPLES.glob("*.yaml")) + list(CUSTOMERS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else __import__(
            "yaml").safe_load(path.read_text(encoding="utf-8"))
        result = schema.validate(data)
        assert result.ok, f"{path.name}\n" + result.report()


def test_missing_company_name_is_an_error_with_a_usable_hint():
    result = schema.validate({"industry": "인테리어"})
    assert not result.ok
    problem = result.errors[0]
    assert problem.where == "company.name"
    assert "상호" in problem.hint


def test_a_typo_in_a_top_level_key_is_caught_and_guessed():
    result = schema.validate({"name": "가게", "projcets": []})
    assert result.ok                       # 짓기는 한다
    assert any("projects" in w.hint for w in result.warnings)


def test_wrong_shapes_are_errors_not_crashes():
    result = schema.validate({"name": "가게", "services": {"a": 1}, "contact": "010-0000-0000"})
    wheres = {p.where for p in result.errors}
    assert "services" in wheres and "contact" in wheres


def test_rows_must_carry_what_the_template_needs():
    result = schema.validate({
        "name": "가게",
        "projects": [{"분류": "아파트"}],
        "faq": [{"질문": "언제?"}],
        "reviews": [{"이름": "김○○"}],
    })
    wheres = {p.where for p in result.errors}
    assert "projects[0].name" in wheres
    assert "faq[0].answer" in wheres
    assert "reviews[0].quote" in wheres


def test_unknown_theme_and_long_seo_are_warnings_only():
    result = schema.validate({"name": "가게", "theme": "보라", "seo": {"title": "가" * 90}})
    assert result.ok
    text = result.report()
    assert "charcoal" in text and "70자" in text


def test_loading_a_broken_brief_says_where_it_broke(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"industry": "인테리어"}, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(BriefError) as exc:
        load_brief(path)
    assert any("company.name" in problem for problem in exc.value.problems)


def test_cli_validate_returns_one_when_broken(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text('{"projects": [{"분류": "아파트"}]}', encoding="utf-8")
    assert main(["validate", str(path)]) == 1
    assert "SITE_CONFIG_SCHEMA_V1" in capsys.readouterr().out
    assert main(["validate", str(CUSTOMERS / "b-onhouse.json")]) == 0


# ── 사진 줄이기 ───────────────────────────────────────────────────

def _photo(path: Path, size=(4032, 3024), orientation: int | None = None) -> Path:
    Image = pytest.importorskip("PIL.Image")
    image = Image.new("RGB", size, (180, 160, 140))
    for x in range(0, size[0], 40):        # 압축이 0바이트로 끝나지 않게 무늬를 넣는다
        for y in range(0, size[1], 40):
            image.paste((90 + x % 120, 70 + y % 90, 60), (x, y, min(x + 20, size[0]), min(y + 20, size[1])))
    if orientation:
        exif = image.getexif()
        exif[274] = orientation
        image.save(path, quality=90, exif=exif)
    else:
        image.save(path, quality=90)
    return path


@pytest.mark.parametrize("role,expected", [("hero", 1920), ("project", 1600), ("service", 900), ("thumb", 500)])
def test_each_role_gets_its_own_size(tmp_path, role, expected):
    pytest.importorskip("PIL.Image")
    source = _photo(tmp_path / "big.jpg")
    report = images.ImageReport()
    name = images.optimize(source, tmp_path / "out", role=role, report=report)
    assert name.endswith(".webp")
    assert report.rows[-1]["px"].startswith(str(expected))
    assert report.rows[-1]["after"] < report.rows[-1]["before"]


def test_a_small_photo_is_never_blown_up(tmp_path):
    pytest.importorskip("PIL.Image")
    source = _photo(tmp_path / "small.jpg", size=(600, 400))
    report = images.ImageReport()
    images.optimize(source, tmp_path / "out", role="hero", report=report)
    assert report.rows[-1]["px"] == "600×400"


def test_phone_rotation_is_applied(tmp_path):
    pytest.importorskip("PIL.Image")
    source = _photo(tmp_path / "rotated.jpg", size=(1200, 600), orientation=6)
    report = images.ImageReport()
    images.optimize(source, tmp_path / "out", role="project", report=report)
    width, height = report.rows[-1]["px"].split("×")
    assert int(height) > int(width), "휴대폰이 세로로 찍은 사진이 눕혀진 채 나갔습니다"


def test_vectors_are_left_alone(tmp_path):
    report = images.ImageReport()
    name = images.optimize(PHOTO, tmp_path / "out", role="hero", report=report)
    assert name.endswith(".svg") and report.rows[-1]["action"] == "copy"


def test_a_broken_photo_warns_and_keeps_going(tmp_path):
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"this is not a photo")
    report = images.ImageReport()
    name = images.optimize(broken, tmp_path / "out", role="hero", report=report)
    assert name == "broken.jpg"                     # 원본을 그대로 쓴다
    assert report.warnings and "broken.jpg" in report.warnings[0]


def test_build_reports_what_it_did_to_the_photos(tmp_path):
    pytest.importorskip("PIL.Image")
    photos = tmp_path / "photos"
    photos.mkdir()
    _photo(photos / "room.jpg")
    brief_path = tmp_path / "brief.json"
    brief_path.write_text(json.dumps({
        "template": TEMPLATE,
        "company": {"name": "사진테스트", "industry": "인테리어"},
        "hero": {"headline": "사진", "image": "photos/room.jpg"},
        "contact": {"전화": "041-000-0000"},
        "projects": [{"name": "사례", "사진": "photos/room.jpg"}],
    }, ensure_ascii=False), encoding="utf-8")
    result = build_from_file(brief_path, tmp_path / "out", offline=True)
    summary = result.report["images"]
    assert summary["converted"] >= 1
    assert summary["saved_bytes"] > 0
    assert "사진" in (tmp_path / "out" / "납품메모.md").read_text(encoding="utf-8")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert "room.webp" in html


def test_optimization_can_be_turned_off(tmp_path):
    pytest.importorskip("PIL.Image")
    photos = tmp_path / "p"; photos.mkdir()
    _photo(photos / "room.jpg", size=(2400, 1600))
    brief, _ = parse_brief({
        "company": {"name": "원본", "industry": "인테리어"},
        "hero": {"headline": "원본", "image": "p/room.jpg"},
    }, source_path=str(tmp_path / "brief.json"))
    result = build(brief, tmp_path / "out", template_id=TEMPLATE, offline=True, optimize=False)
    assert (result.out_dir / "assets" / "img" / "room.jpg").is_file()


# ── 고객 셋 양산 ──────────────────────────────────────────────────

def _interior_customers() -> list[Path]:
    """이 파일은 인테리어 마스터를 지키는 자리다. 다른 마스터의 견본은 제 파일에서 본다."""
    return [
        path for path in sorted(CUSTOMERS.glob("*.json"))
        if json.loads(path.read_text(encoding="utf-8")).get("template") == TEMPLATE
    ]


@pytest.fixture(scope="module")
def three(tmp_path_factory):
    root = tmp_path_factory.mktemp("demo")
    out = {}
    for path in _interior_customers():
        result = build_from_file(path, root / path.stem, offline=True, clean=True)
        out[path.stem] = result
    return out


def test_all_three_customers_build_from_the_same_master(three):
    assert len(three) == 3
    for name, result in three.items():
        assert result.plan.template.id == TEMPLATE, name
        assert (result.out_dir / "index.html").is_file()


def test_the_three_do_not_look_like_the_same_site(three):
    results = list(three.values())
    primaries = {r.plan.style.primary for r in results}
    assert len(primaries) == 3, f"주색이 겹칩니다: {primaries}"
    aligns = {r.plan.brief.layout.hero_align for r in results}
    layouts = {r.plan.brief.layout.projects for r in results}
    assert len(aligns) > 1 and len(layouts) > 1, "배치 갈래가 하나뿐입니다"
    headlines = {r.plan.content.pages[0].sections[0].heading for r in results}
    assert len(headlines) == 3
    counts = {len(r.plan.brief.projects) for r in results}
    assert len(counts) > 1


def test_each_customer_keeps_its_own_seo(three):
    for name, result in three.items():
        html = (result.out_dir / "index.html").read_text(encoding="utf-8")
        assert result.plan.brief.seo.title in html
        assert result.plan.brief.business.name in html
        data = json.loads(html.split('<script type="application/ld+json">')[1].split("</script>")[0])
        assert data["areaServed"]


def test_layout_options_actually_change_the_markup(three):
    for result in three.values():
        html = (result.out_dir / "index.html").read_text(encoding="utf-8")
        assert f'class="hero hero--{result.plan.brief.layout.hero_align}"' in html
        assert f'pj__grid--{result.plan.brief.layout.projects}' in html


# ── 실제 고객이 보내오는 극단값 ───────────────────────────────────

def _brief(**extra) -> dict:
    data = {
        "template": TEMPLATE,
        "company": {"name": "테스트인테리어", "industry": "인테리어"},
        "hero": {"headline": "한 줄"},
        "contact": {"전화": "041-000-0000", "카카오톡": "https://pf.kakao.com/_x"},
    }
    for key, value in extra.items():
        if key in data and isinstance(data[key], dict) and isinstance(value, dict):
            data[key].update(value)
        else:
            data[key] = value
    return data


def _build(data: dict, out: Path):
    brief, _ = parse_brief(data, source_path=str(EXAMPLES / "x.json"))
    return build(brief, out, template_id=TEMPLATE, offline=True, clean=True)


def test_a_thirty_letter_company_name_still_fits(tmp_path):
    name = "충청남도천안아산종합인테리어리모델링시공디자인주식회사"
    assert len(name) >= 26
    result = _build(_brief(company={"name": name}), tmp_path / "long-name")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert name in html
    title = html.split("<title>")[1].split("</title>")[0]
    assert len(title) <= 70


@pytest.mark.parametrize("headline", [
    "한 줄짜리 제목",
    "두 줄이 되는 제법 긴 제목입니다 여기까지 읽으면 두 줄",
    "세 줄까지 내려가는 아주 긴 제목입니다 인테리어 업체 사장님이 하고 싶은 말이 많을 때 이렇게 됩니다 그래도 깨지면 안 됩니다",
])
def test_hero_titles_of_any_length(headline, tmp_path):
    result = _build(_brief(hero={"headline": headline}), tmp_path / f"h{len(headline)}")
    assert headline in (result.out_dir / "index.html").read_text(encoding="utf-8")


def test_a_three_hundred_letter_introduction(tmp_path):
    story = ("저희는 " + "집을 고치는 일을 오래 해 왔습니다. " * 16).strip()
    assert len(story) >= 300
    result = _build(_brief(about={"paragraphs": [story]}), tmp_path / "wordy")
    assert story in (result.out_dir / "index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("count", [1, 12])
def test_services_from_one_to_twelve(count, tmp_path):
    services = [{"name": f"서비스{n}", "설명": "설명"} for n in range(count)]
    result = _build(_brief(services=services), tmp_path / f"svc{count}")
    assert (result.out_dir / "index.html").read_text(encoding="utf-8").count('class="svc__card"') == count


@pytest.mark.parametrize("count", [1, 15])
def test_projects_from_one_to_fifteen(count, tmp_path):
    projects = [{"name": f"사례{n}", "분류": "아파트", "사진": str(PHOTO)} for n in range(count)]
    result = _build(_brief(projects=projects), tmp_path / f"pj{count}")
    assert (result.out_dir / "index.html").read_text(encoding="utf-8").count('class="pj__cell"') == count


def test_no_reviews_no_faq_leaves_no_empty_box(tmp_path):
    result = _build(_brief(), tmp_path / "bare")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert 'id="testimonials"' not in html and 'id="faq"' not in html
    assert "REVIEWS" not in html and "FAQ" not in html


def test_a_very_long_address_does_not_spill(tmp_path):
    address = "충청남도 천안시 서북구 불당동 한들도시개발지구 " + "가나다라마바사 " * 8 + "101동 1502호"
    result = _build(_brief(contact={"주소": address}), tmp_path / "addr")
    assert address in (result.out_dir / "index.html").read_text(encoding="utf-8")


def test_without_kakao_the_bar_has_two_buttons(tmp_path):
    data = _brief()
    data["contact"].pop("카카오톡")
    result = _build(data, tmp_path / "nokakao")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    bar = html.split('<nav class="mbar"')[1].split("</nav>")[0]
    assert bar.count("<a ") == 2
    assert "카카오톡" not in bar
    assert 'style="--n:2"' in html


def test_without_a_logo_the_initial_is_drawn(tmp_path):
    result = _build(_brief(), tmp_path / "nologo")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert '<span class="mh__mark" aria-hidden="true">' in html
    assert "테" in html.split('class="mh__mark"')[1][:120]


def test_a_project_without_photos_shows_a_named_slot(tmp_path):
    projects = [{"name": "사진 있는 사례", "분류": "아파트", "사진": str(PHOTO)},
                {"name": "사진 없는 사례", "분류": "주택"}]
    result = _build(_brief(projects=projects), tmp_path / "halfpics")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert "[사진 없는 사례 사진]" in html
    assert any("사진" in item for item in result.plan.content.meta["todo"])


# ── 무게 ──────────────────────────────────────────────────────────

def test_the_shipped_site_stays_light(three):
    for name, result in three.items():
        weight = result.report["weight_bytes"]
        assert weight < 1_500_000, f"{name}: 산출물이 {weight/1024:.0f}KB 입니다"
        html = (result.out_dir / "index.html").read_text(encoding="utf-8")
        assert html.count("<script") <= 2          # JSON-LD 와 우리 스크립트뿐
        assert "cdn." not in html and "unpkg" not in html   # 바깥 프레임워크를 끌어오지 않는다
        assert 'loading="lazy"' in html
        assert 'rel="preload" as="image"' in html  # 첫 화면 사진은 미리 받는다


# ── 공개 미리보기 위생 ────────────────────────────────────────────
# 검수용 임시 주소는 고객과 잠재 구매자가 그대로 봅니다.
# 개발자용 문구와 내부 서류가 거기 섞여 나가면 그 자리에서 상품성이 깎입니다.

import subprocess  # noqa: E402
import sys  # noqa: E402

DEV_WORDS = ("--form-action", "form_action", "빌드할 때", "지정하십시오",
             "build_report", "납품메모", "placeholder 또는")


def _dev_words_in(html: str) -> list[str]:
    return [word for word in DEV_WORDS if word in html]


def test_the_form_never_explains_itself_to_the_customer(tmp_path):
    """받는 곳이 없어도 설정 이야기를 손님에게 하지 않는다."""
    result = build_from_file(CUSTOMERS / "a-gonggan.json", tmp_path / "quiet", offline=True)
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert not _dev_words_in(html), _dev_words_in(html)
    assert 'data-noaction="1"' in html            # 새로고침 대신 안내를 띄운다
    note = html.split('class="ct__sent"')[1].split("</p>")[0]
    assert "hidden" in note or "hidden" in html.split('class="ct__sent"')[0][-40:]
    assert "전화" in note and "카카오톡" in note
    assert "--form" not in note and "빌드" not in note


def test_a_real_form_target_turns_the_notice_off(tmp_path):
    brief, _ = load_brief(CUSTOMERS / "a-gonggan.json")
    result = build(brief, tmp_path / "wired", offline=True,
                   form_action="https://formspree.io/f/abcd")
    html = (result.out_dir / "index.html").read_text(encoding="utf-8")
    assert 'action="https://formspree.io/f/abcd"' in html
    form_tag = html.split('<form class="ct__form"')[1].split(">")[0]
    assert "data-noaction" not in form_tag      # 스크립트의 선택자 문자열과 혼동하지 않는다
    assert 'class="ct__sent"' not in html
    assert not _dev_words_in(html)


def test_sample_customers_carry_no_developer_looking_contacts():
    """견본 연락처가 개발용처럼 보이면 쇼케이스가 아니라 테스트 화면이 된다."""
    for path in [EXAMPLES / "master-interior-01.json"] + sorted(CUSTOMERS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        contact = data.get("contact", {})
        flat = json.dumps(contact, ensure_ascii=False)
        assert "000-0000" not in contact.get("전화", ""), f"{path.name}: 전화"
        assert "○○" not in flat, f"{path.name}: 주소에 ○○"
        assert "이메일" not in contact, f"{path.name}: 예시 이메일은 빼 둡니다"
        assert ".example" not in flat, f"{path.name}: .example 주소"
        assert "가상" in data.get("_주의", ""), f"{path.name}: 가상 업체 표시"


def _build_preview_bundle(out: Path) -> Path:
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_previews.py"), str(out)],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return out


def test_preview_bundle_ships_only_what_a_browser_needs(tmp_path):
    site = _build_preview_bundle(tmp_path / "_site")
    for folder in sorted(p for p in site.iterdir() if p.is_dir()):
        names = {child.name for child in folder.iterdir()}
        assert names == {"index.html", "assets"}, f"{folder.name}: {names}"
    assert not list(site.rglob("build_report.json"))
    assert not list(site.rglob("납품메모.md"))
    assert not list(site.rglob("CNAME"))


def test_preview_bundle_keeps_search_engines_out(tmp_path):
    site = _build_preview_bundle(tmp_path / "_site")
    assert "Disallow: /" in (site / "robots.txt").read_text(encoding="utf-8")
    for page in site.rglob("index.html"):
        assert 'content="noindex, nofollow"' in page.read_text(encoding="utf-8"), page


def test_preview_pages_point_at_the_preview_address(tmp_path, monkeypatch):
    monkeypatch.setenv("PREVIEW_BASE", "https://preview.example.test/factory")
    site = _build_preview_bundle(tmp_path / "_site")
    html = (site / "gonggan-interior" / "index.html").read_text(encoding="utf-8")
    assert 'href="https://preview.example.test/factory/gonggan-interior/"' in html
    assert "gonggan-interior.example" not in html      # 없는 도메인을 가리키지 않는다
    assert not _dev_words_in(html)


# ── 새 컴퓨터에서 도는가 ──────────────────────────────────────────
# 저장소를 그대로 받아 온 사람이 무엇을 깔아야 하는지 알 수 있어야 합니다.

def test_the_doctor_runs_and_finds_the_factory():
    done = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "doctor.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    for must in ("파이썬", "Jinja2", "Pillow", "master-interior-01",
                 "master-cleaning-01", "master-company-01"):
        assert must in done.stdout, must


def test_requirements_name_everything_the_factory_imports():
    """Pillow 가 목록에 없으면 새 컴퓨터에서 사진이 조용히 커집니다."""
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for package in ("Jinja2", "PyYAML", "Pillow"):
        assert package in runtime, package
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "-r requirements.txt" in dev
    for package in ("pytest", "playwright"):
        assert package in dev, package
