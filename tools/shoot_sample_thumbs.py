"""샘플 썸네일 찍기 — 판매 페이지 카드에 쓸 실제 화면.

    python tools/shoot_sample_thumbs.py

지어진 샘플 사이트를 브라우저로 열어 위쪽 한 화면을 찍고,
`storefront/assets/samples/<slug>.webp` 로 저장합니다. 그림이 아니라
실제로 파는 홈페이지의 첫 화면이므로, 샘플을 고칠 때마다 다시 찍습니다.
playwright 가 있어야 돕니다(없으면 그냥 건너뜁니다).
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from factory.images import ImageReport, optimize  # noqa: E402
from factory.pipeline import build_from_file  # noqa: E402

OUT = ROOT / "storefront" / "assets" / "samples"
CHROMIUM = ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
            "/opt/pw-browsers/chromium/chrome-linux/chrome")
SHOTS = [
    ("interior-01", ROOT / "examples" / "master-interior-01.json"),
    ("cleaning-01", ROOT / "examples" / "customers" / "d-bareungyeol.json"),
]
WIDTH, HEIGHT = 1440, 1000          # 위쪽 한 화면 (첫인상이 카드에 실린다)


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright 가 없어 건너뜁니다 — 기존 썸네일을 그대로 씁니다")
        return 0
    executable = next((p for p in CHROMIUM if Path(p).exists()), None)
    OUT.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp())

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=executable) if executable else pw.chromium.launch()
        for slug, brief in SHOTS:
            result = build_from_file(brief, staging / slug, offline=True, clean=True)
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
            page.goto((result.out_dir / "index.html").as_uri())
            page.wait_for_timeout(900)
            raw = staging / f"{slug}.png"
            page.screenshot(path=str(raw))
            page.close()
            report = ImageReport()
            name = optimize(raw, OUT, role="about", report=report)   # 1200px 폭이면 카드에 넉넉하다
            if name != f"{slug}.webp":
                (OUT / name).rename(OUT / f"{slug}.webp")
            row = report.rows[-1]
            print(f"  {slug}.webp  {row['after'] / 1024:.0f}KB  {row['px']}")
        browser.close()
    shutil.rmtree(staging, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
