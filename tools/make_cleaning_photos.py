"""청소 마스터용 견본 그림을 그린다.

남의 사진을 쓰지 않습니다. 라이선스를 확인할 수 없는 스톡 사진도
내려받지 않습니다 — 그래서 직접 그립니다. 같은 장면을 두 번 그려서
`작업 전`(때·얼룩·흐린 빛)과 `작업 후`(맑은 빛·깨끗한 면)를 만듭니다.

    python tools/make_cleaning_photos.py [내보낼폴더]

비율을 일부러 섞습니다 — 16:9 · 4:3 · 3:2 · 3:4 가 한 격자에 섞여도
레이아웃이 버티는지 눈으로 확인하기 위해서입니다.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "examples/photos/cleaning")

# (벽, 바닥, 설비, 잉크) — 밝고 차가운 쪽. 청소 끝난 집의 색이다.
CLEAN = [
    ("#F2F4F6", "#DCE2E6", "#B9C4CC", "#22303A"),
    ("#F4F5F3", "#E0E3DE", "#BEC6BF", "#26302C"),
    ("#F1F4F7", "#D8DFE6", "#B2BFCB", "#1F2A35"),
    ("#F5F4F1", "#E2E0DA", "#C3C0B6", "#2B2A26"),
]


def _dim(hex_color: str, amount: float) -> str:
    """색을 누렇고 어둡게. 때가 낀 면은 채도가 아니라 밝기가 먼저 떨어진다."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    r = int(r * (1 - amount * 0.86) + 18 * amount)
    g = int(g * (1 - amount * 0.90) + 14 * amount)
    b = int(b * (1 - amount)        + 6 * amount)
    return "#%02X%02X%02X" % (max(0, r), max(0, g), max(0, b))


def _defs(idx: int, wall: str, floor: str, mid: str, ink: str, dirty: bool) -> str:
    glow = ".14" if dirty else ".58"
    return f"""<defs>
  <linearGradient id="w{idx}" x1="0" y1="0" x2=".3" y2="1">
    <stop offset="0" stop-color="{wall}"/><stop offset="1" stop-color="{mid}" stop-opacity=".4"/>
  </linearGradient>
  <linearGradient id="f{idx}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{floor}"/><stop offset="1" stop-color="{ink}" stop-opacity=".42"/>
  </linearGradient>
  <linearGradient id="l{idx}" x1="0" y1="0" x2="1" y2=".9">
    <stop offset="0" stop-color="#ffffff" stop-opacity="{glow}"/>
    <stop offset=".6" stop-color="#ffffff" stop-opacity=".04"/>
    <stop offset="1" stop-color="{ink}" stop-opacity="{'.34' if dirty else '.16'}"/>
  </linearGradient>
  <linearGradient id="g{idx}" x1="0" y1="0" x2=".5" y2="1">
    <stop offset="0" stop-color="#ffffff" stop-opacity="{'.42' if dirty else '.95'}"/>
    <stop offset="1" stop-color="{wall}" stop-opacity=".6"/>
  </linearGradient>
</defs>"""


