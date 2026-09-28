"""판매 홈페이지 짓기 — 데이터 한 장(storefront.json)을 정적 사이트로.

    python storefront/build.py _site/store

고객 템플릿 엔진(factory/)과 책임을 나눕니다. 여기는 **우리 상품을 파는 페이지**,
factory/ 는 **고객에게 납품할 홈페이지**를 찍는 곳입니다. 서로 건드리지 않습니다.
공유하는 것은 사진 최적화(factory.images) 하나뿐입니다.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape  # noqa: E402
from markupsafe import Markup, escape  # noqa: E402

DATA = HERE / "storefront.json"


def jsonld(site: dict) -> str:
    """구조화 데이터 — 화면에 적은 것만 넣습니다. 후기·평점은 없으므로 넣지 않습니다."""
    base = site["urls"]["self"].rstrip("/") + "/"
    offers = [
        {
            "@type": "Offer",
            "name": f"{p['name']} — {p['summary']}",
            "price": "".join(c for c in p["price"] if c.isdigit()),
            "priceCurrency": "KRW",
            "url": base + "#pricing",
            "description": p["audience"],
        }
        for p in site["products"]["items"]
    ]
    graph = [
        {
            "@type": "WebSite",
            "@id": base + "#website",
            "url": base,
            "name": site["brand"]["name"],
            "inLanguage": "ko",
            "description": site["seo"]["description"],
        },
        {
            "@type": "Service",
            "@id": base + "#service",
            "name": site["brand"]["tagline"],
            "serviceType": "홈페이지 제작",
            "areaServed": {"@type": "Country", "name": "대한민국"},
            "provider": {"@id": base + "#website"},
            "offers": offers,
        },
        {
            "@type": "FAQPage",
            "@id": base + "#faq",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f["q"],
                    "acceptedAnswer": {"@type": "Answer", "text": f["a"]},
                }
                for f in site["faq"]["items"]
            ],
        },
    ]
    text = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    return text.replace("</", "<\\/")


def load(path: Path = DATA) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def env() -> Environment:
    environment = Environment(
        loader=FileSystemLoader(str(HERE / "templates")),
        autoescape=select_autoescape(enabled_extensions=("html", "xml"), default=False),
        undefined=StrictUndefined,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    environment.filters["nl2br"] = lambda text: Markup("<br>").join(
        escape(line) for line in str(text).split("\n")
    )
    environment.filters["tel"] = lambda text: "".join(c for c in str(text) if c.isdigit() or c == "+")
    return environment


def build(out_dir: str | Path, data: dict | None = None) -> Path:
    site = data or load()
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)

    environment = env()
    context = {
        "site": site,
        "brand": site["brand"],
        "theme": site["theme"],
        "seo": site["seo"],
        "urls": site["urls"],
        "year": date.today().year,
        "jsonld": Markup(jsonld(site)),
        "channels": [c for c in (
            ("전화", site["brand"]["contact"].get("phone", ""), "tel"),
            ("카카오톡", site["brand"]["contact"].get("kakao", ""), "kakao"),
            ("이메일", site["brand"]["contact"].get("email", ""), "mail"),
        ) if c[1]],
        "available_samples": [s for s in site["samples"]["items"] if s.get("status") == "available"],
    }

    (out / "index.html").write_text(
        environment.get_template("index.html").render(**context), encoding="utf-8"
    )
    (out / "assets" / "styles.css").write_text(
        environment.get_template("styles.css.j2").render(**context), encoding="utf-8"
    )

    samples = HERE / "assets" / "samples"
    if samples.is_dir():
        shutil.copytree(samples, out / "assets" / "samples")

    base = site["urls"]["self"].rstrip("/")
    noindex = bool(site["seo"].get("noindex"))
    (out / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n" if noindex
        else f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n",
        encoding="utf-8",
    )
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{base}/</loc><lastmod>{date.today().isoformat()}</lastmod></url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )
    return out


def main(argv: list[str]) -> int:
    out = build(argv[1] if len(argv) > 1 else "_site/store")
    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"판매 홈페이지 → {out}  ({total / 1024:.0f}KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
