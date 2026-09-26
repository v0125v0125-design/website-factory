"""공장에 들어가는 것과 나오는 것의 모양.

주문서(Brief) → 고른 템플릿(TemplateSpec) + 스타일(StyleProfile)
→ 원고(SiteContent) → 지어진 사이트(BuildResult)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------- 주문서


@dataclass
class Business:
    name: str
    industry: str = "general"
    tagline: str = ""
    description: str = ""
    founded: str = ""
    owner: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass
class Contact:
    phone: str = ""
    email: str = ""
    address: str = ""
    hours: str = ""
    map_url: str = ""
    links: dict[str, str] = field(default_factory=dict)  # instagram, kakao, blog ...

    def has_any(self) -> bool:
        return bool(self.phone or self.email or self.address or self.links)


@dataclass
class SiteSpec:
    pages: int = 1
    locale: str = "ko"
    domain: str = ""
    goals: list[str] = field(default_factory=list)     # reservation, inquiry, brand ...
    features: list[str] = field(default_factory=list)  # map, gallery, form, pricing ...
    primary_cta: str = ""


@dataclass
class Brand:
    primary_color: str = ""
    accent_color: str = ""
    mood: list[str] = field(default_factory=list)  # warm, minimal, bold, trustworthy ...
    mode: str = ""                                 # light | dark | ""(자동)
    logo_text: str = ""
    font_preference: str = ""                      # sans | serif | rounded


@dataclass
class ReferenceSpec:
    url: str = ""
    html_path: str = ""
    notes: str = ""

    def is_empty(self) -> bool:
        return not (self.url or self.html_path)


@dataclass
class Item:
    """메뉴 한 줄, 서비스 하나, 요금 하나."""

    title: str
    summary: str = ""
    price: str = ""
    icon: str = ""


@dataclass
class GalleryImage:
    src: str
    alt: str = ""
    caption: str = ""


@dataclass
class Testimonial:
    quote: str
    name: str = ""
    role: str = ""


@dataclass
class FaqEntry:
    question: str
    answer: str


@dataclass
class Brief:
    """고객 정보 한 벌. 여기까지가 사람이 채우는 부분이다."""

    business: Business
    contact: Contact = field(default_factory=Contact)
    site: SiteSpec = field(default_factory=SiteSpec)
    brand: Brand = field(default_factory=Brand)
    reference: ReferenceSpec = field(default_factory=ReferenceSpec)
    items: list[Item] = field(default_factory=list)
    gallery: list[GalleryImage] = field(default_factory=list)
    testimonials: list[Testimonial] = field(default_factory=list)
    faq: list[FaqEntry] = field(default_factory=list)
    slug: str = ""
    source_path: str = ""

    @property
    def name(self) -> str:
        return self.business.name


# ---------------------------------------------------------------- 스타일


@dataclass
class Fonts:
    heading: str
    body: str
    google: list[str] = field(default_factory=list)  # ["Noto Serif KR:600"]

    def google_href(self) -> str:
        if not self.google:
            return ""
        families = "&".join(
            "family=" + spec.replace(" ", "+").replace(":", ":wght@")
            for spec in self.google
        )
        return f"https://fonts.googleapis.com/css2?{families}&display=swap"


@dataclass
class StyleProfile:
    """레퍼런스에서 읽어 낸 것 + 주문서에서 못 박은 것을 합친 결과."""

    primary: str
    accent: str
    mode: str                  # light | dark
    fonts: Fonts
    radius: str                # "0px" | "6px" | "18px" ...
    density: str               # compact | regular | airy
    hero: str                  # split | center | image
    background: str = ""       # 레퍼런스에서 가져온 바탕색 (없으면 자동)
    source: str = "preset"     # reference:<url> | brief | preset:<name>
    confidence: float = 0.0    # 0.0 ~ 1.0
    evidence: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- 템플릿


@dataclass
class PageSpec:
    slug: str          # "" 이면 index
    title: str
    nav_label: str
    sections: list[str]
    description: str = ""

    @property
    def filename(self) -> str:
        return "index.html" if not self.slug else f"{self.slug}.html"


@dataclass
class TemplateSpec:
    id: str
    name: str
    summary: str
    page_count: int
    pages: list[PageSpec]
    industries: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    hero: str = "split"
    density: str = "regular"
    root: Path | None = None

    def page(self, slug: str) -> PageSpec | None:
        for p in self.pages:
            if p.slug == slug:
                return p
        return None


@dataclass
class MatchScore:
    template: TemplateSpec
    score: float
    reasons: list[str] = field(default_factory=list)
    penalties: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- 원고


@dataclass
class Section:
    kind: str                       # hero, about, services, gallery ...
    heading: str = ""
    subheading: str = ""
    body: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Page:
    spec: PageSpec
    title: str
    description: str
    sections: list[Section]
    nav_label: str = ""

    @property
    def filename(self) -> str:
        return self.spec.filename


@dataclass
class SiteContent:
    pages: list[Page]
    nav: list[dict[str, str]]
    meta: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------- 결과


@dataclass
class BuildPlan:
    brief: Brief
    template: TemplateSpec
    style: StyleProfile
    match: MatchScore
    tokens: dict[str, str]
    content: SiteContent


@dataclass
class BuildResult:
    plan: BuildPlan
    out_dir: Path
    files: list[str]
    report: dict[str, Any]
