"""이 컴퓨터에서 공장이 도는지 확인한다.

새 컴퓨터를 잡았을 때 가장 먼저 돌립니다. 무엇이 없는지와 어떻게 채우는지를
한 화면에 적어 줍니다. 아무것도 고치지 않고 보기만 합니다.

    python tools/doctor.py            확인만
    python tools/doctor.py --build    주문서를 전부 실제로 지어 본다 (느림)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OK, WARN, BAD = "  ✓", "  !", "  ✗"
CHROMIUM = ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
            "/opt/pw-browsers/chromium/chrome-linux/chrome")


class Report:
    def __init__(self) -> None:
        self.bad: list[str] = []
        self.warn: list[str] = []

    def ok(self, what: str, note: str = "") -> None:
        print(f"{OK} {what}" + (f"  — {note}" if note else ""))

    def miss(self, what: str, fix: str) -> None:
        print(f"{BAD} {what}\n      → {fix}")
        self.bad.append(what)

    def soft(self, what: str, fix: str) -> None:
        print(f"{WARN} {what}\n      → {fix}")
        self.warn.append(what)


def check_python(r: Report) -> None:
    v = sys.version_info
    text = f"파이썬 {v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= (3, 11):
        r.ok(text)
    else:
        r.miss(text + " — 3.11 이상이 필요합니다", "python.org 에서 3.11 이상을 받으십시오")


def check_packages(r: Report) -> None:
    needed = [
        ("jinja2", "Jinja2", True, "pip install -r requirements.txt"),
        ("yaml", "PyYAML", True, "pip install -r requirements.txt"),
        ("PIL", "Pillow", True, "pip install Pillow  (없으면 사진을 줄이지 못합니다)"),
        ("pytest", "pytest", False, "pip install -r requirements-dev.txt"),
        ("playwright", "playwright", False,
         "pip install playwright && playwright install chromium  (브라우저 검사·썸네일용)"),
    ]
    for module, name, required, fix in needed:
        try:
            mod = import_module(module)
        except ImportError:
            (r.miss if required else r.soft)(f"{name} 없음", fix)
            continue
        version = getattr(mod, "__version__", "") or getattr(mod, "VERSION", "")
        r.ok(name, str(version))


def check_browser(r: Report) -> None:
    try:
        import_module("playwright")
    except ImportError:
        return
    found = next((p for p in CHROMIUM if Path(p).exists()), None)
    if found:
        r.ok("크로미움", found)
        return
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            browser.close()
        r.ok("크로미움", "playwright 기본 경로")
    except Exception as exc:
        r.soft(f"크로미움을 띄울 수 없습니다 ({str(exc).splitlines()[0][:70]})",
               "playwright install chromium")


def check_templates(r: Report) -> None:
    from factory.catalog import load_catalog

    templates = load_catalog()
    ids = sorted(t.id for t in templates)
    masters = [i for i in ids if i.startswith("master-")]
    r.ok(f"템플릿 {len(ids)}벌", " · ".join(ids))
    for master in ("master-interior-01", "master-cleaning-01", "master-company-01"):
        if master not in masters:
            r.miss(f"{master} 이 없습니다", "저장소를 다시 받으십시오 (git pull)")


def check_briefs(r: Report, build: bool) -> None:
    from factory import schema
    from factory.intake import load_brief
    from factory.pipeline import build as build_site

    briefs = [ROOT / "examples" / "master-interior-01.json"]
    briefs += sorted((ROOT / "examples" / "customers").glob("*.json"))
    staging = Path(tempfile.mkdtemp()) if build else None
    for path in briefs:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = schema.validate(data)
        if not result.ok:
            r.miss(f"{path.name} 규격 오류", "; ".join(result.error_lines()[:2]))
            continue
        if not build:
            r.ok(path.name, f"경고 {len(result.warnings)}개")
            continue
        brief, _ = load_brief(path)
        built = build_site(brief, staging / path.stem, offline=True, clean=True)
        weight = sum(f.stat().st_size for f in built.out_dir.rglob("*") if f.is_file())
        r.ok(path.name, f"{built.plan.template.id} · {weight/1024:.0f}KB")
    if staging:
        shutil.rmtree(staging, ignore_errors=True)


def check_storefront(r: Report) -> None:
    import storefront.build as sf

    data = sf.load()
    live = [s for s in data["samples"]["items"] if s.get("status") == "available"]
    r.ok(f"판매 홈페이지 샘플 {len(live)}개", " · ".join(s["title"] for s in live))
    for sample in live:
        shot = ROOT / "storefront" / sample["previewImage"]
        if not shot.is_file():
            r.soft(f"{sample['title']} 썸네일이 없습니다",
                   "python tools/shoot_sample_thumbs.py  (playwright 필요)")
    submission = data.get("submission", {})
    if submission.get("provider") and submission.get("endpoint"):
        r.ok("신청 접수 창구", f"{submission['provider']} → {submission['endpoint'][:48]}")
    else:
        r.soft("신청을 받을 곳이 없습니다 — 제작 상담 신청 버튼이 눌리지 않습니다",
               "storefront.json 의 submission.provider 와 endpoint 를 채우십시오 "
               "(문서/ORDER_FLOW_V1.md 4장)")
    if not any(data["brand"]["contact"].get(k) for k in ("phone", "kakao", "email")):
        r.soft("판매 홈페이지에 공개 연락처가 없습니다",
               "광고를 태우기 전에 storefront/storefront.json 의 brand.contact 를 채우십시오")
    if not data["brand"]["legal"].get("registration"):
        r.soft("사업자 정보가 비어 있습니다 (통신판매 고지)",
               "사업자등록을 마치면 storefront.json 의 brand.legal 을 채우십시오")


def check_git(r: Report) -> None:
    try:
        head = subprocess.run(["git", "log", "-1", "--pretty=%h %s"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        r.soft("git 정보를 읽지 못했습니다", "압축 파일로 받으셨다면 넘어가도 됩니다")
        return
    r.ok("마지막 커밋", head)
    if dirty:
        r.soft(f"저장하지 않은 변경 {len(dirty.splitlines())}개", "git status 로 확인하십시오")


def main(argv: list[str]) -> int:
    build = "--build" in argv
    r = Report()
    print(f"\nwebsite-factory 준비 확인  ({ROOT})\n")

    print("환경")
    check_python(r)
    check_packages(r)
    check_browser(r)

    print("\n공장")
    check_templates(r)
    check_storefront(r)
    check_git(r)

    print("\n주문서" + (" (실제로 지어 봅니다)" if build else ""))
    check_briefs(r, build)

    print()
    if r.bad:
        print(f"못 도는 것 {len(r.bad)}개 — 위의 → 를 먼저 따라 하십시오.")
        return 1
    if r.warn:
        print(f"돌긴 합니다. 다만 {len(r.warn)}개는 채워 두는 편이 좋습니다.")
        return 0
    print("전부 준비되었습니다.  python -m pytest -q  로 한 번 더 확인하실 수 있습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
