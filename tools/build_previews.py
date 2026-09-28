"""미리보기 묶음 짓기 — 고객 주문서들을 한 폴더에 나란히 찍는다.

    python tools/build_previews.py _site [주문서 ...]

`PREVIEW_BASE` 를 주면 그 주소를 기준으로 canonical·og:image 를 만듭니다
(기본값은 git remote 에서 뽑은 GitHub Pages 주소).

인자를 주지 않으면 `examples/master-interior-01.json` 과 `examples/customers/*.json`
을 모두 짓습니다. 결과는 이렇게 놓입니다.

    _site/index.html              미리보기 목록
    _site/store/                  판매 홈페이지 (storefront/)
    _site/gonggan-interior/       고객별 사이트 (slug 폴더)
    _site/a-gonggan-interior/
    ...

**템플릿은 건드리지 않습니다.** 다만 미리보기는 공개 주소이므로 세 가지를 합니다.

  · 지어진 HTML 에 `noindex` 한 줄 (가상 업체 데모가 검색에 잡히면 안 됩니다)
  · 고객에게 보일 필요가 없는 내부 파일(견적 보고서·납품 메모·호스팅 설정)은 빼고
    브라우저가 쓰는 것만 올립니다
  · 아직 고객 도메인이 없으므로 canonical·og:image 를 미리보기 주소로 맞춥니다
    — 링크를 공유했을 때 없는 주소를 가리키지 않게 하기 위해서입니다

고객 도메인에 실제로 올릴 때는 이 스크립트를 쓰지 않습니다.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import storefront.build as storefront  # noqa: E402
from factory.intake import load_brief  # noqa: E402
from factory.pipeline import build  # noqa: E402

NOINDEX = '<meta name="robots" content="noindex, nofollow">'
# 브라우저가 실제로 쓰는 것만 올린다. 나머지는 우리 쪽 서류다.
PUBLISH = ("index.html", "assets")
DEFAULT_BRIEFS = [ROOT / "examples" / "master-interior-01.json"] + sorted(
    (ROOT / "examples" / "customers").glob("*.json")
)


def preview_base() -> str:
    """미리보기가 놓이는 주소. 없으면 git remote 에서 GitHub Pages 주소를 만든다."""
    given = os.environ.get("PREVIEW_BASE", "").strip().rstrip("/")
    if given:
        return given
    try:
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return ""
    found = re.search(r"github\.com[:/]([^/]+?)/(.+?)(?:\.git)?$", remote)
    return f"https://{found.group(1)}.github.io/{found.group(2)}" if found else ""


def _keep_only_web_files(folder: Path) -> None:
    """고객에게 보일 필요가 없는 것을 걷어낸다 (보고서·납품메모·호스팅 설정)."""
    for child in list(folder.iterdir()):
        if child.name in PUBLISH:
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()


def _mark_noindex(page: Path) -> None:
    text = page.read_text(encoding="utf-8")
    if NOINDEX in text:
        return
    page.write_text(text.replace("<head>", "<head>\n" + NOINDEX, 1), encoding="utf-8")


def _build_storefront(out: Path, base: str) -> None:
    """판매 홈페이지를 /store/ 에 같이 올린다. 주소는 미리보기 주소에 맞춘다."""
    text = storefront.DATA.read_text(encoding="utf-8")
    if base:
        old = json.loads(text)["urls"]["previewBase"].rstrip("/")
        text = text.replace(old, base)
    data = json.loads(text)
    data["urls"]["self"] = f"{base}/store/" if base else data["urls"]["self"]
    storefront.build(out / "store", data)
    # 미리보기 묶음에서는 폴더마다 브라우저가 쓰는 것만 둔다 (robots 는 뿌리에 하나)
    _keep_only_web_files(out / "store")
    _mark_noindex(out / "store" / "index.html")


def _index_page(rows: list[dict], built_at: str) -> str:
    cards = "\n".join(
        f"""    <li class="card">
      <a href="{html.escape(row['slug'])}/">
        <span class="swatch" style="background:{html.escape(row['primary'])}"></span>
        <span class="name">{html.escape(row['name'])}</span>
        <span class="slug">/{html.escape(row['slug'])}/</span>
        <span class="meta">{html.escape(row['theme'])} · {row['sections']}개 섹션 · {row['weight']}KB</span>
      </a>
    </li>"""
        for row in rows
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{NOINDEX}
<title>website-factory 미리보기</title>
<style>
  :root{{color-scheme:light dark;--bg:#fbfaf8;--fg:#1b1d20;--muted:#6f7278;--line:#e5e2dd;--card:#fff}}
  @media (prefers-color-scheme:dark){{
    :root{{--bg:#131416;--fg:#ececea;--muted:#9a9c9f;--line:#2b2d30;--card:#1a1c1e}}
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.7 "Noto Sans KR",system-ui,sans-serif;
       -webkit-text-size-adjust:100%}}
  .wrap{{width:min(880px,100% - 40px);margin:0 auto;padding:64px 0 80px}}
  h1{{margin:0;font-size:clamp(1.5rem,1.2rem + 1.4vw,2rem);letter-spacing:-.03em}}
  .lede{{margin:.6em 0 0;color:var(--muted)}}
  ul{{list-style:none;margin:40px 0 0;padding:0;display:grid;gap:14px}}
  .card a{{display:grid;grid-template-columns:auto 1fr;grid-template-areas:"s n" "s g" "s m";
          gap:2px 16px;align-items:center;padding:20px 22px;background:var(--card);
          border:1px solid var(--line);border-radius:10px;color:inherit;text-decoration:none;
          transition:border-color .18s,transform .18s}}
  .card a:hover{{border-color:var(--muted);transform:translateY(-2px)}}
  .swatch{{grid-area:s;width:40px;height:40px;border-radius:8px;border:1px solid rgba(0,0,0,.12)}}
  .name{{grid-area:n;font-weight:700;letter-spacing:-.02em}}
  .slug{{grid-area:g;color:var(--muted);font-size:.875rem;font-family:ui-monospace,Menlo,monospace}}
  .meta{{grid-area:m;color:var(--muted);font-size:.8125rem}}
  footer{{margin-top:48px;padding-top:20px;border-top:1px solid var(--line);color:var(--muted);font-size:.8125rem}}
</style>
</head>
<body>
<div class="wrap">
  <h1>website-factory 미리보기</h1>
  <p class="lede"><a href="store/"><strong>판매 홈페이지 보기 →</strong></a></p>
  <p class="lede">검수용 임시 주소입니다. 아래는 모두 <strong>가상 업체</strong> 견본이며,
     실제 업체가 아닙니다. 고객 도메인은 아직 연결하지 않았습니다.</p>
  <ul>
{cards}
  </ul>
  <footer>MASTER_INTERIOR_01 · MASTER_CLEANING_01 · {built_at} 빌드 · 검색 노출 차단(noindex)</footer>
</div>
</body>
</html>
"""


