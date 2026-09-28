"""색 계산기 — 레퍼런스에서 뽑은 색 하나로 쓸 수 있는 팔레트를 만든다.

바깥 의존성 없이 돌아간다. 하는 일은 세 가지다.

  · 색을 읽고 쓴다 (#abc, #aabbcc, rgb(...))
  · 밝기와 대비를 재서 글자가 읽히는지 본다 (WCAG 2.1)
  · 주색 하나에서 표면색·보조색·강조색을 만들어 낸다
"""

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass

_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGB_FUNC = re.compile(
    r"rgba?\(\s*([0-9.]+%?)\s*[, ]\s*([0-9.]+%?)\s*[, ]\s*([0-9.]+%?)", re.I
)

RGB = tuple[int, int, int]


class ColorError(ValueError):
    """읽을 수 없는 색 표기."""


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _channel(token: str) -> int:
    token = token.strip()
    if token.endswith("%"):
        return round(_clamp(float(token[:-1]) / 100.0) * 255)
    return max(0, min(255, round(float(token))))


def parse(color: str) -> RGB:
    """'#f4a', '#ff44aa', 'rgb(255 68 170)' 를 (r, g, b) 로."""
    if not isinstance(color, str):
        raise ColorError(f"색이 문자열이 아닙니다: {color!r}")
    text = color.strip()
    m = _HEX.match(text)
    if m:
        digits = m.group(1)
        if len(digits) in (3, 4):
            digits = "".join(ch * 2 for ch in digits[:3])
        digits = digits[:6]
        return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
    m = _RGB_FUNC.match(text)
    if m:
        return (_channel(m.group(1)), _channel(m.group(2)), _channel(m.group(3)))
    raise ColorError(f"읽을 수 없는 색: {color!r}")


def is_color(color: str) -> bool:
    try:
        parse(color)
    except ColorError:
        return False
    return True


def to_hex(rgb: RGB) -> str:
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def to_hsl(rgb: RGB) -> tuple[float, float, float]:
    r, g, b = (c / 255.0 for c in rgb)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return (h * 360.0, s, l)


def from_hsl(h: float, s: float, l: float) -> RGB:
    r, g, b = colorsys.hls_to_rgb((h % 360.0) / 360.0, _clamp(l), _clamp(s))
    return (round(r * 255), round(g * 255), round(b * 255))


def chroma(color: str | RGB) -> float:
    """색이 얼마나 물들었는지 (0 = 무채색, 1 = 원색).

    HSL 채도는 거의 흰색·거의 검정에서 1 에 가까워져 쓸 수 없다.
    크림색 바탕처럼 '거의 흰데 살짝 물든' 색을 가리려면 이 값을 본다.
    """
    r, g, b = parse(color) if isinstance(color, str) else color
    return (max(r, g, b) - min(r, g, b)) / 255.0


