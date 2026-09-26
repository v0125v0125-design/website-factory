"""원고 만들기 — 주문서에 있는 사실만으로 각 섹션을 채운다.

한 가지 규칙만 지킨다: **없는 사실은 지어내지 않는다.**
"직접 볶은 원두", "20년 경력" 같은 말은 고객이 적어 준 것이 아니면
쓰지 않는다. 재료가 없으면 섹션을 빼거나, 사람이 채울 자리를
`[…]` 로 남기고 채울 목록(todo)에 적는다.

머리말·버튼 글자처럼 사실 주장이 아닌 말은 업종에 맞춰 골라 쓴다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Brief, Page, PageSpec, Section, SiteContent, StyleProfile, TemplateSpec

PLACEHOLDER = "[{}]"


@dataclass
class Lexicon:
    """업종마다 다른 머리말 한 벌. 사실이 아니라 이름표다."""

    items_heading: str = "서비스"
    items_label: str = "서비스"
    about_heading: str = "소개"
    gallery_heading: str = "사진"
    contact_heading: str = "문의"
    process_heading: str = "진행 방법"
    cta: str = "문의하기"
    hero_kicker: str = ""


LEXICONS: dict[str, Lexicon] = {
    "cafe": Lexicon("메뉴", "메뉴", "저희 공간", "매장 사진", "찾아오시는 길", "이용 안내", "메뉴 보기"),
    "restaurant": Lexicon("메뉴", "메뉴", "저희 가게", "음식과 공간", "찾아오시는 길", "예약 안내", "예약 문의"),
    "clinic": Lexicon("진료 과목", "진료", "병원 소개", "내부 둘러보기", "진료 문의", "진료 절차", "진료 예약"),
    "salon": Lexicon("시술 안내", "시술", "샵 소개", "작업 사진", "예약 문의", "예약 절차", "예약하기"),
    "studio": Lexicon("촬영 상품", "상품", "스튜디오 소개", "포트폴리오", "촬영 문의", "촬영 절차", "촬영 문의"),
    "fitness": Lexicon("프로그램", "프로그램", "센터 소개", "시설 사진", "상담 문의", "등록 절차", "체험 신청"),
    "legal": Lexicon("업무 분야", "분야", "사무소 소개", "사무소 전경", "상담 문의", "상담 절차", "상담 신청"),
    "academy": Lexicon("수업 안내", "과정", "학원 소개", "수업 현장", "입학 문의", "수강 절차", "상담 신청"),
    "construction": Lexicon("시공 범위", "공정", "회사 소개", "시공 사례", "견적 문의", "시공 절차", "견적 문의"),
    "realestate": Lexicon("중개 업무", "업무", "사무소 소개", "매물 사진", "매물 문의", "거래 절차", "매물 문의"),
    "shop": Lexicon("취급 품목", "품목", "브랜드 소개", "제품 사진", "주문 문의", "주문 방법", "주문 문의"),
    "tech": Lexicon("제공 서비스", "서비스", "회사 소개", "화면 미리보기", "도입 문의", "도입 절차", "도입 문의"),
    "wellness": Lexicon("케어 프로그램", "프로그램", "센터 소개", "공간 사진", "예약 문의", "이용 절차", "예약 문의"),
    "general": Lexicon(),
}

CTA_BY_GOAL = {
    "reservation": "예약 문의",
    "inquiry": "상담 신청",
    "sell": "구매 문의",
    "visit": "오시는 길",
    "recruit": "지원 문의",
    "brand": "자세히 보기",
}


def lexicon_for(industry: str) -> Lexicon:
    return LEXICONS.get(industry, LEXICONS["general"])


def _first_sentence(text: str, limit: int = 120) -> str:
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?。])\s+|\n+", text.strip())
    head = parts[0].strip() if parts else text.strip()
    return head if len(head) <= limit else head[: limit - 1].rstrip() + "…"


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text.strip()) if p.strip()]


@dataclass
class CopyEngine:
    """규칙 기반 원고 담당. 나중에 사람이 고쳐 쓰거나 다른 엔진으로 갈아 끼울 자리."""

    brief: Brief
    style: StyleProfile
    todo: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.lex = lexicon_for(self.brief.business.industry)

    # ---------------------------------------------------------- 도움말

    def _need(self, what: str, where: str) -> str:
        """채울 자리를 남기고 목록에 적는다."""
        note = f"{where}: {what}"
        if note not in self.todo:
            self.todo.append(note)
        return PLACEHOLDER.format(what)

    def cta_label(self) -> str:
        if self.brief.site.primary_cta:
            return self.brief.site.primary_cta
        for goal in self.brief.site.goals:
            if goal in CTA_BY_GOAL:
                return CTA_BY_GOAL[goal]
        return self.lex.cta

    def cta_href(self) -> str:
        contact = self.brief.contact
        if contact.phone:
            return "tel:" + re.sub(r"[^0-9+]", "", contact.phone)
        if contact.email:
            return "mailto:" + contact.email
        return "#contact"

    # ---------------------------------------------------------- 섹션들

    def hero(self) -> Section:
        biz = self.brief.business
        heading = biz.tagline or biz.name
        sub = _first_sentence(biz.description)
        if not sub:
            sub = self._need("한 줄 소개", "히어로")
        data = {
            "name": biz.name,
            "cta_label": self.cta_label(),
            "cta_href": self.cta_href(),
            # 제목이 한 줄 소개로 들어가면 상호를 그 위에 작게 올린다.
            "kicker": biz.name if biz.tagline else "",
            "image": self.brief.gallery[0].src if self.brief.gallery else "",
            "facts": [f for f in (self.brief.contact.hours, self.brief.contact.address) if f][:2],
        }
        if self.style.hero == "image" and not data["image"]:
            data["image_placeholder"] = self._need("대표 사진 1장", "히어로")
        return Section(kind="hero", heading=heading, subheading=sub, data=data)

    def about(self) -> Section:
        biz = self.brief.business
        body_paragraphs = _paragraphs(biz.description)
        if not body_paragraphs:
            body_paragraphs = [self._need("소개 글 2~3문장", "소개")]
        facts: list[tuple[str, str]] = []
        if biz.founded:
            facts.append(("시작", biz.founded))
        if biz.owner:
            facts.append(("대표", biz.owner))
        if self.brief.contact.hours:
            facts.append(("영업시간", self.brief.contact.hours))
        if self.brief.contact.address:
            facts.append(("위치", self.brief.contact.address))
        return Section(
            kind="about",
            heading=self.lex.about_heading,
            subheading=biz.tagline,
            data={"paragraphs": body_paragraphs, "facts": facts},
        )

    def items(self, kind: str = "services") -> Section | None:
        if not self.brief.items:
            self.skipped.append(f"{kind}: 항목이 하나도 없어 뺐습니다")
            return None
        rows = [
            {"title": i.title, "summary": i.summary, "price": i.price, "icon": i.icon}
            for i in self.brief.items
        ]
        return Section(
            kind=kind,
            heading=self.lex.items_heading,
            data={"items": rows, "label": self.lex.items_label,
                  "has_price": any(i.price for i in self.brief.items)},
        )

    def gallery(self) -> Section | None:
        if not self.brief.gallery:
            self.skipped.append("gallery: 사진이 없어 뺐습니다")
            return None
        images = [
            {"src": g.src, "alt": g.alt or f"{self.brief.business.name} 사진", "caption": g.caption}
            for g in self.brief.gallery
        ]
        return Section(kind="gallery", heading=self.lex.gallery_heading, data={"images": images})

    def testimonials(self) -> Section | None:
        if not self.brief.testimonials:
            self.skipped.append("testimonials: 받은 후기가 없어 뺐습니다")
            return None
        rows = [{"quote": t.quote, "name": t.name, "role": t.role} for t in self.brief.testimonials]
        return Section(kind="testimonials", heading="고객 후기", data={"items": rows})

    def faq(self) -> Section | None:
        if not self.brief.faq:
            self.skipped.append("faq: 질문·답이 없어 뺐습니다")
            return None
        rows = [{"question": f.question, "answer": f.answer} for f in self.brief.faq]
        return Section(kind="faq", heading="자주 묻는 질문", data={"items": rows})

    def process(self) -> Section | None:
        # 절차는 사실이라 지어낼 수 없다. 요청이 있으면 자리만 만든다.
        if "process" not in self.brief.site.features:
            return None
        steps = [
            {"step": str(n), "title": self._need(f"{n}단계 제목", "진행 방법"), "summary": ""}
            for n in (1, 2, 3)
        ]
        return Section(kind="process", heading=self.lex.process_heading, data={"steps": steps})

    def contact(self) -> Section:
        contact = self.brief.contact
        rows: list[tuple[str, str, str]] = []
        if contact.phone:
            rows.append(("전화", contact.phone, "tel:" + re.sub(r"[^0-9+]", "", contact.phone)))
        if contact.email:
            rows.append(("이메일", contact.email, "mailto:" + contact.email))
        if contact.address:
            rows.append(("주소", contact.address, contact.map_url))
        if contact.hours:
            rows.append(("영업시간", contact.hours, ""))
        for label, url in contact.links.items():
            rows.append((label, url, url))
        if not rows:
            rows.append(("전화", self._need("대표 연락처", "문의"), ""))
        wants_form = "form" in self.brief.site.features
        wants_map = "map" in self.brief.site.features
        if wants_map and not contact.map_url:
            self.todo.append("문의: 지도 링크(네이버/카카오 지도 공유 주소)")
        return Section(
            kind="contact",
            heading=self.lex.contact_heading,
            data={
                "rows": rows,
                "form": wants_form,
                "map_url": contact.map_url,
                "map_requested": wants_map,
                "cta_label": self.cta_label(),
                "cta_href": self.cta_href(),
            },
        )

    def cta(self) -> Section:
        return Section(
            kind="cta",
            heading=self.brief.business.tagline or f"{self.brief.business.name}에 문의해 보세요",
            data={"cta_label": self.cta_label(), "cta_href": self.cta_href(),
                  "phone": self.brief.contact.phone},
        )

    # ---------------------------------------------------------- 조립

    def build_section(self, kind: str) -> Section | None:
        builders = {
            "hero": self.hero,
            "about": self.about,
            "services": lambda: self.items("services"),
            "menu": lambda: self.items("menu"),
            "pricing": lambda: self.items("pricing"),
            "gallery": self.gallery,
            "testimonials": self.testimonials,
            "faq": self.faq,
            "process": self.process,
            "contact": self.contact,
            "cta": self.cta,
        }
        builder = builders.get(kind)
        if builder is None:
            self.skipped.append(f"{kind}: 공장이 모르는 섹션이라 뺐습니다")
            return None
        return builder()


def _nav_label(spec: PageSpec, engine: CopyEngine) -> str:
    """메뉴 이름을 업종 말씨로 바꾼다 — 치과의 '서비스' 는 '진료 과목' 이다."""
    if not spec.slug:
        return spec.nav_label
    first = spec.sections[0] if spec.sections else ""
    if first in ("services", "menu", "pricing"):
        return engine.lex.items_heading
    if first == "gallery":
        return engine.lex.gallery_heading
    if first == "contact":
        return engine.lex.contact_heading
    if first == "about":
        return engine.lex.about_heading
    return spec.nav_label


def _page_description(brief: Brief, spec: PageSpec, label: str = "") -> str:
    base = brief.business.tagline or _first_sentence(brief.business.description)
    place = brief.contact.address.split()[0] if brief.contact.address else ""
    bits = [brief.business.name]
    if spec.slug:
        bits.append(label or spec.title)
    if place:
        bits.append(place)
    if base:
        bits.append(base)
    return " · ".join(dict.fromkeys(b for b in bits if b))[:155]


def build_content(brief: Brief, template: TemplateSpec, style: StyleProfile) -> SiteContent:
    """템플릿이 요구하는 섹션을 주문서 재료로 채운다."""
    engine = CopyEngine(brief=brief, style=style)
    pages: list[Page] = []

    # 쪽이 여러 장이면 연락처 유도는 문의 페이지로 보낸다.
    has_contact_page = any(p.slug == "contact" for p in template.pages)

    for spec in template.pages:
        nav_label = _nav_label(spec, engine)
        sections: list[Section] = []
        for kind in spec.sections:
            section = engine.build_section(kind)
            if section is None:
                continue
            if has_contact_page and section.data.get("cta_href") == "#contact":
                section.data["cta_href"] = "contact.html"
            sections.append(section)

        kinds = [s.kind for s in sections]
        primary = spec.sections[0] if spec.sections else ""
        lost_primary = bool(spec.slug) and primary not in kinds
        if not sections or lost_primary:
            # 속장의 본체가 빠졌으면 장 자체를 내지 않는다.
            # 유도 띠만 남은 빈 페이지가 팔려 나가는 것보다 없는 편이 낫다.
            engine.skipped.append(
                f"{spec.slug or 'index'}.html: {primary} 재료가 없어 이 장을 빼고 메뉴에서도 지웠습니다"
            )
            engine.todo.append(
                f"{nav_label} 페이지: {primary} 재료(사진·항목)를 받으면 다시 지으면 살아납니다"
            )
            continue

        title = brief.business.name if not spec.slug else f"{nav_label} · {brief.business.name}"
        pages.append(
            Page(
                spec=spec,
                title=title,
                description=spec.description or _page_description(brief, spec, nav_label),
                sections=sections,
                nav_label=nav_label,
            )
        )

    nav = [
        {"label": p.nav_label, "href": p.filename if p.spec.slug else "index.html"}
        for p in pages
    ]
    if len(pages) == 1:
        # 원페이지는 섹션 앵커로 메뉴를 만든다.
        labels = {
            "about": engine.lex.about_heading,
            "services": engine.lex.items_heading,
            "menu": engine.lex.items_heading,
            "pricing": engine.lex.items_heading,
            "gallery": engine.lex.gallery_heading,
            "testimonials": "후기",
            "faq": "자주 묻는 질문",
            "contact": engine.lex.contact_heading,
        }
        nav = [
            {"label": labels[s.kind], "href": f"#{s.kind}"}
            for s in pages[0].sections
            if s.kind in labels
        ]

    cta_label = engine.cta_label()
    return SiteContent(
        pages=pages,
        nav=nav,
        meta={
            "todo": engine.todo,
            "skipped": engine.skipped,
            # 메뉴에 같은 말이 이미 있으면 머리의 버튼은 접는다.
            "head_cta": cta_label not in [link["label"] for link in nav],
            "cta_label": cta_label,
            "cta_href": engine.cta_href(),
            "lexicon": engine.lex.__dict__,
        },
    )
