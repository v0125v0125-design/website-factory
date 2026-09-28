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
    "strengths": "partials/strengths.html",
    "projects": "partials/projects.html",
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
    links = list(brief.contact.links.values())
    if brief.contact.kakao:
        links.append(brief.contact.kakao)
    if links:
        data["sameAs"] = [u for u in links if u.startswith("http")]
    if brief.seo.region:
        data["areaServed"] = [r.strip() for r in brief.seo.region.replace("·", ",").split(",") if r.strip()]
        if isinstance(data.get("address"), dict):
            data["address"]["addressLocality"] = data["areaServed"][0]
    # <script> 안에 그대로 들어가므로 이스케이프를 걸지 않는다.
    # 대신 "</script>" 를 만들 수 있는 조각만 막는다.
    payload = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return Markup(payload)


def absolute(plan: BuildPlan, path: str) -> str:
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        return path
    base = site_url(plan.brief.site.domain)
    return f"{base}/{path.lstrip('/')}" if base else ""


def seo_block(plan: BuildPlan, page) -> dict[str, str]:
    """검색·공유에 나가는 글자 한 벌. seo 블록이 있으면 그것이 이긴다."""
    seo = plan.brief.seo
    biz = plan.brief.business
    name = biz.name
    if seo.title:
        title = seo.title
    else:
        head = f"{seo.region} {name}".strip() if seo.region else name
        if page.spec.slug:
            head = f"{page.nav_label} · {head}"
        title = f"{head} | {biz.tagline}" if biz.tagline and not page.spec.slug else head
    description = seo.description or page.description
    return {
        "title": title[:70],
        "description": description[:160],
        "og_title": seo.og_title or title[:70],
        "og_description": (seo.og_description or description)[:160],
        "og_image": absolute(plan, seo.og_image) or og_image(plan),
        "keywords": ", ".join(seo.keywords),
        "region": seo.region,
        "favicon": seo.favicon,
    }


def og_image(plan: BuildPlan) -> str:
    """대표 이미지 한 장의 절대 주소. 도메인이 없으면 비운다."""
    candidates = [plan.brief.hero.image]
    candidates += [p.image for p in plan.brief.projects]
    candidates += [g.src for g in plan.brief.gallery]
    src = next((c for c in candidates if c), "")
    if not src:
        return ""
    return absolute(plan, src)


def hero_image_path(plan: BuildPlan) -> str:
    """첫 화면에 깔리는 사진. 미리 받아 두면 첫인상이 빨라진다."""
    for page in plan.content.pages:
        for section in page.sections:
            if section.kind == "hero":
                return str(section.data.get("image") or "")
    return ""


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
        "hero_preload": hero_image_path(plan),
        "favicon_href": "assets/favicon.svg",
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
            seo=seo_block(plan, page),
            canonical=_canonical(plan.brief.site.domain, page.filename),
        )
        (out / page.filename).write_text(html, encoding="utf-8")
        written.append(page.filename)

    first = plan.content.pages[0]
    css = env.get_template("assets/styles.css.j2").render(
        **context, page=first, seo=seo_block(plan, first)
    )
    (out / "assets" / "styles.css").write_text(css, encoding="utf-8")
    written.append("assets/styles.css")

    # 파비콘 파일을 준 고객이면 그것을 쓰고, 없으면 주색과 머리글자로 하나 그린다.
    given_favicon = plan.brief.seo.favicon
    if given_favicon and not given_favicon.startswith(("http://", "https://")):
        context["favicon_href"] = given_favicon
    else:
        favicon = env.get_template("assets/favicon.svg.j2").render(
            **context, page=first, seo=seo_block(plan, first)
        )
        (out / "assets" / "favicon.svg").write_text(favicon, encoding="utf-8")
        written.append("assets/favicon.svg")

    (out / "sitemap.xml").write_text(
        render_sitemap(plan.content, plan.brief.site.domain), encoding="utf-8"
    )
    written.append("sitemap.xml")
    (out / "robots.txt").write_text(render_robots(plan.brief.site.domain), encoding="utf-8")
    written.append("robots.txt")

    return written
