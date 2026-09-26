"""주문서 받기 — JSON / YAML 한 장을 Brief 로 바꾼다.

영업 현장에서 받아 적는 말이 그때그때 다르므로 키 이름을 조금 느슨하게
받는다. `상호`, `업종`, `전화` 같은 한글 키도 그대로 통한다.
빠진 칸은 채워 넣지 않고 비워 둔 채 경고로만 남긴다 — 없는 사실을
지어내면 그게 그대로 상품이 되기 때문이다.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .models import (
    Brand,
    Brief,
    Business,
    Contact,
    FaqEntry,
    GalleryImage,
    Item,
    ReferenceSpec,
    SiteSpec,
    Testimonial,
)


class BriefError(ValueError):
    """주문서를 읽을 수 없다."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("주문서에 문제가 있습니다:\n  - " + "\n  - ".join(problems))


# 같은 뜻으로 쓰이는 키들. 왼쪽이 정식 이름.
_ALIASES: dict[str, tuple[str, ...]] = {
    "business": ("고객", "사업자", "company", "client", "업체"),
    "contact": ("연락처", "contacts", "정보"),
    "site": ("홈페이지", "website", "site_spec", "사이트"),
    "brand": ("브랜드", "design", "스타일", "style"),
    "reference": ("레퍼런스", "ref", "참고", "benchmark"),
    "items": ("메뉴", "서비스", "services", "menu", "products", "요금",
              "시술", "상품", "프로그램", "진료", "업무", "과정", "품목", "수업"),
    "gallery": ("갤러리", "사진", "images", "photos"),
    "testimonials": ("후기", "리뷰", "reviews"),
    "faq": ("자주묻는질문", "questions", "문의"),
    "name": ("상호", "업체명", "title", "브랜드명", "이름"),
    "industry": ("업종", "category", "분야", "sector"),
    "tagline": ("한줄소개", "슬로건", "slogan", "catchphrase"),
    "description": ("소개", "설명", "about", "intro"),
    "founded": ("설립", "개업", "since", "창업"),
    "owner": ("대표", "대표자", "representative"),
    "keywords": ("키워드", "tags", "태그"),
    "phone": ("전화", "전화번호", "tel", "연락처번호"),
    "email": ("이메일", "mail"),
    "address": ("주소", "위치", "location"),
    "hours": ("영업시간", "운영시간", "time", "opening_hours"),
    "map_url": ("지도", "map", "지도링크"),
    "links": ("링크", "sns", "social"),
    "pages": ("페이지", "page_count", "페이지수"),
    "goals": ("목표", "목적", "purpose"),
    "features": ("기능", "요구사항", "needs"),
    "primary_cta": ("행동유도", "cta", "버튼"),
    "domain": ("도메인", "url"),
    "locale": ("언어", "lang"),
    "primary_color": ("주색", "메인색", "color", "brand_color", "대표색"),
    "accent_color": ("강조색", "포인트색", "accent"),
    "mood": ("분위기", "톤", "tone", "느낌"),
    "mode": ("모드", "배경", "theme"),
    "logo_text": ("로고", "logo"),
    "font_preference": ("서체", "font", "글꼴"),
    "url": ("주소", "링크", "site_url"),
    "html_path": ("파일", "file", "local_html", "html"),
    "notes": ("메모", "비고", "note", "요청사항"),
    "summary": ("설명", "desc", "내용"),
    "price": ("가격", "요금", "비용"),
    "quote": ("내용", "본문", "text", "후기내용"),
    "question": ("질문", "q"),
    "answer": ("답", "답변", "a"),
    "src": ("경로", "파일", "file", "이미지"),
    "alt": ("대체문구", "설명"),
    "caption": ("설명", "문구"),
    "title_": (),
}

# 업종 표기를 하나로 모은다.
_INDUSTRY: dict[str, tuple[str, ...]] = {
    "cafe": ("카페", "커피", "coffee", "베이커리", "bakery", "디저트", "브런치"),
    "restaurant": ("식당", "음식점", "레스토랑", "요리", "food", "고깃집", "주점", "바"),
    "clinic": ("병원", "의원", "치과", "한의원", "clinic", "dental", "hospital", "피부과", "정형외과"),
    "salon": ("미용실", "헤어", "네일", "살롱", "hair", "nail", "에스테틱", "속눈썹"),
    "studio": ("스튜디오", "사진", "촬영", "photo", "영상", "studio"),
    "fitness": ("헬스", "체육관", "피트니스", "요가", "필라테스", "gym", "pt", "크로스핏"),
    "legal": ("법률", "변호사", "법무사", "세무", "회계", "노무", "law", "tax", "특허"),
    "academy": ("학원", "교육", "과외", "레슨", "academy", "school", "공부방", "어학"),
    "construction": ("인테리어", "건축", "시공", "리모델링", "설비", "construction", "이사"),
    "realestate": ("부동산", "중개", "공인중개", "realestate", "분양"),
    "shop": ("쇼핑몰", "판매", "소매", "매장", "shop", "store", "공방"),
    "tech": ("it", "소프트웨어", "개발", "saas", "스타트업", "앱", "tech", "solution"),
    "wellness": ("마사지", "테라피", "케어", "요양", "산후조리", "spa", "웰니스"),
}