def main(argv: list[str]) -> int:
    out = Path(argv[1] if len(argv) > 1 else "_site")
    briefs = [Path(p) for p in argv[2:]] or DEFAULT_BRIEFS
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    base = preview_base()
    rows: list[dict] = []
    for brief_path in briefs:
        brief, _warnings = load_brief(brief_path)
        slug = brief.slug
        if base:
            # 아직 고객 도메인이 없다. 그 자리에 미리보기 주소를 넣는다.
            brief.site.domain = f"{base}/{slug}"
        result = build(brief, out / "___tmp", offline=True, clean=True)
        target = out / slug
        if target.exists():
            shutil.rmtree(target)
        (out / "___tmp").rename(target)
        _keep_only_web_files(target)
        _mark_noindex(target / "index.html")
        weight = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
        rows.append({
            "slug": slug,
            "name": result.plan.brief.business.name,
            "primary": result.plan.style.primary,
            "theme": result.plan.brief.theme.preset or "직접 지정",
            "sections": len(result.plan.content.pages[0].sections),
            "weight": round(weight / 1024),
        })
        print(f"  {slug:24} {result.plan.brief.business.name:16} {weight/1024:5.0f}KB")

    _build_storefront(out, base)
    print(f"  {'store':24} 판매 홈페이지")

    built_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    (out / "index.html").write_text(_index_page(rows, built_at), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    # 검수용 주소이므로 크롤러를 전부 막는다
    (out / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    print(f"\n{len(rows)}건 → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
