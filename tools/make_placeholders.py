"""개발용 임시 이미지를 그린다.

고객 사진이 아직 없을 때 자리를 채우는 SVG 를 만든다. 남의 사진을
쓰지 않으려고 직접 그린다. 비율을 일부러 섞어 두었다 —
16:9 · 4:3 · 1:1 · 3:4 가 한 격자에 섞여도 레이아웃이 버티는지
눈으로 확인하기 위해서다.

    python tools/make_placeholders.py [내보낼폴더]
"""

from __future__ import annotations

import sys
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "examples/photos/interior")

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

def scene(kind: str, w: int, h: int, palette: tuple[str, str, str, str], label: str) -> str:
    wall, floor, mid, ink = palette
    floor_y = int(h * 0.68)
    parts = [
        f'<rect width="{w}" height="{h}" fill="{wall}"/>',
        f'<rect y="{floor_y}" width="{w}" height="{h - floor_y}" fill="{floor}"/>',
    ]

    if kind == "room":
        parts += [
            f'<rect x="{int(w*.06)}" y="{int(h*.12)}" width="{int(w*.30)}" height="{int(h*.46)}" rx="4" fill="#FFFFFF" opacity=".72"/>',
            f'<rect x="{int(w*.06)}" y="{int(h*.12)}" width="{int(w*.30)}" height="{int(h*.46)}" rx="4" fill="none" stroke="{mid}" stroke-width="3"/>',
            f'<line x1="{int(w*.21)}" y1="{int(h*.12)}" x2="{int(w*.21)}" y2="{int(h*.58)}" stroke="{mid}" stroke-width="3"/>',
            f'<rect x="{int(w*.45)}" y="{int(h*.44)}" width="{int(w*.44)}" height="{int(h*.20)}" rx="6" fill="{mid}"/>',
            f'<rect x="{int(w*.49)}" y="{int(h*.36)}" width="{int(w*.13)}" height="{int(h*.09)}" rx="4" fill="{ink}" opacity=".45"/>',
            f'<circle cx="{int(w*.80)}" cy="{int(h*.22)}" r="{int(min(w,h)*.07)}" fill="{ink}" opacity=".30"/>',
            f'<line x1="{int(w*.80)}" y1="0" x2="{int(w*.80)}" y2="{int(h*.15)}" stroke="{ink}" stroke-width="2" opacity=".35"/>',
        ]
    elif kind == "kitchen":
        parts += [
            f'<rect x="{int(w*.05)}" y="{int(h*.40)}" width="{int(w*.90)}" height="{int(h*.10)}" rx="3" fill="{ink}" opacity=".55"/>',
            f'<rect x="{int(w*.05)}" y="{int(h*.50)}" width="{int(w*.90)}" height="{int(h*.18)}" fill="{mid}"/>',
            f'<rect x="{int(w*.10)}" y="{int(h*.14)}" width="{int(w*.34)}" height="{int(h*.20)}" rx="3" fill="{mid}" opacity=".8"/>',
            f'<rect x="{int(w*.52)}" y="{int(h*.14)}" width="{int(w*.34)}" height="{int(h*.20)}" rx="3" fill="{mid}" opacity=".55"/>',
            f'<circle cx="{int(w*.30)}" cy="{int(h*.60)}" r="{int(min(w,h)*.035)}" fill="{wall}"/>',
            f'<circle cx="{int(w*.70)}" cy="{int(h*.60)}" r="{int(min(w,h)*.035)}" fill="{wall}"/>',
        ]
    elif kind == "bath":
        parts += [
            f'<rect x="{int(w*.08)}" y="{int(h*.18)}" width="{int(w*.36)}" height="{int(h*.44)}" rx="6" fill="#FFFFFF" opacity=".66"/>',
            f'<rect x="{int(w*.52)}" y="{int(h*.30)}" width="{int(w*.36)}" height="{int(h*.32)}" rx="8" fill="{mid}"/>',
            f'<rect x="{int(w*.60)}" y="{int(h*.16)}" width="{int(w*.20)}" height="{int(h*.10)}" rx="4" fill="{ink}" opacity=".35"/>',
        ]
    else:  # detail
        parts += [
            f'<circle cx="{int(w*.50)}" cy="{int(h*.44)}" r="{int(min(w,h)*.22)}" fill="{mid}"/>',
            f'<rect x="{int(w*.12)}" y="{int(h*.70)}" width="{int(w*.76)}" height="{int(h*.06)}" rx="3" fill="{ink}" opacity=".35"/>',
            f'<line x1="0" y1="{int(h*.30)}" x2="{w}" y2="{int(h*.30)}" stroke="{ink}" stroke-width="2" opacity=".18"/>',
        ]

    parts.append(
        f'<text x="{w//2}" y="{h - max(18, int(h*.05))}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="{max(13, int(min(w, h) * .045))}" '
        f'fill="{ink}" opacity=".62">{label}</text>'
    )
    body = "".join(parts)
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
        svg = scene(kind, w, h, PALETTES[index % len(PALETTES)], label)
        (OUT / name).write_text(svg, encoding="utf-8")
    print(f"{len(PLAN)}장을 {OUT} 에 그렸습니다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