_KNOWN_FEATURES = {
    "map", "gallery", "form", "pricing", "menu", "reservation", "faq",
    "testimonials", "team", "blog", "notice", "hours", "sns", "process",
}
_FEATURE_ALIASES = {
    "지도": "map", "약도": "map", "갤러리": "gallery", "사진": "gallery",
    "문의폼": "form", "폼": "form", "문의": "form", "상담신청": "form",
    "요금": "pricing", "가격": "pricing", "가격표": "pricing",
    "메뉴": "menu", "메뉴판": "menu",
    "예약": "reservation", "예약하기": "reservation",
    "faq": "faq", "자주묻는질문": "faq", "질문": "faq",
    "후기": "testimonials", "리뷰": "testimonials",
    "팀": "team", "구성원": "team", "의료진": "team", "강사": "team",
    "블로그": "blog", "공지": "notice", "소식": "notice",
    "영업시간": "hours", "시간": "hours", "sns": "sns", "인스타": "sns",
    "절차": "process", "진행과정": "process", "과정": "process",
}
# 분위기 말도 한 벌로 모은다. 여기 있는 낱말만 템플릿·스타일 고르기에 쓰인다.
KNOWN_MOODS = {
    "minimal", "clean", "warm", "cool", "luxury", "trustworthy", "bold",
    "soft", "modern", "natural", "playful", "professional", "youthful", "vivid",
}
_MOOD_ALIASES = {
    "깔끔": "clean", "깔끔한": "clean", "심플": "minimal", "미니멀": "minimal",
    "단정": "clean", "정갈": "clean", "여백": "minimal",
    "따뜻": "warm", "따뜻한": "warm", "온기": "warm", "포근": "warm", "아늘한": "warm",
    "시원": "cool", "차분": "cool", "차분한": "cool", "서늘": "cool",
    "고급": "luxury", "고급스러운": "luxury", "프리미엄": "luxury", "럭셔리": "luxury",
    "신뢰": "trustworthy", "믿음": "trustworthy", "안정": "trustworthy", "정직": "trustworthy",
    "강렬": "bold", "대담": "bold", "임팩트": "bold", "강한": "bold",
    "부드러운": "soft", "은은": "soft", "편안": "soft", "잔잔": "soft",
    "모던": "modern", "현대적": "modern", "세련": "modern", "트렌디": "modern",
    "자연": "natural", "내추럴": "natural", "친환경": "natural", "우드": "natural",
    "귀여운": "playful", "발랄": "playful", "유쾌": "playful", "밝은": "playful",
    "전문": "professional", "전문적": "professional", "정확": "professional",
    "젊은": "youthful", "활기": "vivid", "생기": "vivid", "화려": "vivid",
}

_GOAL_ALIASES = {
    "예약": "reservation", "예약유도": "reservation",
    "문의": "inquiry", "상담": "inquiry", "견적": "inquiry",
    "브랜딩": "brand", "브랜드": "brand", "소개": "brand",
    "판매": "sell", "구매": "sell", "주문": "sell",
    "모집": "recruit", "채용": "recruit",
    "방문": "visit", "내점": "visit", "오시는길": "visit",
}


