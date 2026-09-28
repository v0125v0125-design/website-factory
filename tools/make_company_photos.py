"""기업·B2B 마스터용 견본 그림을 그린다.

남의 사진을 쓰지 않습니다. 라이선스를 확인할 수 없는 스톡 사진도 내려받지
않습니다 — 그래서 직접 그립니다. 공장·설비·부품·도면처럼 산업 현장에서
실제로 보이는 형태만 씁니다. 기어 아이콘이나 금속 질감은 쓰지 않습니다.

    python tools/make_company_photos.py [내보낼폴더]

비율을 일부러 섞습니다 — 16:9 · 4:3 · 3:2 · 1:1 이 한 격자에 섞여도
레이아웃이 버티는지 눈으로 확인하기 위해서입니다.
"""

from __future__ import annotations

import sys
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "examples/photos/company")

# (바탕, 바닥/면, 설비, 잉크) — 공장 조명 아래의 회청색.
STEEL = [
    ("#E9ECEF", "#CFD6DD", "#9AA6B2", "#1B2836"),
    ("#EDEFF1", "#D5D9DD", "#A3ABB4", "#20262C"),
    ("#E7EBEE", "#C9D1D8", "#93A0AC", "#17222E"),
    ("#EFF1F3", "#D9DDE1", "#A8AFB6", "#1E242A"),
]
ACCENT = "#E2622A"


def _defs(i: int, bg: str, mid: str, ink: str) -> str:
    return f"""<defs>
  <linearGradient id="b{i}" x1="0" y1="0" x2=".2" y2="1">
    <stop offset="0" stop-color="{bg}"/><stop offset="1" stop-color="{mid}" stop-opacity=".55"/>
  </linearGradient>
  <linearGradient id="l{i}" x1="0" y1="0" x2=".9" y2="1">
    <stop offset="0" stop-color="#ffffff" stop-opacity=".46"/>
    <stop offset=".62" stop-color="#ffffff" stop-opacity=".04"/>
    <stop offset="1" stop-color="{ink}" stop-opacity=".2"/>
  </linearGradient>
</defs>"""


