"""SITE_CONFIG_SCHEMA_V1 — 고객 데이터의 규격.

관리자 웹이 만들어지기 전까지 **이 구조가 호환성 기준**이다.
칸 이름을 함부로 바꾸지 않는다. 늘리는 것은 되지만, 있는 이름을 다른 뜻으로
쓰거나 지우면 이미 만든 고객 주문서가 전부 깨진다.

여기서 하는 일은 두 가지다.

  · 반드시 있어야 하는 것이 없으면 **오류** — 짓지 않는다.
  · 있으면 좋은 것이 없거나 모양이 이상하면 **경고** — 짓되 알려 준다.

오류 글은 사람이 읽고 바로 고칠 수 있게 쓴다. "어디가" 와 "무엇을" 이 함께 있어야 한다.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any

from .intake import aliases_for, pick

SCHEMA_VERSION = "SITE_CONFIG_SCHEMA_V1"

# 규격에 적힌 이름 → 공장 안에서 쓰는 이름.
# 바깥(관리자 웹·주문서)에는 왼쪽 이름이 규격이고, 오른쪽은 구현 사정이다.
CANON = {
    "company": "business",
    "services": "items",
    "reviews": "testimonials",
    "about": "about_block",
}

# 최상단에서 받는 칸. 이름을 바꾸면 안 되는 목록이기도 하다.
TOP_LEVEL = (
    "template", "slug", "company", "hero", "strengths", "services", "about",
    "projects", "process", "reviews", "faq", "contact", "site", "theme",
    "layout", "seo", "gallery", "reference", "brand",
)


def _key(name: str) -> str:
    return CANON.get(name, name)


def get(data: dict, name: str, default: Any = None) -> Any:
    """규격 이름으로 값을 꺼낸다 (별칭과 내부 이름을 함께 본다)."""
    return pick(data, _key(name), default)


def _names(name: str) -> tuple[str, ...]:
    return aliases_for(_key(name))
# 배열이어야 하는 칸
ARRAYS = ("strengths", "services", "projects", "process", "reviews", "faq", "gallery")
# 반드시 사전이어야 하는 칸
OBJECTS = ("company", "contact", "site", "seo", "layout", "brand")
# 사전으로도, 한 줄 글로도 받는 칸
#   about: "소개글" / hero: "대표문구" / theme: "charcoal" / reference: "https://..."
OBJECT_OR_TEXT = ("about", "hero", "theme", "reference")

KNOWN_THEMES = ("charcoal", "beige", "black", "green", "sky", "mist")


@dataclass
class Problem:
    where: str
    what: str
    hint: str = ""

    def line(self, mark: str) -> str:
        text = f"  {mark} {self.where} — {self.what}"
        return text + (f"\n      → {self.hint}" if self.hint else "")


@dataclass
class Result:
    errors: list[Problem] = field(default_factory=list)
    warnings: list[Problem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error_lines(self) -> list[str]:
        return [f"{p.where} — {p.what}" + (f" ({p.hint})" if p.hint else "") for p in self.errors]

    def warning_lines(self) -> list[str]:
        return [f"{p.where} — {p.what}" + (f" ({p.hint})" if p.hint else "") for p in self.warnings]

    def report(self) -> str:
        out = [f"[{SCHEMA_VERSION}]"]
        if self.errors:
            out.append("\n오류 — 이대로는 짓지 않습니다")
            out += [p.line("✗") for p in self.errors]
        if self.warnings:
            out.append("\n확인할 것 — 짓기는 합니다")
            out += [p.line("!") for p in self.warnings]
        if not self.errors and not self.warnings:
            out.append("\n규격에 맞습니다.")
        return "\n".join(out)


def _has(data: dict, key: str) -> bool:
    value = get(data, key)
    return value not in (None, "", [], {})


def _text_of(data: dict, key: str) -> str:
    value = get(data, key)
    return value.strip() if isinstance(value, str) else ""


def _entries(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check_rows(
    result: Result, rows: list[Any], where: str, required: tuple[str, ...], label: str
) -> None:
    for index, row in enumerate(rows):
        spot = f"{where}[{index}]"
        if isinstance(row, str) and required == ("name",):
            continue          # 문자열 한 줄만 적어 온 것도 받는다
        if not isinstance(row, dict):
            result.errors.append(Problem(spot, f"{label} 한 건은 사전이어야 합니다",
                                         "예: { \"name\": \"...\", \"설명\": \"...\" }"))
            continue
        for key in required:
            if _has(row, key) or (key == "name" and row.get("title")):
                continue
            names = ("name", "이름", "title", "제목") if key == "name" else _names(key)[:4]
            result.errors.append(
                Problem(f"{spot}.{key}", f"{label}에 '{key}' 칸이 없습니다",
                        "이 중 아무 이름이나 됩니다: " + ", ".join(names))
            )


def validate(data: Any) -> Result:
    """주문서 한 장을 규격에 비춰 본다."""
    result = Result()
    if not isinstance(data, dict):
        result.errors.append(Problem("(최상단)", "주문서가 사전(dict) 이 아닙니다"))
        return result

    # 1. 모르는 칸 — 오타를 잡아 준다
    known = {name for key in TOP_LEVEL for name in _names(key)}
    known |= {"name", "industry", "tagline", "description", "founded", "owner", "keywords"}
    known |= {name for key in ("name", "industry", "tagline", "description", "founded", "owner",
                               "items", "testimonials", "gallery", "keywords")
              for name in aliases_for(key)}
    for key in data:
        if key.startswith("_") or key in known:
            continue
        near = difflib.get_close_matches(key, sorted(known), n=1, cutoff=0.7)
        result.warnings.append(
            Problem(key, "공장이 모르는 칸이라 무시합니다",
                    f"혹시 {near[0]} 입니까?" if near else "")
        )

    # 2. 모양
    for key in ARRAYS:
        value = get(data, key)
        if value is not None and not isinstance(value, list):
            result.errors.append(Problem(key, "목록(배열)이어야 합니다",
                                         "예: [ { ... }, { ... } ]"))
    for key in OBJECTS:
        value = get(data, key)
        if value is not None and not isinstance(value, dict):
            result.errors.append(Problem(key, "사전(dict)이어야 합니다",
                                         "예: { \"...\": \"...\" }"))
    for key in OBJECT_OR_TEXT:
        value = get(data, key)
        if value is not None and not isinstance(value, (dict, str)):
            result.errors.append(Problem(key, "사전이거나 한 줄 글이어야 합니다"))

    def block(name: str) -> dict:
        value = get(data, name)
        return value if isinstance(value, dict) else {}

    company, contact, hero = block("company"), block("contact"), block("hero")
    site, seo = block("site"), block("seo")

    # 3. 반드시 있어야 하는 것
    if not (_text_of(company, "name") or _text_of(data, "name")):
        result.errors.append(
            Problem("company.name", "상호가 없습니다 — 이것만은 있어야 짓습니다",
                    "쓸 수 있는 이름: " + ", ".join(aliases_for("name")[:5]))
        )

    # 4. 있어야 팔리는 것
    if not (_text_of(company, "industry") or _text_of(data, "industry")):
        result.warnings.append(Problem("company.industry", "업종이 비어 있습니다",
                                       "템플릿·말씨·기본 색을 고르는 데 씁니다"))
    if not _text_of(contact, "phone"):
        result.warnings.append(Problem("contact.phone", "전화번호가 없습니다",
                                       "전화 버튼과 모바일 하단 바가 비게 됩니다"))
    if not _text_of(contact, "address"):
        result.warnings.append(Problem("contact.address", "주소가 없습니다",
                                       "지역 검색과 지도 안내에 씁니다"))
    if not (_text_of(hero, "headline") or _text_of(company, "tagline") or _text_of(data, "tagline")):
        result.warnings.append(Problem("hero.headline", "첫 화면 문구가 없어 상호로 대신합니다",
                                       "여기가 고객이 3초 안에 읽는 한 줄입니다"))
    if not _text_of(hero, "image"):
        result.warnings.append(Problem("hero.image", "대표 사진이 없습니다",
                                       "시공 사례 사진을 대신 씁니다 — 그것도 없으면 빈 자리로 남습니다"))

    # 5. 목록 한 건씩
    _check_rows(result, _entries(get(data, "services")), "services", ("name",), "서비스")
    _check_rows(result, _entries(get(data, "strengths")), "strengths", ("name",), "강점")
    _check_rows(result, _entries(get(data, "process")), "process", ("name",), "절차")
    _check_rows(result, _entries(get(data, "projects")), "projects", ("name",), "시공 사례")
    _check_rows(result, _entries(get(data, "reviews")), "reviews", ("quote",), "후기")
    _check_rows(result, _entries(get(data, "faq")), "faq", ("question", "answer"), "질문")

    for index, row in enumerate(_entries(get(data, "projects"))):
        if not isinstance(row, dict):
            continue
        # 전·후 짝(before/after)도 사진이다 — 청소·방역처럼 비교로 파는 업종이 그렇다.
        has_shot = any(_has(row, k) for k in ("image", "images", "before", "after"))
        if not has_shot:
            result.warnings.append(
                Problem(f"projects[{index}].image", "사례에 사진이 없습니다",
                        "사례 사진은 홈페이지에서 가장 값이 나가는 자리입니다")
            )
        elif _has(row, "before") != _has(row, "after"):
            result.warnings.append(
                Problem(f"projects[{index}]", "작업 전·후 중 한 장만 있습니다",
                        "둘 다 있어야 비교로 보여 줍니다 — 한 장만 있으면 그 한 장만 나갑니다")
            )

    # 6. 쪽수·테마·배치
    pages = pick(site, "pages")
    if pages not in (None, "") and str(pages) not in ("1", "5"):
        result.warnings.append(Problem("site.pages", f"지금 공장은 1쪽과 5쪽만 찍습니다 (받은 값: {pages})",
                                       "가까운 쪽으로 맞춥니다"))
    theme = get(data, "theme")
    preset = theme if isinstance(theme, str) else (pick(theme, "preset") if isinstance(theme, dict) else "")
    if isinstance(preset, str) and preset and preset.lower() not in KNOWN_THEMES:
        result.warnings.append(Problem("theme", f"모르는 테마 이름입니다: {preset}",
                                       "쓸 수 있는 것: " + ", ".join(KNOWN_THEMES)))

    # 7. 검색에 나가는 글자
    title = _text_of(seo, "title")
    description = _text_of(seo, "description")
    if not title:
        result.warnings.append(Problem("seo.title", "검색 제목이 없어 상호로 만듭니다",
                                       "'천안 인테리어 ○○' 처럼 지역을 넣으면 검색에 잡힙니다"))
    elif len(title) > 70:
        result.warnings.append(Problem("seo.title", f"검색 제목이 {len(title)}자입니다",
                                       "70자가 넘으면 검색 결과에서 잘립니다"))
    if not description:
        result.warnings.append(Problem("seo.description", "검색 설명이 없습니다",
                                       "검색 결과에 보이는 두 줄입니다"))
    elif len(description) > 160:
        result.warnings.append(Problem("seo.description", f"검색 설명이 {len(description)}자입니다",
                                       "160자가 넘으면 잘립니다"))
    return result
