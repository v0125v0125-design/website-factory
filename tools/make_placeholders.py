"""개발용 임시 이미지를 그린다.

고객 사진이 아직 없을 때 자리를 채우는 SVG 를 만든다. 남의 사진을
쓰지 않으려고 직접 그린다. 비율을 일부러 섞어 두었다 —
16:9 · 4:3 · 1:1 · 3:4 가 한 격자에 섞여도 레이아웃이 버티는지
눈으로 확인하기 위해서다.

    python tools/make_placeholders.py [내보낼폴더] [색자리이동]
"""

from __future__ import annotations

import sys
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "examples/photos/interior")
# 두 번째 인자는 색 자리를 몇 칸 밀지. 고객마다 방 색을 달리해 보려고 둔다.
SHIFT = int(sys.argv[2]) if len(sys.argv) > 2 else 0

# 따뜻한 무채색 계열. 마스터 템플릿의 기본 테마와 같은 방을 본다.
# (벽, 바닥, 가구, 잉크)
PALETTES = [
    ("#EDE7DE", "#D6C9B8", "#8C7A66", "#3A342D"),
    ("#E6E4E1", "#C9C4BC", "#7E7A73", "#332F2B"),
    ("#EFE9E1", "#D9C8B4", "#96806A", "#3B332B"),
    ("#E8EAE7", "#C8CFC8", "#7C8A7C", "#2E362E"),
    ("#F0EAE3", "#DCCBB9", "#96806A", "#372F28"),
    ("#E9E6E2", "#CFC6BA", "#8A8076", "#312C27"),
]

def _defs(idx: int, wall: str, floor: str, mid: str, ink: str) -> str:
    """빛과 그림자. 납작한 도형과 사진의 차이는 대개 이것뿐이다."""
    return f"""<defs>
  <linearGradient id="wall{idx}" x1="0" y1="0" x2="0.35" y2="1">
    <stop offset="0" stop-color="{wall}"/><stop offset="1" stop-color="{mid}" stop-opacity=".45"/>
  </linearGradient>
  <linearGradient id="floor{idx}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{floor}"/><stop offset="1" stop-color="{ink}" stop-opacity=".55"/>
  </linearGradient>
  <linearGradient id="light{idx}" x1="0" y1="0" x2="1" y2="0.8">
    <stop offset="0" stop-color="#ffffff" stop-opacity=".55"/><stop offset=".55" stop-color="#ffffff" stop-opacity=".06"/>
    <stop offset="1" stop-color="{ink}" stop-opacity=".22"/>
  </linearGradient>
  <linearGradient id="glass{idx}" x1="0" y1="0" x2="0.6" y2="1">
    <stop offset="0" stop-color="#ffffff" stop-opacity=".92"/><stop offset="1" stop-color="{wall}" stop-opacity=".6"/>
  </linearGradient>
  <radialGradient id="lamp{idx}" cx=".5" cy=".5" r=".5">
    <stop offset="0" stop-color="#ffe9c4" stop-opacity=".95"/><stop offset="1" stop-color="#ffe9c4" stop-opacity="0"/>
  </radialGradient>
</defs>"""