def _grime(w: int, h: int, ink: str, seed: int, strength: int) -> list[str]:
    """때·얼룩·먼지. 규칙적으로 뿌리면 무늬가 되므로 자리를 흩는다."""
    rnd = random.Random(seed)
    out = []
    for _ in range(strength):
        cx, cy = rnd.uniform(.05, .95), rnd.uniform(.30, .96)
        rx = rnd.uniform(.03, .11)
        out.append(
            f'<ellipse cx="{int(w*cx)}" cy="{int(h*cy)}" rx="{int(w*rx)}" '
            f'ry="{int(h*rx*rnd.uniform(.35,.7))}" fill="{ink}" opacity="{rnd.uniform(.06,.17):.2f}"/>'
        )
    for _ in range(strength // 2):
        x = rnd.uniform(.05, .95)
        y0 = rnd.uniform(.10, .45)
        out.append(
            f'<rect x="{int(w*x)}" y="{int(h*y0)}" width="{max(2,int(w*.004))}" '
            f'height="{int(h*rnd.uniform(.08,.30))}" fill="{ink}" opacity="{rnd.uniform(.07,.15):.2f}"/>'
        )
    return out


def scene(kind: str, w: int, h: int, palette, label: str, idx: int, dirty: bool) -> str:
    wall, floor, mid, ink = palette
    if dirty:
        wall, floor, mid = _dim(wall, .22), _dim(floor, .30), _dim(mid, .26)
    floor_y = int(h * 0.68)
    P = [_defs(idx, wall, floor, mid, ink, dirty)]
    P.append(f'<rect width="{w}" height="{h}" fill="url(#w{idx})"/>')
    P.append(f'<rect y="{floor_y}" width="{w}" height="{h - floor_y}" fill="url(#f{idx})"/>')

    if kind == "empty":          # 입주 전 빈 거실 — 창·문틀·걸레받이
        wx, wy = int(w * .06), int(h * .10)
        ww, wh_ = int(w * .46), int(h * .50)
        P.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh_}" rx="2" fill="url(#g{idx})"/>')
        P.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh_}" rx="2" fill="none" stroke="{ink}" stroke-opacity=".3" stroke-width="{max(2,w//440)}"/>')
        P.append(f'<line x1="{wx+ww//2}" y1="{wy}" x2="{wx+ww//2}" y2="{wy+wh_}" stroke="{ink}" stroke-opacity=".24" stroke-width="{max(2,w//560)}"/>')
        if not dirty:
            P.append(f'<polygon points="{wx},{floor_y} {wx+ww},{floor_y} {int(wx+ww*2.0)},{h} {int(wx-w*.02)},{h}" fill="#fff" opacity=".17"/>')
        # 오른쪽 문틀과 걸레받이 — 빈 방이 빈 카드로 보이지 않게 잡아 준다
        dx, dw = int(w * .64), int(w * .26)
        P.append(f'<rect x="{dx}" y="{int(h*.06)}" width="{dw}" height="{floor_y - int(h*.06)}" fill="{mid}" opacity=".30"/>')
        P.append(f'<rect x="{dx}" y="{int(h*.06)}" width="{dw}" height="{floor_y - int(h*.06)}" fill="none" stroke="{ink}" stroke-opacity=".28" stroke-width="{max(2,w//440)}"/>')
        P.append(f'<circle cx="{dx + int(dw*.88)}" cy="{int(h*.42)}" r="{max(4,int(min(w,h)*.012))}" fill="{ink}" opacity=".45"/>')
        P.append(f'<rect x="0" y="{floor_y - max(6,int(h*.022))}" width="{w}" height="{max(6,int(h*.022))}" fill="{wall}" opacity=".85"/>')
        P.append(f'<rect x="0" y="{floor_y}" width="{w}" height="2" fill="{ink}" opacity=".30"/>')
        for i in range(5):
            y = floor_y + int((h - floor_y) * (i + 1) / 6)
            P.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{ink}" stroke-opacity=".08" stroke-width="2"/>')
    elif kind == "kitchen":
        P.append(f'<rect x="{int(w*.04)}" y="{int(h*.10)}" width="{int(w*.42)}" height="{int(h*.22)}" rx="3" fill="{mid}" opacity=".85"/>')
        P.append(f'<rect x="{int(w*.50)}" y="{int(h*.10)}" width="{int(w*.46)}" height="{int(h*.22)}" rx="3" fill="{mid}" opacity=".5"/>')
        P.append(f'<rect x="{int(w*.04)}" y="{int(h*.44)}" width="{int(w*.92)}" height="{int(h*.045)}" rx="2" fill="{ink}" opacity=".5"/>')
        P.append(f'<rect x="{int(w*.04)}" y="{int(h*.485)}" width="{int(w*.92)}" height="{int(h*.20)}" fill="{wall}" opacity=".9"/>')
        P.append(f'<rect x="{int(w*.56)}" y="{int(h*.34)}" width="{int(w*.18)}" height="{int(h*.09)}" rx="2" fill="{ink}" opacity=".28"/>')
        for i in range(4):
            x = int(w * (.10 + i * .22))
            P.append(f'<line x1="{x}" y1="{int(h*.485)}" x2="{x}" y2="{int(h*.685)}" stroke="{ink}" stroke-opacity=".16" stroke-width="2"/>')
    elif kind == "bath":
        P.append(f'<rect x="{int(w*.06)}" y="{int(h*.12)}" width="{int(w*.40)}" height="{int(h*.52)}" rx="4" fill="url(#g{idx})" opacity=".9"/>')
        P.append(f'<rect x="{int(w*.06)}" y="{int(h*.12)}" width="{int(w*.40)}" height="{int(h*.52)}" rx="4" fill="none" stroke="{ink}" stroke-opacity=".26" stroke-width="2"/>')
        P.append(f'<rect x="{int(w*.54)}" y="{int(h*.38)}" width="{int(w*.38)}" height="{int(h*.26)}" rx="{int(h*.04)}" fill="{mid}"/>')
        P.append(f'<rect x="{int(w*.60)}" y="{int(h*.16)}" width="{int(w*.26)}" height="{int(h*.14)}" rx="3" fill="{wall}" opacity=".92"/>')
        # 타일 줄눈 — 때가 끼면 여기가 먼저 보인다
        for i in range(7):
            x = int(w * (i + 1) / 8)
            P.append(f'<line x1="{x}" y1="{floor_y}" x2="{x}" y2="{h}" stroke="{ink}" stroke-opacity="{.30 if dirty else .12}" stroke-width="2"/>')
        for i in range(3):
            y = floor_y + int((h - floor_y) * (i + 1) / 4)
            P.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{ink}" stroke-opacity="{.30 if dirty else .12}" stroke-width="2"/>')
    elif kind == "shop":         # 상가 — 유리 파사드와 넓은 바닥
        P.append(f'<rect x="{int(w*.04)}" y="{int(h*.08)}" width="{int(w*.92)}" height="{int(h*.52)}" fill="url(#g{idx})" opacity=".85"/>')
        for i in range(3):
            x = int(w * (.04 + (i + 1) * .23))
            P.append(f'<line x1="{x}" y1="{int(h*.08)}" x2="{x}" y2="{int(h*.60)}" stroke="{ink}" stroke-opacity=".3" stroke-width="{max(3,w//380)}"/>')
        P.append(f'<rect x="{int(w*.04)}" y="{int(h*.60)}" width="{int(w*.92)}" height="{max(4,int(h*.012))}" fill="{ink}" opacity=".45"/>')
        if not dirty:
            P.append(f'<polygon points="{int(w*.10)},{floor_y} {int(w*.55)},{floor_y} {int(w*.80)},{h} {int(w*.02)},{h}" fill="#fff" opacity=".15"/>')
    else:                        # detail — 설비 한 점
        cx, cy = int(w * .5), int(h * .44)
        r = int(min(w, h) * .19)
        P.append(f'<rect x="{int(w*.14)}" y="{int(h*.16)}" width="{int(w*.18)}" height="{int(h*.22)}" rx="3" fill="{wall}" opacity=".8"/>')
        P.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{mid}"/>')
        P.append(f'<circle cx="{int(cx-r*.34)}" cy="{int(cy-r*.34)}" r="{int(r*.5)}" fill="#fff" opacity="{.06 if dirty else .22}"/>')
        P.append(f'<rect x="{int(w*.10)}" y="{int(h*.72)}" width="{int(w*.80)}" height="{max(5,int(h*.016))}" rx="2" fill="{ink}" opacity=".35"/>')

    if dirty:
        P += _grime(w, h, ink, seed=idx * 17 + 3, strength=18)
    P.append(f'<rect width="{w}" height="{h}" fill="url(#l{idx})"/>')
    if not label:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
                f'role="img" aria-label="예시 이미지">{"".join(P)}</svg>\n')
    P.append(
        f'<text x="{w//2}" y="{h - max(14, int(h*.04))}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="{max(12, int(min(w,h)*.036))}" '
        f'fill="{ink}" opacity=".42">{label}</text>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="{label}">{"".join(P)}</svg>\n'
    )


# (파일이름, 가로, 세로, 장면, 라벨, 때) — 비율을 일부러 섞는다.
PLAN = [
    ("hero.svg",      1600, 1200, "empty",   "예시 이미지 · 대표 사진 자리", False),
    ("about.svg",      900, 1200, "detail",  "예시 이미지 · 업체 사진 자리", False),
    ("service-1.svg", 1200,  900, "empty",   "예시 이미지 · 입주청소", False),
    ("service-2.svg", 1200,  900, "kitchen", "예시 이미지 · 이사청소", False),
    ("service-3.svg", 1200,  900, "bath",    "예시 이미지 · 거주청소", False),
    ("service-4.svg", 1200,  900, "shop",    "예시 이미지 · 상가청소", False),
    ("ba-1-before.svg", 1600, 1200, "kitchen", "", True),
    ("ba-1-after.svg",  1600, 1200, "kitchen", "", False),
    ("ba-2-before.svg", 1600, 1200, "bath", "", True),
    ("ba-2-after.svg",  1600, 1200, "bath", "", False),
    ("ba-3-before.svg", 1600, 1200, "empty", "", True),
    ("ba-3-after.svg",  1600, 1200, "empty", "", False),
    ("ba-4-before.svg", 1600, 1200, "shop", "", True),
    ("ba-4-after.svg",  1600, 1200, "shop", "", False),
    ("case-1.svg", 1500, 1000, "empty",   "예시 이미지 · 작업 사례", False),
    ("case-2.svg", 1200,  900, "kitchen", "예시 이미지 · 작업 사례", False),
    ("case-3.svg",  900, 1200, "bath",    "예시 이미지 · 작업 사례", False),
    ("case-4.svg", 1600,  900, "shop",    "예시 이미지 · 작업 사례", False),
    ("case-5.svg", 1200, 1200, "detail",  "예시 이미지 · 작업 사례", False),
    ("case-6.svg", 1500, 1000, "kitchen", "예시 이미지 · 작업 사례", False),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for index, (name, w, h, kind, label, dirty) in enumerate(PLAN):
        # 전·후 한 짝은 같은 방이어야 한다. 팔레트 자리를 짝끼리 맞춘다.
        slot = (index // 2) if name.startswith("ba-") else index
        svg = scene(kind, w, h, CLEAN[slot % len(CLEAN)], label, idx=index, dirty=dirty)
        (OUT / name).write_text(svg, encoding="utf-8")
    print(f"{len(PLAN)}장을 {OUT} 에 그렸습니다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
