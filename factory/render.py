"""짓기 — 고른 템플릿과 정한 스타일로 실제 파일을 쓴다.

Jinja 로 HTML 을, 같은 토큰으로 CSS 를 찍는다. 템플릿 디렉터리를 먼저
보고 없으면 _shared 에서 찾으므로, 템플릿은 필요한 조각만 덮어쓰면 된다.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from .catalog import SHARED_DIR
from .models import BuildPlan, SiteContent

# 섹션 종류 → 조각 파일. 여러 종류가 같은 조각을 쓴다.
SECTION_PARTIALS = {
    "hero": "partials/hero.html",
    "about": "partials/about.html",
    "services": "partials/items.html",
    "menu": "partials/items.html",
    "pricing": "partials/items.html",
    "gallery": "partials/gallery.html",
    "testimonials": "partials/testimonials.html",
    "faq": "partials/faq.html",
    "process": "partials/process.html",
    "contact": "partials/contact.html",
    "cta": "partials/cta.html",
}


def _tel(value: str) -> str:
    return re.sub(r"[^0-9+]", "", value or "")


def make_env(template_root: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader([str(template_root), str(SHARED_DIR)]),
        autoescape=select_autoescape(enabled_extensions=("html", "xml"), default=False),
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["tel"] = _tel
    return env


def site_url(domain: str) -> str:
    if not domain:
        return ""
    domain = domain.strip().rstrip("/")
    if "://" not in domain:
        domain = "https://" + domain
    return domain


def _canonical(domain: str, filename: str) -> str:
    base = site_url(domain)
    if not base:
        return ""
    if filename == "index.html":
        return base + "/"
    return f"{base}/{quote(filename)}"


def build_jsonld(plan: BuildPlan) -> str:
    """검색엔진이 읽는 사업체 정보. 주문서에 있는 것만 넣는다."""
    brief = plan.brief
    data: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": brief.business.name,
    }
    if brief.business.description:
        data["description"] = brief.business.description
    if brief.business.tagline and "description" not in data:
        data["description"] = brief.business.tagline
    if brief.contact.phone:
        data["telephone"] = brief.contact.phone
    if brief.contact.email:
        data["email"] = brief.contact.email
    if brief.contact.address:
        data["address"] = {"@type": "PostalAddress", "streetAddress": brief.contact.address}
    if brief.contact.hours:
        data["openingHours"] = brief.contact.hours
    if brief.site.domain:
        data["url"] = site_url(brief.site.domain)
    if brief.contact.map_url:
        data["hasMap"] = brief.contact.map_url
    if brief.gallery:
        base = site_url(brief.site.domain)
        images = []
        for image in brief.gallery[:6]:
            if image.src.startswith(("http://", "https://")) or not base:
                images.append(image.src)
            else:
                images.append(f"{base}/{image.src.lstrip('/')}")
        data["image"] = images
    if brief.contact.links:
        data["sameAs"] = [u for u in brief.contact.links.values() if u.startswith("http")]
    # <script> 안에 그대로 들어가므로 이스케이프를 걸지 않는다.
    # 대신 "</script>" 를 만들 수 있는 조각만 막는다.
    payload = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return Markup(payload)


def og_image(plan: BuildPlan) -> str:
    """대표 이미지 한 장의 절대 주소. 도메인이 없으면 비운다."""
    if not plan.brief.gallery:
        return ""
    src = plan.brief.gallery[0].src
    if src.startswith(("http://", "https://")):
        return src
    base = site_url(plan.brief.site.domain)
    return f"{base}/{src.lstrip('/')}" if base else ""


def base_context(plan: BuildPlan, form_action: str = "") -> dict[str, object]:
    return {
        "brief": plan.brief,
        "style": plan.style,
        "tokens": plan.tokens,
        "template": plan.template,
        "content": plan.content,
        "match": plan.match,
        "section_partials": SECTION_PARTIALS,
        "year": date.today().year,
        "jsonld": build_jsonld(plan),
        "og_image": og_image(plan),
        "form_action": form_action,
        "radius_px": int(plan.style.radius.rstrip("px") or 0),
        "initial": (plan.brief.brand.logo_text or plan.brief.business.name or "·")[:1],
    }


def render_sitemap(content: SiteContent, domain: str) -> str:
    base = site_url(domain)
    today = date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for page in content.pages:
        location = _canonical(domain, page.filename) or page.filename
        lines.append(
            f"  <url><loc>{location}</loc><lastmod>{today}</lastmod>"
            f"<priority>{'1.0' if page.filename == 'index.html' else '0.7'}</priority></url>"
        )
    lines.append("</urlset>")
    if not base:
        lines.insert(1, "<!-- 도메인이 정해지면 loc 를 절대 주소로 바꿔야 합니다 -->")
    return "\n".join(lines) + "\n"


def render_robots(domain: str) -> str:
    base = site_url(domain)
    out = ["User-agent: *", "Allow: /"]
    if base:
        out.append(f"Sitemap: {base}/sitemap.xml")
    return "\n".join(out) + "\n"


def render_site(plan: BuildPlan, out_dir: str | Path, form_action: str = "") -> list[str]:
    """파일을 실제로 쓴다. 쓴 파일 목록(상대 경로)을 돌려준다."""
    if plan.template.root is None:
        raise ValueError("템플릿 경로가 비어 있습니다")
    out = Path(out_dir)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    env = make_env(plan.template.root)
    context = base_context(plan, form_action=form_action)
    written: list[str] = []

    for page in plan.content.pages:
        template = env.get_template(page.filename)
        html = template.render(
            **context,
            page=page,
            canonical=_canonical(plan.brief.site.domain, page.filename),
        )
        (out / page.filename).write_text(html, encoding="utf-8")
        written.append(page.filename)

    css = env.get_template("assets/styles.css.j2").render(**context, page=plan.content.pages[0])
    (out / "assets" / "styles.css").write_text(css, encoding="utf-8")
    written.append("assets/styles.css")

    favicon = env.get_template("assets/favicon.svg.j2").render(**context, page=plan.content.pages[0])
    (out / "assets" / "favicon.svg").write_text(favicon, encoding="utf-8")
    written.append("assets/favicon.svg")

    (out / "sitemap.xml").write_text(
        render_sitemap(plan.content, plan.brief.site.domain), encoding="utf-8"
    )
    written.append("sitemap.xml")
    (out / "robots.txt").write_text(render_robots(plan.brief.site.domain), encoding="utf-8")
    written.append("robots.txt")

    return written