def scene(kind: str, w: int, h: int, palette: tuple[str, str, str, str], label: str, idx: int = 0) -> str:
    wall, floor, mid, ink = palette
    floor_y = int(h * 0.70)
    P = []  # 겹겹이 쌓는다: 벽 → 빛 → 가구 → 바닥 그림자 → 라벨
    P.append(_defs(idx, wall, floor, mid, ink))
    P.append(f'<rect width="{w}" height="{h}" fill="url(#wall{idx})"/>')
    P.append(f'<rect y="{floor_y}" width="{w}" height="{h - floor_y}" fill="url(#floor{idx})"/>')

    def shadow(x, y, width, height, opacity=".18"):
        return (f'<ellipse cx="{x + width // 2}" cy="{y + height}" rx="{int(width * .62)}" '
                f'ry="{max(6, int(height * .07))}" fill="{ink}" opacity="{opacity}"/>')

    if kind == "room":
        win_x, win_y = int(w * .05), int(h * .10)
        win_w, win_h = int(w * .32), int(h * .50)
        P.append(f'<rect x="{win_x}" y="{win_y}" width="{win_w}" height="{win_h}" rx="3" fill="url(#glass{idx})"/>')
        P.append(f'<rect x="{win_x}" y="{win_y}" width="{win_w}" height="{win_h}" rx="3" fill="none" stroke="{ink}" stroke-opacity=".35" stroke-width="{max(2, w // 420)}"/>')
        P.append(f'<line x1="{win_x + win_w // 2}" y1="{win_y}" x2="{win_x + win_w // 2}" y2="{win_y + win_h}" stroke="{ink}" stroke-opacity=".28" stroke-width="{max(2, w // 520)}"/>')
        # 창에서 들어온 빛이 바닥에 떨어진다
        P.append(f'<polygon points="{win_x},{floor_y} {win_x + win_w},{floor_y} {int(win_x + win_w * 2.1)},{h} {int(win_x - w * .02)},{h}" fill="#fff" opacity=".13"/>')
        sofa_x, sofa_y = int(w * .42), int(h * .47)
        sofa_w, sofa_h = int(w * .48), int(h * .20)
        P.append(shadow(sofa_x, sofa_y, sofa_w, sofa_h, ".22"))
        P.append(f'<rect x="{sofa_x}" y="{sofa_y}" width="{sofa_w}" height="{sofa_h}" rx="{int(h * .022)}" fill="{mid}"/>')
        P.append(f'<rect x="{sofa_x + int(sofa_w * .06)}" y="{sofa_y - int(h * .07)}" width="{int(sofa_w * .40)}" height="{int(h * .09)}" rx="{int(h * .018)}" fill="{mid}" opacity=".78"/>')
        P.append(f'<rect x="{sofa_x + int(sofa_w * .52)}" y="{sofa_y - int(h * .06)}" width="{int(sofa_w * .34)}" height="{int(h * .08)}" rx="{int(h * .016)}" fill="{wall}" opacity=".7"/>')
        table_x, table_y = int(w * .45), int(h * .74)
        P.append(f'<ellipse cx="{table_x}" cy="{table_y}" rx="{int(w * .11)}" ry="{int(h * .035)}" fill="{ink}" opacity=".30"/>')
        lamp_x, lamp_y, lamp_r = int(w * .80), int(h * .21), int(min(w, h) * .075)
        P.append(f'<line x1="{lamp_x}" y1="0" x2="{lamp_x}" y2="{lamp_y}" stroke="{ink}" stroke-opacity=".45" stroke-width="{max(2, w // 600)}"/>')
        P.append(f'<circle cx="{lamp_x}" cy="{lamp_y}" r="{int(lamp_r * 2.4)}" fill="url(#lamp{idx})"/>')
        P.append(f'<circle cx="{lamp_x}" cy="{lamp_y}" r="{lamp_r}" fill="{ink}" opacity=".55"/>')
    elif kind == "kitchen":
        P.append(f'<rect x="{int(w*.04)}" y="{int(h*.12)}" width="{int(w*.40)}" height="{int(h*.22)}" rx="4" fill="{mid}" opacity=".85"/>')
        P.append(f'<rect x="{int(w*.48)}" y="{int(h*.12)}" width="{int(w*.48)}" height="{int(h*.22)}" rx="4" fill="{mid}" opacity=".55"/>')
        P.append(f'<line x1="{int(w*.24)}" y1="{int(h*.12)}" x2="{int(w*.24)}" y2="{int(h*.34)}" stroke="{ink}" stroke-opacity=".22" stroke-width="2"/>')
        P.append(f'<rect x="{int(w*.04)}" y="{int(h*.44)}" width="{int(w*.92)}" height="{int(h*.05)}" rx="2" fill="{ink}" opacity=".62"/>')
        P.append(f'<rect x="{int(w*.04)}" y="{int(h*.49)}" width="{int(w*.92)}" height="{int(h*.21)}" fill="{wall}" opacity=".92"/>')
        for i in range(4):
            x = int(w * (.10 + i * .22))
            P.append(f'<line x1="{x}" y1="{int(h*.49)}" x2="{x}" y2="{int(h*.70)}" stroke="{ink}" stroke-opacity=".18" stroke-width="2"/>')
            P.append(f'<circle cx="{x + int(w*.02)}" cy="{int(h*.58)}" r="{max(3, int(min(w,h)*.008))}" fill="{ink}" opacity=".45"/>')
        P.append(f'<rect x="{int(w*.62)}" y="{int(h*.36)}" width="{int(w*.16)}" height="{int(h*.08)}" rx="3" fill="{ink}" opacity=".30"/>')
        P.append(f'<polygon points="0,{int(h*.05)} {int(w*.5)},{int(h*.02)} {int(w*.35)},{int(h*.7)} 0,{int(h*.75)}" fill="#fff" opacity=".10"/>')
    elif kind == "bath":
        P.append(f'<rect x="{int(w*.06)}" y="{int(h*.14)}" width="{int(w*.40)}" height="{int(h*.52)}" rx="6" fill="url(#glass{idx})" opacity=".85"/>')
        P.append(f'<rect x="{int(w*.06)}" y="{int(h*.14)}" width="{int(w*.40)}" height="{int(h*.52)}" rx="6" fill="none" stroke="{ink}" stroke-opacity=".28" stroke-width="2"/>')
        P.append(shadow(int(w*.52), int(h*.40), int(w*.40), int(h*.26), ".20"))
        P.append(f'<rect x="{int(w*.52)}" y="{int(h*.40)}" width="{int(w*.40)}" height="{int(h*.26)}" rx="{int(h*.05)}" fill="{mid}"/>')
        P.append(f'<rect x="{int(w*.58)}" y="{int(h*.18)}" width="{int(w*.26)}" height="{int(h*.14)}" rx="4" fill="{wall}" opacity=".9"/>')
        P.append(f'<rect x="{int(w*.58)}" y="{int(h*.18)}" width="{int(w*.26)}" height="{int(h*.14)}" rx="4" fill="none" stroke="{ink}" stroke-opacity=".25" stroke-width="2"/>')
        for i in range(6):
            y = int(h * (.72 + i * .045))
            P.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{ink}" stroke-opacity=".10" stroke-width="2"/>')
    else:  # detail — 가구 한 점과 소품
        cx, cy = int(w * .50), int(h * .46)
        r = int(min(w, h) * .21)
        P.append(f'<polygon points="0,0 {int(w*.55)},0 {int(w*.30)},{h} 0,{h}" fill="#fff" opacity=".10"/>')
        P.append(shadow(cx - r, cy - r, r * 2, r * 2, ".20"))
        P.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{mid}"/>')
        P.append(f'<circle cx="{int(cx - r*.35)}" cy="{int(cy - r*.35)}" r="{int(r*.55)}" fill="#fff" opacity=".18"/>')
        P.append(f'<rect x="{int(w*.10)}" y="{int(h*.74)}" width="{int(w*.80)}" height="{max(6,int(h*.018))}" rx="3" fill="{ink}" opacity=".40"/>')
        P.append(f'<rect x="{int(w*.16)}" y="{int(h*.18)}" width="{int(w*.16)}" height="{int(h*.20)}" rx="3" fill="{wall}" opacity=".75"/>')
        P.append(f'<rect x="{int(w*.16)}" y="{int(h*.18)}" width="{int(w*.16)}" height="{int(h*.20)}" rx="3" fill="none" stroke="{ink}" stroke-opacity=".30" stroke-width="2"/>')

    # 사진처럼 보이게 하는 마지막 한 겹: 비네팅과 빛
    P.append(f'<rect width="{w}" height="{h}" fill="url(#light{idx})"/>')
    P.append(
        f'<text x="{w//2}" y="{h - max(16, int(h*.045))}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="{max(12, int(min(w, h) * .038))}" '
        f'fill="{ink}" opacity=".45">{label}</text>'
    )
    body = "".join(P)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="{label}">{body}</svg>\n'
    )


