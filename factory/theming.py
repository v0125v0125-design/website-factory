"""스타일 정하기 — 레퍼런스에서 본 것 + 주문서에서 못 박은 것 → 한 벌의 토큰.

순서는 언제나 이것이다.

  1. 고객이 직접 지정한 값 (주문서의 주색·모드·서체)
  2. 레퍼런스에서 실제로 읽어 낸 값
  3. 업종 기본값

앞의 것이 있으면 뒤의 것을 쓰지 않는다. 무엇을 왜 썼는지는
StyleProfile.evidence 에 남겨 견적서에 그대로 붙일 수 있게 한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import colorkit
from .models import Brand, Brief, Fonts, StyleProfile
from .reference import ReferenceFindings

KOREAN_SANS = '"Noto Sans KR"'
KOREAN_SERIF = '"Noto Serif KR"'


@dataclass(frozen=True)
class Preset:
    primary: str
    accent: str
    mood: tuple[str, ...]
    radius_px: int
    density: str
    hero: str
    serif_heading: bool = False


# 업종 기본값. 레퍼런스가 없거나 못 읽었을 때 여기서 출발한다.
PRESETS: dict[str, Preset] = {
    "cafe":         Preset("#8a5a2b", "#c9a227", ("warm", "natural"), 14, "airy", "image", True),
    "restaurant":   Preset("#a83e2c", "#e3a008", ("warm", "bold"), 8, "regular", "image", True),
    "clinic":       Preset("#0f6f8a", "#22b8cf", ("clean", "trustworthy"), 10, "regular", "split"),
    "salon":        Preset("#8e5572", "#d9a5b3", ("soft", "luxury"), 20, "airy", "image"),
    "studio":       Preset("#1f2430", "#c0a062", ("minimal", "luxury"), 2, "airy", "image"),
    "fitness":      Preset("#e8590c", "#1f2937", ("bold", "vivid"), 6, "compact", "image"),
    "legal":        Preset("#123a5f", "#9a7b4f", ("professional", "trustworthy"), 4, "regular", "split", True),
    "academy":      Preset("#2b6cb0", "#f59f00", ("clean", "youthful"), 12, "regular", "split"),
    "construction": Preset("#3f4a5a", "#f59f00", ("professional", "bold"), 4, "compact", "split"),
    "realestate":   Preset("#1f6f54", "#c99a2e", ("trustworthy", "clean"), 8, "regular", "split"),
    "shop":         Preset("#111827", "#ef4444", ("modern", "minimal"), 10, "regular", "image"),
    "tech":         Preset("#4c6ef5", "#12b886", ("modern", "clean"), 12, "regular", "split"),
    "wellness":     Preset("#6f9e7e", "#d1a054", ("soft", "natural"), 18, "airy", "image"),
    "general":      Preset("#2f6fed", "#12b886", ("clean", "modern"), 10, "regular", "split"),
}

# 분위기 말이 치수를 조금 밀고 당긴다.
_MOOD_RADIUS = {"minimal": -6, "luxury": -4, "modern": 0, "playful": 10, "soft": 6, "bold": -2}
_MOOD_DENSITY = {"minimal": "airy", "luxury": "airy", "soft": "airy", "bold": "compact", "vivid": "compact"}

_DENSITY_SCALE = {
    # 섹션 위아래 여백, 블록 간격, 본문 크기, 제목 배율
    "compact": ("64px", "20px", "16px", "1.0"),
    "regular": ("96px", "28px", "17px", "1.08"),
    "airy":    ("136px", "36px", "18px", "1.16"),
}

_SERIF_FALLBACK = ("Playfair Display", "Noto Serif KR", "Nanum Myeongjo", "Gowun Batang", "Song Myung")


def preset_for(industry: str) -> Preset:
    return PRESETS.get(industry, PRESETS["general"])


def _usable_brand_color(findings: ReferenceFindings) -> tuple[str, str] | None:
    """레퍼런스 색 중 주색으로 쓸 만한 것 하나. (색, 근거)"""
    if findings.theme_color:
        _, saturation, lightness = colorkit.to_hsl(colorkit.parse(findings.theme_color))
        if saturation >= 0.12 and 0.08 <= lightness <= 0.86:
            return findings.theme_color, f"레퍼런스 theme-color {findings.theme_color}"

    best: tuple[float, str, int] | None = None
    for color, count in findings.brand_colors:
        _, saturation, lightness = colorkit.to_hsl(colorkit.parse(color))
        if saturation < 0.18 or not (0.12 <= lightness <= 0.78):
            continue
        # 많이 쓰였고, 너무 흐리지 않은 색을 좋아한다.
        weight = count * 1.0 + saturation * 2.0
        if best is None or weight > best[0]:
            best = (weight, color, count)
    if best:
        _, color, count = best
        return color, f"레퍼런스에서 {count}번 쓰인 색 {color}"
    return None


def _usable_accent(findings: ReferenceFindings, primary: str) -> tuple[str, str] | None:
    """주색과 색조가 다르고 또렷한 색 하나. 글자색으로 쓰인 짙은 색은 뺀다."""
    primary_hue, _, _ = colorkit.to_hsl(colorkit.parse(primary))
    best: tuple[float, str] | None = None
    for color, count in findings.brand_colors:
        hue, saturation, lightness = colorkit.to_hsl(colorkit.parse(color))
        if saturation < 0.25 or not (0.25 <= lightness <= 0.75):
            continue
        distance = abs((hue - primary_hue + 180) % 360 - 180)
        if distance < 12:
            continue
        weight = distance / 180.0 * 2.0 + saturation + count * 0.05
        if best is None or weight > best[0]:
            best = (weight, color)
    if best:
        return best[1], f"레퍼런스 보조색 {best[1]}"
    return None


def _decide_mode(brand: Brand, findings: ReferenceFindings) -> tuple[str, str]:
    if brand.mode:
        return brand.mode, f"주문서 지정: {brand.mode} 모드"
    background = findings.page_background()
    if background and colorkit.is_dark(background):
        return "dark", f"레퍼런스 바탕 {background} 이 어두움"
    if background:
        return "light", f"레퍼런스 바탕 {background} 이 밝음"
    return "light", "기본 밝은 배경"


def _quote(family: str) -> str:
    return f'"{family}"' if " " in family and not family.startswith('"') else family


def _decide_fonts(brief: Brief, findings: ReferenceFindings, preset: Preset) -> tuple[Fonts, list[str]]:
    notes: list[str] = []
    want = brief.brand.font_preference
    google: list[str] = []

    display = ""
    for family in findings.google_fonts:
        if "Noto Sans" in family:
            continue
        display = family
        break
    if not display:
        for family in findings.fonts:
            if family.lower().startswith("noto sans"):
                continue
            display = family
            break

    serif_wanted = want in ("serif", "명조", "바탕") or (
        not want and (preset.serif_heading or findings.serif_hint)
    )

    if want in ("sans", "고딕"):
        serif_wanted = False
        notes.append("주문서가 고딕을 지정")
    elif want in ("serif", "명조", "바탕"):
        notes.append("주문서가 명조를 지정")
    elif findings.serif_hint:
        notes.append("레퍼런스가 명조 계열을 씀")

    korean = KOREAN_SERIF if serif_wanted else KOREAN_SANS
    korean_name = korean.strip('"')
    google.append(f"{korean_name}:400;500;700")
    if korean_name != "Noto Sans KR":
        google.append("Noto Sans KR:400;500")

    heading_parts: list[str] = []
    if display and display.lower() not in ("noto serif kr", "noto sans kr"):
        heading_parts.append(_quote(display))
        # 레퍼런스가 쓰던 라틴 서체는 구글 폰트에 있을 때만 불러온다.
        if display in findings.google_fonts or display in _SERIF_FALLBACK:
            google.insert(0, f"{display}:600;700")
        notes.append(f"제목 서체를 레퍼런스에서 가져옴: {display}")
    heading_parts.append(korean)
    heading_parts.append("serif" if serif_wanted else "sans-serif")

    body_stack = f'{KOREAN_SANS}, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif'
    if serif_wanted and want in ("serif", "명조", "바탕"):
        body_stack = f'{KOREAN_SERIF}, {body_stack}'
        if "Noto Serif KR:400;500;700" not in google:
            google.append("Noto Serif KR:400;500")

    fonts = Fonts(heading=", ".join(heading_parts), body=body_stack, google=google)
    return fonts, notes


def _decide_radius(brief: Brief, findings: ReferenceFindings, preset: Preset, moods: list[str]) -> tuple[int, str]:
    radius = findings.dominant_radius()
    if radius is not None:
        return int(round(min(radius, 32))), f"레퍼런스 모서리 {radius:g}px"
    value = preset.radius_px
    shifted = value
    for mood in moods:
        shifted += _MOOD_RADIUS.get(mood, 0)
    shifted = max(0, min(28, shifted))
    if shifted != value:
        return shifted, f"업종 기본 {value}px 에 분위기({', '.join(moods)}) 반영 → {shifted}px"
    return value, f"업종 기본 모서리 {value}px"


def _decide_density(findings: ReferenceFindings, preset: Preset, moods: list[str]) -> tuple[str, str]:
    padding = findings.max_block_padding
    if padding >= 112:
        return "airy", f"레퍼런스 블록 여백 {padding:g}px (넉넉함)"
    if padding and padding < 56:
        return "compact", f"레퍼런스 블록 여백 {padding:g}px (빽빽함)"
    for mood in moods:
        if mood in _MOOD_DENSITY:
            return _MOOD_DENSITY[mood], f"분위기 {mood} → {_MOOD_DENSITY[mood]}"
    if padding:
        return "regular", f"레퍼런스 블록 여백 {padding:g}px"
    return preset.density, f"업종 기본 간격 {preset.density}"


def build_style(brief: Brief, findings: ReferenceFindings | None = None) -> StyleProfile:
    """주문서 + 레퍼런스 → StyleProfile."""
    findings = findings or ReferenceFindings()
    preset = preset_for(brief.business.industry)
    moods = brief.brand.mood or list(preset.mood)
    evidence: list[str] = []
    signals = 0

    if brief.brand.primary_color and colorkit.is_color(brief.brand.primary_color):
        primary = colorkit.to_hex(colorkit.parse(brief.brand.primary_color))
        evidence.append(f"주색: 주문서 지정 {primary}")
        source = "brief"
        signals += 3
    else:
        found = _usable_brand_color(findings)
        if found:
            primary, why = found
            evidence.append("주색: " + why)
            source = f"reference:{findings.source}" if findings.source else "reference"
            signals += 3
        else:
            primary = preset.primary
            evidence.append(f"주색: {brief.business.industry} 업종 기본 {primary}")
            source = f"preset:{brief.business.industry}"
            if findings.problems:
                evidence.append("레퍼런스를 못 읽음 — " + findings.problems[0])

    if brief.brand.accent_color and colorkit.is_color(brief.brand.accent_color):
        accent = colorkit.to_hex(colorkit.parse(brief.brand.accent_color))
        evidence.append(f"강조색: 주문서 지정 {accent}")
        signals += 1
    else:
        found_accent = _usable_accent(findings, primary)
        if found_accent:
            accent, why = found_accent
            evidence.append("강조색: " + why)
            signals += 1
        else:
            accent = preset.accent
            evidence.append(f"강조색: 업종 기본 {accent}")

    mode, mode_why = _decide_mode(brief.brand, findings)
    evidence.append("배경: " + mode_why)
    if brief.brand.mode or findings.page_background():
        signals += 1

    fonts, font_notes = _decide_fonts(brief, findings, preset)
    evidence.extend("서체: " + note for note in font_notes)
    if findings.google_fonts or findings.fonts or brief.brand.font_preference:
        signals += 1

    radius, radius_why = _decide_radius(brief, findings, preset, moods)
    evidence.append("모서리: " + radius_why)
    if findings.dominant_radius() is not None:
        signals += 1

    density, density_why = _decide_density(findings, preset, moods)
    evidence.append("간격: " + density_why)
    if findings.max_block_padding:
        signals += 1

    background = ""
    reference_background = findings.page_background()
    if reference_background:
        _, _, bg_lightness = colorkit.to_hsl(colorkit.parse(reference_background))
        bg_chroma = colorkit.chroma(reference_background)
        if mode == "light" and bg_lightness >= 0.90 and bg_chroma <= 0.12:
            background = reference_background
        elif mode == "dark" and bg_lightness <= 0.22 and bg_chroma <= 0.30:
            background = reference_background
        if background:
            evidence.append(f"바탕색: 레퍼런스 {background} 를 그대로 씀")
            signals += 1

    hero = preset.hero
    if brief.gallery:
        hero = "image"
        evidence.append("히어로: 사진이 있어 이미지형")
    elif findings.images >= 6:
        hero = "image"
        evidence.append(f"히어로: 레퍼런스 이미지 {findings.images}장 → 이미지형")
    else:
        evidence.append(f"히어로: 업종 기본 {hero}형")

    confidence = round(min(1.0, signals / 8.0), 2)
    return StyleProfile(
        primary=primary,
        accent=accent,
        mode=mode,
        fonts=fonts,
        radius=f"{radius}px",
        density=density,
        hero=hero,
        background=background,
        source=source,
        confidence=confidence,
        evidence=evidence,
    )


def build_tokens(style: StyleProfile) -> dict[str, str]:
    """StyleProfile → CSS 커스텀 속성 한 벌."""
    palette = colorkit.build_palette(
        style.primary, mode=style.mode, accent=style.accent, background=style.background or None
    )
    section_pad, gap, body_size, heading_scale = _DENSITY_SCALE[style.density]
    radius_px = int(style.radius.rstrip("px") or 0)

    tokens = {f"color-{k}": v for k, v in palette.as_dict().items()}
    tokens.update(
        {
            "font-heading": style.fonts.heading,
            "font-body": style.fonts.body,
            "radius": style.radius,
            "radius-sm": f"{max(0, radius_px // 2)}px",
            "radius-lg": f"{min(48, radius_px * 2) if radius_px else 0}px",
            "radius-pill": "999px" if radius_px >= 10 else style.radius,
            "section-pad": section_pad,
            "gap": gap,
            "text-base": body_size,
            "heading-scale": heading_scale,
            "container": "1120px" if style.density != "compact" else "1040px",
            "shadow": (
                "0 18px 40px rgba(0,0,0,.30)"
                if style.mode == "dark"
                else "0 14px 34px rgba(16,24,40,.09)"
            ),
            # 밝은 사진 위에도 흰 글자가 읽혀야 한다. 글이 놓이는 아래쪽을
            # 특히 짙게 덮어, 어떤 사진이 와도 대비 4.5 를 넘도록 한다.
            "overlay": (
                "linear-gradient(180deg, rgba(0,0,0,.38) 0%, rgba(0,0,0,.62) 45%,"
                " rgba(0,0,0,.86) 100%)"
                if style.mode == "dark"
                else "linear-gradient(180deg, rgba(0,0,0,.28) 0%, rgba(0,0,0,.56) 45%,"
                " rgba(0,0,0,.80) 100%)"
            ),
        }
    )
    return tokens


def contrast_audit(tokens: dict[str, str]) -> dict[str, float]:
    """지어 놓은 색이 실제로 읽히는지 다시 잰다."""
    pairs = {
        "text/background": ("color-text", "color-background"),
        "muted/background": ("color-text-muted", "color-background"),
        "text/surface": ("color-text", "color-surface"),
        "on-primary/primary": ("color-on-primary", "color-primary"),
        "primary/background": ("color-primary", "color-background"),
    }
    out: dict[str, float] = {}
    for label, (a, b) in pairs.items():
        if a in tokens and b in tokens:
            out[label] = round(colorkit.contrast(tokens[a], tokens[b]), 2)
    return out