def luminance(rgb: RGB) -> float:
    """WCAG 상대 휘도."""

    def f(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str | RGB, b: str | RGB) -> float:
    """두 색의 대비비 (1.0 ~ 21.0)."""
    la = luminance(parse(a) if isinstance(a, str) else a)
    lb = luminance(parse(b) if isinstance(b, str) else b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def is_dark(color: str | RGB) -> bool:
    return luminance(parse(color) if isinstance(color, str) else color) < 0.18


def lighten(color: str, amount: float) -> str:
    h, s, l = to_hsl(parse(color))
    return to_hex(from_hsl(h, s, l + amount))


def darken(color: str, amount: float) -> str:
    return lighten(color, -amount)


def saturate(color: str, amount: float) -> str:
    h, s, l = to_hsl(parse(color))
    return to_hex(from_hsl(h, _clamp(s + amount), l))


def rotate(color: str, degrees: float) -> str:
    h, s, l = to_hsl(parse(color))
    return to_hex(from_hsl(h + degrees, s, l))


def mix(a: str, b: str, weight: float = 0.5) -> str:
    """a 를 weight 만큼, b 를 (1-weight) 만큼 섞는다."""
    w = _clamp(weight)
    ra, ga, ba = parse(a)
    rb, gb, bb = parse(b)
    return to_hex(
        (ra * w + rb * (1 - w), ga * w + gb * (1 - w), ba * w + bb * (1 - w))
    )


def readable_on(background: str, dark: str = "#14161a", light: str = "#ffffff") -> str:
    """배경 위에 올릴 글자색 중 대비가 큰 쪽."""
    return dark if contrast(background, dark) >= contrast(background, light) else light


def ensure_contrast(color: str, background: str, ratio: float = 4.5) -> str:
    """색조는 지키면서 밝기만 옮겨 대비 기준을 맞춘다.

    배경이 어두우면 색을 밝히고, 밝으면 어둡게 한다. 한계까지 가도
    기준에 못 미치면 흑/백 중 읽히는 쪽으로 물러선다.
    """
    if contrast(color, background) >= ratio:
        return to_hex(parse(color))
    h, s, l = to_hsl(parse(color))
    step = 0.02 if is_dark(background) else -0.02
    current = l
    for _ in range(50):
        current = _clamp(current + step)
        candidate = to_hex(from_hsl(h, s, current))
        if contrast(candidate, background) >= ratio:
            return candidate
        if current in (0.0, 1.0):
            break
    return readable_on(background)


def scale(color: str, steps: int = 5) -> list[str]:
    """밝은 쪽에서 어두운 쪽으로 늘어놓은 색 계단."""
    if steps < 2:
        raise ValueError("steps 는 2 이상")
    h, s, l = to_hsl(parse(color))
    top, bottom = min(0.94, l + 0.34), max(0.08, l - 0.34)
    out = []
    for i in range(steps):
        t = i / (steps - 1)
        out.append(to_hex(from_hsl(h, s, top + (bottom - top) * t)))
    return out


def button_safe(color: str, background: str, text_ratio: float = 4.5,
                background_ratio: float = 3.0) -> str:
    """버튼으로 쓸 수 있게 다듬은 색.

    버튼은 색 위에 글자를 얹는다. 흰 글자도 검은 글자도 4.5 를 못 넘기는
    중간 밝기 색(파랑 계열에 흔하다)은 밝기를 조금 옮겨 통과시킨다.
    바탕과의 대비도 같이 지켜, 배경에 묻히는 쪽으로는 옮기지 않는다.
    """
    base = to_hex(parse(color))
    if contrast(base, readable_on(base)) >= text_ratio:
        return base
    h, s, l = to_hsl(parse(base))
    for step in range(1, 61):
        for candidate_l in (l - step * 0.01, l + step * 0.01):
            if not 0.0 <= candidate_l <= 1.0:
                continue
            candidate = to_hex(from_hsl(h, s, candidate_l))
            if contrast(candidate, readable_on(candidate)) < text_ratio:
                continue
            if contrast(candidate, background) < background_ratio:
                continue
            return candidate
    return base


@dataclass(frozen=True)
class Palette:
    """실제로 CSS 변수로 나가는 한 벌."""

    primary: str
    primary_hover: str
    accent: str
    background: str
    surface: str
    border: str
    text: str
    text_muted: str
    on_primary: str
    mode: str  # "light" | "dark"

    def as_dict(self) -> dict[str, str]:
        return {
            "primary": self.primary,
            "primary-hover": self.primary_hover,
            "accent": self.accent,
            "background": self.background,
            "surface": self.surface,
            "border": self.border,
            "text": self.text,
            "text-muted": self.text_muted,
            "on-primary": self.on_primary,
        }

    def contrast_report(self) -> dict[str, float]:
        return {
            "text/background": round(contrast(self.text, self.background), 2),
            "muted/background": round(contrast(self.text_muted, self.background), 2),
            "primary/background": round(contrast(self.primary, self.background), 2),
            "on-primary/primary": round(contrast(self.on_primary, self.primary), 2),
        }


def build_palette(
    primary: str,
    mode: str = "light",
    accent: str | None = None,
    background: str | None = None,
    surface: str | None = None,
) -> Palette:
    """주색 하나에서 한 벌을 짠다. 글자 대비는 AA(4.5)를 맞춰 놓는다.

    background 를 주면 그 바탕색 위에 한 벌을 얹는다 — 레퍼런스의
    크림색·잉크색 바탕을 그대로 살리고 싶을 때 쓴다.
    """
    if mode not in ("light", "dark"):
        raise ValueError("mode 는 light 또는 dark")
    surface_given = surface   # 아래 분기에서 surface 를 다시 계산하므로 먼저 붙잡는다
    base = to_hex(parse(primary))
    h, s, _ = to_hsl(parse(base))
    acc = to_hex(parse(accent)) if accent else rotate(saturate(base, 0.08), 152)

    if background:
        given = to_hex(parse(background))
        background_color = given
        if is_dark(given):
            surface = lighten(given, 0.05)
            border = lighten(given, 0.16)
            text = to_hex(from_hsl(h, 0.08, 0.95))
            muted = to_hex(from_hsl(h, 0.10, 0.70))
        else:
            surface = mix(given, base, 0.96)
            border = darken(mix(given, base, 0.88), 0.04)
            text = to_hex(from_hsl(h, 0.14, 0.13))
            muted = to_hex(from_hsl(h, 0.10, 0.42))
        background = background_color
    elif mode == "dark":
        background = to_hex(from_hsl(h, min(s, 0.22), 0.09))
        surface = to_hex(from_hsl(h, min(s, 0.20), 0.14))
        border = to_hex(from_hsl(h, min(s, 0.18), 0.26))
        text = to_hex(from_hsl(h, 0.08, 0.95))
        muted = to_hex(from_hsl(h, 0.10, 0.70))
    else:
        background = "#ffffff"
        surface = to_hex(from_hsl(h, min(s, 0.30), 0.975))
        border = to_hex(from_hsl(h, min(s, 0.24), 0.90))
        text = to_hex(from_hsl(h, 0.14, 0.13))
        muted = to_hex(from_hsl(h, 0.10, 0.42))

    if surface_given:
        surface = to_hex(parse(surface_given))
        border = darken(surface, 0.07) if not is_dark(surface) else lighten(surface, 0.12)

    # 글자는 바탕에서도 면에서도 읽혀야 한다. 둘 중 더 빡빡한 쪽까지 민다.
    for backdrop in (background, surface):
        text = ensure_contrast(text, backdrop, 7.0)
        muted = ensure_contrast(muted, backdrop, 4.5)

    primary = button_safe(ensure_contrast(base, background, 3.2), background)
    return Palette(
        primary=primary,
        primary_hover=darken(primary, 0.08) if mode == "light" else lighten(primary, 0.10),
        accent=ensure_contrast(acc, background, 3.0),
        background=background,
        surface=surface,
        border=border,
        text=text,
        text_muted=muted,
        on_primary=readable_on(primary),
        mode=mode,
    )