def scene(kind: str, w: int, h: int, palette, label: str, i: int) -> str:
    bg, floor, mid, ink = palette
    P = [_defs(i, bg, mid, ink)]
    P.append(f'<rect width="{w}" height="{h}" fill="url(#b{i})"/>')

    def rect(x, y, ww, hh, fill, op="1", stroke=None):
        s = f' stroke="{stroke}" stroke-opacity=".35" stroke-width="{max(2, w // 500)}"' if stroke else ""
        return (f'<rect x="{int(w*x)}" y="{int(h*y)}" width="{int(w*ww)}" '
                f'height="{int(h*hh)}" fill="{fill}" opacity="{op}"{s}/>')

    if kind == "line":                     # 컨베이어 라인
        P.append(rect(0, .70, 1, .30, floor))
        P.append(rect(.02, .60, .96, .07, mid, ".95", ink))
        for n in range(9):                 # 롤러
            cx = int(w * (.06 + n * .105))
            P.append(f'<circle cx="{cx}" cy="{int(h*.635)}" r="{max(4,int(h*.016))}" fill="{ink}" opacity=".32"/>')
        for n in range(4):                 # 이송물
            P.append(rect(.09 + n * .23, .50, .12, .10, bg, "1", ink))
        P.append(rect(.62, .16, .05, .46, mid, "1", ink))     # 로봇 기둥
        P.append(f'<path d="M{int(w*.645)},{int(h*.22)} L{int(w*.80)},{int(h*.30)} L{int(w*.78)},{int(h*.46)}" '
                 f'fill="none" stroke="{ink}" stroke-opacity=".55" stroke-width="{max(5,int(w*.012))}" stroke-linejoin="round"/>')
        P.append(f'<rect x="{int(w*.755)}" y="{int(h*.45)}" width="{int(w*.055)}" height="{int(h*.06)}" fill="{ACCENT}" opacity=".9"/>')
        P.append(rect(.02, .06, .26, .28, bg, ".55", ink))    # 제어반
        for n in range(3):
            P.append(f'<circle cx="{int(w*(.055+n*.045))}" cy="{int(h*.12)}" r="{max(3,int(h*.012))}" '
                     f'fill="{ACCENT if n == 0 else ink}" opacity="{.9 if n == 0 else .35}"/>')
        # 뒤쪽 설비와 선반 — 빈 벽으로 보이지 않게 잡아 준다
        P.append(rect(.33, .10, .22, .40, mid, ".45", ink))
        P.append(rect(.82, .08, .16, .44, mid, ".38", ink))
        for n in range(3):
            P.append(f'<line x1="{int(w*.82)}" y1="{int(h*(.18+n*.11))}" x2="{int(w*.98)}" '
                     f'y2="{int(h*(.18+n*.11))}" stroke="{ink}" stroke-opacity=".22" stroke-width="2"/>')
        P.append(rect(.06, .70, .18, .22, mid, ".55", ink))   # 앞쪽 파렛트
        P.append(rect(.28, .76, .12, .16, mid, ".45", ink))
    elif kind == "machine":                # CNC 장비 정면
        P.append(rect(0, .78, 1, .22, floor))
        P.append(rect(.10, .12, .80, .66, mid, ".95", ink))
        P.append(rect(.16, .20, .48, .38, bg, ".92", ink))    # 가공실 창
        P.append(rect(.24, .34, .18, .12, mid, "1", ink))     # 척
        P.append(f'<rect x="{int(w*.33)}" y="{int(h*.22)}" width="{max(4,int(w*.01))}" height="{int(h*.12)}" fill="{ACCENT}"/>')
        P.append(rect(.68, .20, .16, .16, bg, ".85", ink))    # 조작 패널
        for n in range(4):
            P.append(f'<line x1="{int(w*.70)}" y1="{int(h*(.23+n*.03))}" x2="{int(w*.82)}" '
                     f'y2="{int(h*(.23+n*.03))}" stroke="{ink}" stroke-opacity=".28" stroke-width="2"/>')
        P.append(rect(.68, .40, .16, .18, mid, ".8", ink))
    elif kind == "parts":                  # 정밀 부품
        P.append(rect(0, .62, 1, .38, floor, ".85"))
        spots = [(.20, .42, .085), (.44, .36, .115), (.70, .44, .075), (.84, .60, .055), (.33, .66, .06)]
        for n, (cx, cy, r) in enumerate(spots):
            R = int(min(w, h) * r)
            P.append(f'<ellipse cx="{int(w*cx)}" cy="{int(h*cy)+R}" rx="{int(R*1.05)}" ry="{max(4,int(R*.2))}" fill="{ink}" opacity=".16"/>')
            P.append(f'<circle cx="{int(w*cx)}" cy="{int(h*cy)}" r="{R}" fill="{mid}"/>')
            P.append(f'<circle cx="{int(w*cx)}" cy="{int(h*cy)}" r="{int(R*.42)}" fill="{bg}"/>')
            for k in range(6):             # 볼트 구멍
                import math
                a = k * math.pi / 3
                P.append(f'<circle cx="{int(w*cx + R*.72*math.cos(a))}" cy="{int(h*cy + R*.72*math.sin(a))}" '
                         f'r="{max(2,int(R*.09))}" fill="{ink}" opacity=".4"/>')
            if n == 1:
                P.append(f'<circle cx="{int(w*cx)}" cy="{int(h*cy)}" r="{int(R*.42)}" fill="none" '
                         f'stroke="{ACCENT}" stroke-width="{max(3,int(R*.07))}"/>')
    elif kind == "inspect":                # 비전 검사
        P.append(rect(0, .74, 1, .26, floor))
        P.append(rect(.06, .56, .88, .06, mid, "1", ink))
        P.append(rect(.30, .46, .16, .10, bg, "1", ink))      # 검사 대상
        P.append(rect(.34, .08, .08, .26, mid, "1", ink))     # 카메라 기둥
        P.append(rect(.30, .30, .16, .09, ink, ".62"))        # 카메라 헤드
        P.append(f'<polygon points="{int(w*.32)},{int(h*.39)} {int(w*.44)},{int(h*.39)} '
                 f'{int(w*.48)},{int(h*.46)} {int(w*.28)},{int(h*.46)}" fill="{ACCENT}" opacity=".26"/>')
        P.append(rect(.58, .12, .34, .34, bg, ".95", ink))    # 모니터
        for n in range(5):
            P.append(f'<line x1="{int(w*.61)}" y1="{int(h*(.17+n*.055))}" x2="{int(w*(.66+ (n%3)*.08))}" '
                     f'y2="{int(h*(.17+n*.055))}" stroke="{ink}" stroke-opacity=".3" stroke-width="3"/>')
        P.append(f'<rect x="{int(w*.61)}" y="{int(h*.38)}" width="{int(w*.10)}" height="{max(4,int(h*.016))}" fill="{ACCENT}"/>')
    elif kind == "cad":                    # 도면
        P.append(f'<rect width="{w}" height="{h}" fill="{bg}"/>')
        step = max(28, int(w * .045))
        for x in range(0, w, step):
            P.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{ink}" stroke-opacity=".09" stroke-width="1"/>')
        for y in range(0, h, step):
            P.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{ink}" stroke-opacity=".09" stroke-width="1"/>')
        P.append(rect(.14, .18, .44, .48, "none", "1", ink))
        P.append(rect(.22, .28, .28, .28, "none", "1", ink))
        P.append(f'<circle cx="{int(w*.36)}" cy="{int(h*.42)}" r="{int(min(w,h)*.10)}" fill="none" '
                 f'stroke="{ink}" stroke-opacity=".38" stroke-width="{max(2,w//500)}"/>')
        P.append(f'<line x1="{int(w*.14)}" y1="{int(h*.74)}" x2="{int(w*.58)}" y2="{int(h*.74)}" '
                 f'stroke="{ACCENT}" stroke-width="{max(2,w//560)}"/>')
        P.append(f'<line x1="{int(w*.14)}" y1="{int(h*.71)}" x2="{int(w*.14)}" y2="{int(h*.77)}" stroke="{ACCENT}" stroke-width="{max(2,w//560)}"/>')
        P.append(f'<line x1="{int(w*.58)}" y1="{int(h*.71)}" x2="{int(w*.58)}" y2="{int(h*.77)}" stroke="{ACCENT}" stroke-width="{max(2,w//560)}"/>')
        P.append(rect(.66, .60, .28, .22, "none", "1", ink))
    else:                                  # plant — 공장 내부
        P.append(rect(0, .72, 1, .28, floor))
        for n in range(4):                 # 기둥
            P.append(rect(.06 + n * .28, .10, .035, .62, mid, ".9"))
        P.append(f'<polygon points="0,{int(h*.10)} {w},{int(h*.02)} {w},{int(h*.08)} 0,{int(h*.16)}" fill="{ink}" opacity=".18"/>')
        for n in range(3):                 # 천장 조명
            P.append(f'<rect x="{int(w*(.14+n*.30))}" y="{int(h*.06)}" width="{int(w*.14)}" '
                     f'height="{max(4,int(h*.014))}" fill="#fff" opacity=".8"/>')
        P.append(rect(.12, .44, .24, .28, mid, "1", ink))
        P.append(rect(.46, .38, .30, .34, mid, ".85", ink))
        P.append(f'<rect x="{int(w*.50)}" y="{int(h*.42)}" width="{int(w*.08)}" height="{int(h*.05)}" fill="{ACCENT}" opacity=".85"/>')
        P.append(f'<line x1="0" y1="{int(h*.72)}" x2="{w}" y2="{int(h*.72)}" stroke="{ink}" stroke-opacity=".3" stroke-width="2"/>')

    P.append(f'<rect width="{w}" height="{h}" fill="url(#l{i})"/>')
    if label:
        P.append(
            f'<text x="{w//2}" y="{h - max(14, int(h*.04))}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="{max(12, int(min(w,h)*.036))}" '
            f'fill="{ink}" opacity=".40">{label}</text>'
        )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{label or "예시 이미지"}">{"".join(P)}</svg>\n')