# (파일이름, 가로, 세로, 장면, 라벨) — 비율을 일부러 섞는다.
PLAN = [
    ("hero.svg", 1920, 1080, "room", "예시 이미지 · 대표 사진 자리"),
    ("about.svg", 900, 1200, "detail", "예시 이미지 · 업체 사진 자리"),
    ("service-1.svg", 1200, 900, "room", "예시 이미지 · 서비스"),
    ("service-2.svg", 1200, 900, "kitchen", "예시 이미지 · 서비스"),
    ("service-3.svg", 1200, 900, "bath", "예시 이미지 · 서비스"),
    ("service-4.svg", 1200, 900, "detail", "예시 이미지 · 서비스"),
    ("project-1a.svg", 1600, 900, "room", "예시 이미지 · 시공 사례"),
    ("project-1b.svg", 1200, 1200, "kitchen", "예시 이미지 · 시공 사례"),
    ("project-2a.svg", 1200, 900, "kitchen", "예시 이미지 · 시공 사례"),
    ("project-2b.svg", 900, 1200, "detail", "예시 이미지 · 시공 사례"),
    ("project-3a.svg", 1200, 900, "bath", "예시 이미지 · 시공 사례"),
    ("project-3b.svg", 1600, 900, "room", "예시 이미지 · 시공 사례"),
    ("project-4a.svg", 1200, 1200, "detail", "예시 이미지 · 시공 사례"),
    ("project-4b.svg", 1200, 900, "room", "예시 이미지 · 시공 사례"),
    ("project-5a.svg", 1200, 900, "room", "예시 이미지 · 시공 사례"),
    ("project-5b.svg", 900, 1200, "bath", "예시 이미지 · 시공 사례"),
    ("project-6a.svg", 1600, 900, "kitchen", "예시 이미지 · 시공 사례"),
    ("project-6b.svg", 1200, 900, "detail", "예시 이미지 · 시공 사례"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for index, (name, w, h, kind, label) in enumerate(PLAN):
        svg = scene(kind, w, h, PALETTES[(index + SHIFT) % len(PALETTES)], label, idx=index)
        (OUT / name).write_text(svg, encoding="utf-8")
    print(f"{len(PLAN)}장을 {OUT} 에 그렸습니다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
