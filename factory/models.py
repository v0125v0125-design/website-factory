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
    kakao: str = ""        # 카카오톡 채널/오픈채팅 주소
    links: dict[str, str] = field(default_factory=dict)  # instagram, blog ...

    def has_any(self) -> bool:
        return bool(self.phone or self.email or self.address or self.kakao or self.links)

    def tel_href(self) -> str:
        import re as _re

        return "tel:" + _re.sub(r"[^0-9+]", "", self.phone) if self.phone else ""


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
    """메뉴 한 줄, 서비스 하나, 시공 분야 하나."""

    title: str
    summary: str = ""
    price: str = ""
    icon: str = ""
    image: str = ""
    bullets: list[str] = field(default_factory=list)


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
    rating: int = 0        # 0 이면 별을 그리지 않는다
    project: str = ""      # "32평 아파트" 처럼 어떤 일이었는지


@dataclass
class FaqEntry:
    question: str
    answer: str


@dataclass
class Strength:
    """왜 이 업체인가 — 숫자 하나와 한 줄."""

    title: str
    summary: str = ""
    number: str = ""       # "1,200" · "15"
    unit: str = ""         # "건" · "년"
    icon: str = ""


@dataclass
class Project:
    """시공 사례 하나. 인테리어 홈페이지에서 가장 중요한 덩어리."""

    title: str
    category: str = ""     # 아파트 · 상가 · 주택
    location: str = ""     # 천안 불당동
    summary: str = ""
    image: str = ""        # 대표 사진
    images: list[str] = field(default_factory=list)  # 추가 사진
    year: str = ""
    size: str = ""         # 32평

    def all_images(self) -> list[str]:
        out = [self.image] if self.image else []
        return out + [i for i in self.images if i and i != self.image]


@dataclass
class ProcessStep:
    """상담부터 완료까지 한 칸."""

    title: str
    summary: str = ""
    duration: str = ""     # "1~2일"
    step: str = ""         # 비우면 순번을 자동으로 넣는다


@dataclass
class HeroSpec:
    """첫 화면. 비우면 회사 정보에서 끌어온다."""

    headline: str = ""
    subline: str = ""
    image: str = ""
    badges: list[str] = field(default_factory=list)   # "A/S 2년" 같은 짧은 신뢰 조각
    cta_label: str = ""
    cta_href: str = ""
    sub_cta_label: str = ""
    sub_cta_href: str = ""


@dataclass
class AboutSpec:
    """업체 소개. 비우면 business.description 을 쓴다."""

    heading: str = ""
    paragraphs: list[str] = field(default_factory=list)
    image: str = ""
    facts: list[tuple[str, str]] = field(default_factory=list)
    signature: str = ""    # "대표 김○○" 처럼 맺는 한 줄


@dataclass
class Seo:
    """검색·공유에 나가는 글자. 지역명이 여기 들어간다."""

    title: str = ""
    description: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    favicon: str = ""
    region: str = ""       # "천안" · "천안·아산"
    keywords: list[str] = field(default_factory=list)


@dataclass
class Theme:
    """같은 템플릿의 색 버전. 관리자 웹에서 고르게 될 칸."""

    preset: str = ""       # charcoal | beige | black | green
    primary: str = ""
    accent: str = ""
    background: str = ""
    surface: str = ""
    mode: str = ""
    radius: str = ""
    font: str = ""         # sans | serif

    def is_empty(self) -> bool:
        return not any(
            (self.preset, self.primary, self.accent, self.background,
             self.surface, self.mode, self.radius, self.font)
        )


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
    # 아래는 마스터 템플릿용으로 늘린 칸. 없으면 없는 대로 돈다.
    hero: HeroSpec = field(default_factory=HeroSpec)
    about: AboutSpec = field(default_factory=AboutSpec)
    strengths: list[Strength] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    process: list[ProcessStep] = field(default_factory=list)
    seo: Seo = field(default_factory=Seo)
    theme: Theme = field(default_factory=Theme)
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
    background: str = ""       # 레퍼런스나 테마에서 가져온 바탕색 (없으면 자동)
    surface: str = ""          # 띠 배경으로 쓸 면 색 (없으면 주색에서 만든다)
    source: str = "preset"     # reference:<url> | brief | preset:<name> | theme:<name>
    confidence: float = 0.0    # 0.0 ~ 1.0
    evidence: list[str] = field(default_factory=list)
    # theme 이 직접 못 박는 토큰들. 맨 마지막에 덮어쓴다.
    overrides: dict[str, str] = field(default_factory=dict)


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