PLAN = [
    ("hero.svg",     1600, 1200, "line",    "예시 이미지 · 대표 사진 자리"),
    ("about.svg",    1600, 1000, "plant",   "예시 이미지 · 회사 사진 자리"),
    ("area-1.svg",   1600,  900, "line",    "예시 이미지 · 사업 영역"),
    ("area-2.svg",   1600,  900, "machine", "예시 이미지 · 사업 영역"),
    ("area-3.svg",   1600,  900, "inspect", "예시 이미지 · 사업 영역"),
    ("area-4.svg",   1600,  900, "cad",     "예시 이미지 · 사업 영역"),
    ("product-1.svg", 1200,  900, "machine", "예시 이미지 · 제품"),
    ("product-2.svg", 1200,  900, "parts",   "예시 이미지 · 제품"),
    ("product-3.svg", 1200, 1200, "inspect", "예시 이미지 · 제품"),
    ("product-4.svg",  900, 1200, "cad",     "예시 이미지 · 제품"),
    ("product-5.svg", 1500, 1000, "line",    "예시 이미지 · 제품"),
    ("product-6.svg", 1200,  900, "plant",   "예시 이미지 · 제품"),
    ("case-1.svg",    800,  600, "line",    ""),
    ("case-2.svg",    800,  600, "machine", ""),
    ("case-3.svg",    800,  600, "inspect", ""),
    ("case-4.svg",    800,  600, "parts",   ""),
    ("case-5.svg",    800,  600, "plant",   ""),
    ("case-6.svg",    800,  600, "cad",     ""),
    ("case-7.svg",    800,  600, "machine", ""),
    ("case-8.svg",    800,  600, "line",    ""),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for index, (name, w, h, kind, label) in enumerate(PLAN):
        svg = scene(kind, w, h, STEEL[index % len(STEEL)], label, i=index)
        (OUT / name).write_text(svg, encoding="utf-8")
    print(f"{len(PLAN)}장을 {OUT} 에 그렸습니다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