def _pick(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """정식 키 또는 별칭으로 값을 꺼낸다."""
    if key in data:
        return data[key]
    for alias in _ALIASES.get(key, ()):
        if alias in data:
            return data[alias]
    return default


def _as_dict(value: Any, where: str, problems: list[str]) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    problems.append(f"{where} 는 사전(dict) 이어야 합니다 — 지금은 {type(value).__name__}")
    return {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [v for v in value if v not in ("", None)]
    if isinstance(value, str):
        parts = [p.strip() for p in re.split(r"[,/·\n]", value)]
        return [p for p in parts if p]
    return [value]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def normalize_industry(raw: str) -> str:
    """'치과' → 'clinic'. 모르는 말이면 그대로 소문자로 둔다."""
    token = _text(raw).lower()
    if not token:
        return "general"
    if token in _INDUSTRY:
        return token
    for canonical, words in _INDUSTRY.items():
        for word in words:
            if word in token or token in word:
                return canonical
    return re.sub(r"\s+", "-", token)


def _normalize_tokens(values: list[Any], aliases: dict[str, str]) -> list[str]:
    out: list[str] = []
    for value in values:
        token = _text(value).lower()
        token = aliases.get(token, token)
        if token and token not in out:
            out.append(token)
    return out


def slugify(text: str, fallback_seed: str = "") -> str:
    """ASCII 로 만든다. 한글만 있으면 짧은 지문으로 대신한다."""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()
    slug = re.sub(r"-{2,}", "-", slug)
    if slug:
        return slug[:48]
    seed = (fallback_seed or text).encode("utf-8")
    return "site-" + hashlib.sha1(seed).hexdigest()[:8]


def _domain_label(domain: str) -> str:
    host = re.sub(r"^https?://", "", _text(domain)).split("/")[0]
    host = host.split(":")[0]
    if not host:
        return ""
    labels = [p for p in host.split(".") if p and p != "www"]
    return labels[0] if labels else ""


def _parse_items(raw: Any) -> list[Item]:
    items: list[Item] = []
    for entry in _as_list(raw):
        if isinstance(entry, str):
            items.append(Item(title=_text(entry)))
            continue
        if not isinstance(entry, dict):
            continue
        title = _text(_pick(entry, "name") or entry.get("title"))
        if not title:
            continue
        items.append(
            Item(
                title=title,
                summary=_text(_pick(entry, "summary")),
                price=_text(_pick(entry, "price")),
                icon=_text(entry.get("icon")),
            )
        )
    return items


def _parse_gallery(raw: Any) -> list[GalleryImage]:
    out: list[GalleryImage] = []
    for entry in _as_list(raw):
        if isinstance(entry, str):
            out.append(GalleryImage(src=_text(entry)))
            continue
        if not isinstance(entry, dict):
            continue
        src = _text(_pick(entry, "src") or entry.get("url"))
        if not src:
            continue
        out.append(
            GalleryImage(
                src=src,
                alt=_text(entry.get("alt")),
                caption=_text(entry.get("caption")),
            )
        )
    return out


def _parse_testimonials(raw: Any) -> list[Testimonial]:
    out: list[Testimonial] = []
    for entry in _as_list(raw):
        if isinstance(entry, str):
            out.append(Testimonial(quote=_text(entry)))
            continue
        if not isinstance(entry, dict):
            continue
        quote = _text(_pick(entry, "quote"))
        if not quote:
            continue
        out.append(
            Testimonial(
                quote=quote,
                name=_text(_pick(entry, "name")),
                role=_text(entry.get("role") or entry.get("역할")),
            )
        )
    return out


def _parse_faq(raw: Any) -> list[FaqEntry]:
    out: list[FaqEntry] = []
    for entry in _as_list(raw):
        if not isinstance(entry, dict):
            continue
        q = _text(_pick(entry, "question"))
        a = _text(_pick(entry, "answer"))
        if q and a:
            out.append(FaqEntry(question=q, answer=a))
    return out


def parse_brief(data: dict[str, Any], source_path: str = "") -> tuple[Brief, list[str]]:
    """사전 하나를 Brief 로. (brief, 경고들) 을 돌려준다."""
    problems: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        raise BriefError(["주문서 최상단이 사전(dict) 이 아닙니다"])

    biz_raw = _as_dict(_pick(data, "business"), "business", problems)

    def biz(key: str) -> object:
        """business 블록에 없으면 최상단에서 찾는다."""
        value = _pick(biz_raw, key)
        return value if value not in (None, "", []) else _pick(data, key)

    name = _text(biz("name"))
    if not name:
        problems.append("상호(business.name) 가 없습니다 — 이것만은 있어야 짓습니다")

    industry_raw = _text(biz("industry"))
    if not industry_raw:
        warnings.append("업종이 비어 있어 general 로 둡니다 — 템플릿 선택이 무뎌집니다")

    business = Business(
        name=name,
        industry=normalize_industry(industry_raw),
        tagline=_text(biz("tagline")),
        description=_text(biz("description")),
        founded=_text(biz("founded")),
        owner=_text(biz("owner")),
        keywords=[_text(k) for k in _as_list(biz("keywords"))],
    )

    contact_raw = _as_dict(_pick(data, "contact"), "contact", problems)
    links_raw = _as_dict(_pick(contact_raw, "links"), "contact.links", problems)
    contact = Contact(
        phone=_text(_pick(contact_raw, "phone")),
        email=_text(_pick(contact_raw, "email")),
        address=_text(_pick(contact_raw, "address")),
        hours=_text(_pick(contact_raw, "hours")),
        map_url=_text(_pick(contact_raw, "map_url")),
        links={_text(k): _text(v) for k, v in links_raw.items() if _text(v)},
    )
    if not contact.has_any():
        warnings.append("연락처가 하나도 없습니다 — 문의 유도 섹션이 비게 됩니다")

    site_raw = _as_dict(_pick(data, "site"), "site", problems)
    pages_value = _pick(site_raw, "pages", 1)
    try:
        pages = int(pages_value)
    except (TypeError, ValueError):
        problems.append(f"site.pages 가 숫자가 아닙니다: {pages_value!r}")
        pages = 1
    if pages not in (1, 5):
        warnings.append(f"지금 공장은 1쪽과 5쪽만 찍습니다 — {pages} 쪽은 가까운 쪽으로 맞춥니다")
        pages = 1 if pages < 3 else 5

    features = _normalize_tokens(_as_list(_pick(site_raw, "features")), _FEATURE_ALIASES)
    unknown = [f for f in features if f not in _KNOWN_FEATURES]
    if unknown:
        warnings.append("모르는 기능 요청은 그냥 메모로만 남깁니다: " + ", ".join(unknown))

    site = SiteSpec(
        pages=pages,
        locale=_text(_pick(site_raw, "locale")) or "ko",
        domain=_text(_pick(site_raw, "domain")),
        goals=_normalize_tokens(_as_list(_pick(site_raw, "goals")), _GOAL_ALIASES),
        features=features,
        primary_cta=_text(_pick(site_raw, "primary_cta")),
    )

    brand_raw = _as_dict(_pick(data, "brand"), "brand", problems)
    mode = _text(_pick(brand_raw, "mode")).lower()
    if mode in ("어둡게", "dark", "night"):
        mode = "dark"
    elif mode in ("밝게", "light", "day"):
        mode = "light"
    elif mode:
        warnings.append(f"brand.mode 를 알 수 없어 자동으로 둡니다: {mode!r}")
        mode = ""
    brand = Brand(
        primary_color=_text(_pick(brand_raw, "primary_color")),
        accent_color=_text(_pick(brand_raw, "accent_color")),
        mood=_normalize_tokens(_as_list(_pick(brand_raw, "mood")), _MOOD_ALIASES),
        mode=mode,
        logo_text=_text(_pick(brand_raw, "logo_text")) or name,
        font_preference=_text(_pick(brand_raw, "font_preference")).lower(),
    )

    ref_value = _pick(data, "reference")
    if isinstance(ref_value, str):
        # 레퍼런스를 주소 한 줄로만 적어 오는 경우가 가장 흔하다.
        ref_raw = {"url": ref_value}
    else:
        ref_raw = _as_dict(ref_value, "reference", problems)
    reference = ReferenceSpec(
        url=_text(_pick(ref_raw, "url")),
        html_path=_text(_pick(ref_raw, "html_path")),
        notes=_text(_pick(ref_raw, "notes")),
    )
    if reference.is_empty() and not brand.primary_color:
        warnings.append("레퍼런스도 주색도 없습니다 — 업종 기본 스타일로 짓습니다")

    if problems:
        raise BriefError(problems)

    slug = _text(_pick(data, "slug")) or _domain_label(site.domain) or name
    brief = Brief(
        business=business,
        contact=contact,
        site=site,
        brand=brand,
        reference=reference,
        items=_parse_items(_pick(data, "items")),
        gallery=_parse_gallery(_pick(data, "gallery")),
        testimonials=_parse_testimonials(_pick(data, "testimonials")),
        faq=_parse_faq(_pick(data, "faq")),
        slug=slugify(slug, fallback_seed=name),
        source_path=source_path,
    )
    return brief, warnings


def load_brief(path: str | Path) -> tuple[Brief, list[str]]:
    """.json / .yaml / .yml 파일을 읽어 Brief 로."""
    p = Path(path)
    if not p.exists():
        raise BriefError([f"주문서 파일이 없습니다: {p}"])
    text = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # 선택 의존성
        except ImportError as exc:  # pragma: no cover
            raise BriefError(["YAML 주문서를 읽으려면 pyyaml 이 필요합니다"]) from exc
        data = yaml.safe_load(text)
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BriefError([f"JSON 을 읽을 수 없습니다 ({p.name} {exc.lineno}행): {exc.msg}"]) from exc
    return parse_brief(data or {}, source_path=str(p))
