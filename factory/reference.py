"""레퍼런스 읽기 — 고객이 "이런 느낌으로" 라며 건넨 사이트에서 사실만 긁어 온다.

여기서는 고르지 않는다. 색이 몇 번 나왔고 서체 이름이 무엇이었는지,
본 것만 적어 theming 에 넘긴다. 판단은 theming 이 한다.

원본을 베끼지 않는다: 문장·이미지·마크업은 가져오지 않고
색·서체 이름·모서리 반경·여백 같은 치수만 본다.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from . import colorkit

MAX_BYTES = 2_000_000
TIMEOUT = 8.0
USER_AGENT = "website-factory/0.1 (+style-probe)"

_GENERIC_FAMILIES = {
    "sans-serif", "serif", "monospace", "cursive", "fantasy", "system-ui",
    "inherit", "initial", "unset", "-apple-system", "blinkmacsystemfont",
    "ui-sans-serif", "ui-serif", "ui-monospace", "apple sd gothic neo",
    "malgun gothic", "helvetica neue", "helvetica", "arial", "segoe ui",
    "roboto", "sans", "dotum", "gulim", "tahoma", "verdana",
}
_DECL = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}]+)")
_HEXCOLOR = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
_RGBCOLOR = re.compile(r"rgba?\([^)]*\)")
_PX = re.compile(r"(-?\d*\.?\d+)\s*px")
_REM = re.compile(r"(-?\d*\.?\d+)\s*rem")


class ReferenceUnavailable(RuntimeError):
    """레퍼런스를 가져오지 못했다 — 없는 대로 짓는다."""


@dataclass
class ReferenceFindings:
    """본 것만. 해석은 아직 없다."""

    source: str = ""
    fetched: bool = False
    title: str = ""
    description: str = ""
    theme_color: str = ""
    brand_colors: list[tuple[str, int]] = field(default_factory=list)   # 채도 있는 색
    background_colors: list[tuple[str, int]] = field(default_factory=list)
    body_background: str = ""
    text_colors: list[tuple[str, int]] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    google_fonts: list[str] = field(default_factory=list)
    serif_hint: bool = False
    radii_px: list[float] = field(default_factory=list)
    max_block_padding: float = 0.0
    nav_links: int = 0
    images: int = 0
    has_video: bool = False
    stylesheets: list[str] = field(default_factory=list)
    css_bytes: int = 0
    evidence: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.brand_colors or self.theme_color or self.fonts)

    def dominant_radius(self) -> float | None:
        if not self.radii_px:
            return None
        counts = Counter(round(r) for r in self.radii_px if 0 <= r <= 64)
        if not counts:
            return None
        # 가장 많이 쓰인 값. 같은 수면 작은 쪽 (덜 튀는 쪽) 으로.
        top = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
        return float(top[0])

    def page_background(self) -> str:
        """바탕에 깔린 색. body/html 규칙이 있으면 그것이 답이다."""
        if self.body_background:
            return self.body_background
        # 없으면 채도가 낮은 배경색 — 넓게 깔리는 색은 대개 무채색에 가깝다.
        for color, _ in self.background_colors:
            _, saturation, _l = colorkit.to_hsl(colorkit.parse(color))
            if saturation < 0.15:
                return color
        return ""

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "fetched": self.fetched,
            "title": self.title,
            "theme_color": self.theme_color,
            "brand_colors": [c for c, _ in self.brand_colors[:6]],
            "background": self.page_background(),
            "body_background": self.body_background,
            "fonts": self.fonts[:5],
            "google_fonts": self.google_fonts,
            "radius_px": self.dominant_radius(),
            "max_block_padding": self.max_block_padding,
            "nav_links": self.nav_links,
            "images": self.images,
            "css_bytes": self.css_bytes,
            "evidence": self.evidence,
            "problems": self.problems,
        }


class _Scraper(HTMLParser):
    """style 블록·style 속성·meta·링크 수를 모은다."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.css_chunks: list[str] = []
        self.inline_styles: list[str] = []
        self.stylesheets: list[str] = []
        self.font_links: list[str] = []
        self.theme_color = ""
        self.title = ""
        self.description = ""
        self.nav_links = 0
        self.images = 0
        self.has_video = False
        self._in_style = False
        self._in_title = False
        self._in_nav = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if "style" in a and a["style"]:
            self.inline_styles.append(a["style"])
        if tag == "style":
            self._in_style = True
        elif tag == "title":
            self._in_title = True
        elif tag == "link":
            rel = a.get("rel", "").lower()
            href = a.get("href", "")
            if "stylesheet" in rel and href:
                if "fonts.googleapis.com" in href:
                    self.font_links.append(href)
                else:
                    self.stylesheets.append(href)
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            content = a.get("content", "")
            if name == "theme-color" and content:
                self.theme_color = content.strip()
            elif name in ("description", "og:description") and content and not self.description:
                self.description = content.strip()
        elif tag in ("nav", "header"):
            self._in_nav += 1
        elif tag == "a" and self._in_nav:
            self.nav_links += 1
        elif tag == "img":
            self.images += 1
        elif tag in ("video", "iframe"):
            self.has_video = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self._in_style = False
        elif tag == "title":
            self._in_title = False
        elif tag in ("nav", "header") and self._in_nav:
            self._in_nav -= 1

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self.css_chunks.append(data)
        elif self._in_title and not self.title:
            self.title = data.strip()


def fetch(url: str, timeout: float = TIMEOUT, max_bytes: int = MAX_BYTES) -> str:
    """주소 하나를 텍스트로. 실패하면 ReferenceUnavailable."""
    parsed = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    if parsed.scheme not in ("http", "https"):
        raise ReferenceUnavailable(f"http/https 만 봅니다: {url}")
    request = urllib.request.Request(
        parsed.geturl(),
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/css,*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes)
            charset = response.headers.get_content_charset() or "utf-8"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise ReferenceUnavailable(f"{url} 을 가져오지 못했습니다: {exc}") from exc
    return raw.decode(charset, errors="replace")


def _color_tokens(value: str) -> list[str]:
    return _HEXCOLOR.findall(value) + _RGBCOLOR.findall(value)


def _lengths_px(value: str) -> list[float]:
    out = [float(v) for v in _PX.findall(value)]
    out += [float(v) * 16.0 for v in _REM.findall(value)]
    return out


def _font_families(value: str) -> list[str]:
    families = []
    for part in value.split(","):
        family = part.strip().strip("\"'")
        if not family:
            continue
        if family.lower() in _GENERIC_FAMILIES or family.startswith("var("):
            continue
        families.append(family)
    return families


def _google_families(href: str) -> list[str]:
    query = urllib.parse.urlparse(href).query
    params = urllib.parse.parse_qs(query)
    names: list[str] = []
    for family in params.get("family", []):
        name = family.split(":")[0].replace("+", " ").strip()
        if name:
            names.append(name)
    return names


_RULE = re.compile(r"([^{}@]+)\{([^{}]*)\}")
_BODY_SELECTOR = re.compile(r"(?:^|[\s,>])(?:html|body)(?=[\s,{:.\[]|$)", re.I)


def find_body_background(css: str) -> str:
    """body 또는 html 규칙이 지정한 배경색. 나중에 나온 것이 이긴다."""
    found = ""
    for match in _RULE.finditer(css):
        selectors, block = match.group(1), match.group(2)
        if not _BODY_SELECTOR.search(selectors):
            continue
        for prop, value in _DECL.findall(block):
            if not prop.lower().startswith("background"):
                continue
            for token in _color_tokens(value):
                if colorkit.is_color(token):
                    found = colorkit.to_hex(colorkit.parse(token))
    return found


def analyze_css(css: str, findings: ReferenceFindings) -> None:
    """CSS 덩어리에서 색·서체·모서리·여백을 센다."""
    if not findings.body_background:
        findings.body_background = find_body_background(css)
    brand = Counter()
    backgrounds = Counter()
    texts = Counter()
    fonts: list[str] = []

    for prop, value in _DECL.findall(css):
        prop = prop.lower()
        value_l = value.strip().lower()

        if "font-family" in prop:
            fonts.extend(_font_families(value))
            if "serif" in value_l and "sans-serif" not in value_l:
                findings.serif_hint = True

        if "color" in prop or "background" in prop or "gradient" in value_l:
            for token in _color_tokens(value):
                if not colorkit.is_color(token):
                    continue
                hex_value = colorkit.to_hex(colorkit.parse(token))
                _, saturation, lightness = colorkit.to_hsl(colorkit.parse(hex_value))
                is_neutral = saturation < 0.15 or lightness > 0.93 or lightness < 0.07
                if prop in ("color",) and not is_neutral:
                    texts[hex_value] += 1
                if prop.startswith("background"):
                    backgrounds[hex_value] += 1
                if not is_neutral:
                    brand[hex_value] += 1

        if "border-radius" in prop:
            findings.radii_px.extend(_lengths_px(value))

        if prop in ("padding", "padding-top", "padding-bottom", "padding-block"):
            for length in _lengths_px(value):
                findings.max_block_padding = max(findings.max_block_padding, length)

    findings.brand_colors = brand.most_common(12)
    # 배경은 "가장 넓게 깔린 색" 을 알고 싶으므로 많이 쓰인 순서 그대로.
    findings.background_colors = backgrounds.most_common(8)
    findings.text_colors = texts.most_common(8)
    for family in fonts:
        if family not in findings.fonts:
            findings.fonts.append(family)
    findings.css_bytes += len(css)


def analyze_html(
    html: str,
    source: str = "",
    follow_css: bool = False,
    base_url: str = "",
    max_stylesheets: int = 3,
) -> ReferenceFindings:
    """HTML 한 장(과 필요하면 딸린 CSS)에서 사실을 긁는다."""
    findings = ReferenceFindings(source=source, fetched=True)
    scraper = _Scraper()
    try:
        scraper.feed(html)
    except Exception as exc:  # 망가진 마크업도 흔하다
        findings.problems.append(f"HTML 을 끝까지 읽지 못했습니다: {exc}")

    findings.title = scraper.title
    findings.description = scraper.description
    findings.nav_links = scraper.nav_links
    findings.images = scraper.images
    findings.has_video = scraper.has_video
    findings.stylesheets = scraper.stylesheets
    if scraper.theme_color and colorkit.is_color(scraper.theme_color):
        findings.theme_color = colorkit.to_hex(colorkit.parse(scraper.theme_color))
        findings.evidence.append(f"meta theme-color = {findings.theme_color}")

    for href in scraper.font_links:
        for name in _google_families(href):
            if name not in findings.google_fonts:
                findings.google_fonts.append(name)
    if findings.google_fonts:
        findings.evidence.append("구글 폰트 링크: " + ", ".join(findings.google_fonts[:4]))

    css = "\n".join(scraper.css_chunks)
    if scraper.inline_styles:
        css += "\n" + "\n".join(f"x{{{s}}}" for s in scraper.inline_styles)

    if follow_css and base_url and scraper.stylesheets:
        for href in scraper.stylesheets[:max_stylesheets]:
            absolute = urllib.parse.urljoin(base_url, href)
            try:
                css += "\n" + fetch(absolute)
                findings.evidence.append(f"CSS 읽음: {absolute}")
            except ReferenceUnavailable as exc:
                findings.problems.append(str(exc))

    analyze_css(css, findings)

    if findings.brand_colors:
        top = ", ".join(f"{c}×{n}" for c, n in findings.brand_colors[:3])
        findings.evidence.append(f"많이 쓰인 색: {top}")
    if findings.fonts:
        findings.evidence.append("서체 선언: " + ", ".join(findings.fonts[:4]))
    radius = findings.dominant_radius()
    if radius is not None:
        findings.evidence.append(f"모서리 반경 {radius:g}px 가 가장 잦음")
    if findings.max_block_padding:
        findings.evidence.append(f"가장 큰 블록 여백 {findings.max_block_padding:g}px")
    if not findings.evidence:
        findings.problems.append("읽을 만한 스타일 신호가 없습니다 (스크립트로 그리는 사이트일 수 있음)")
    return findings


def probe(
    url: str = "",
    html_path: str | Path = "",
    offline: bool = False,
    follow_css: bool = True,
) -> ReferenceFindings:
    """레퍼런스 한 건을 살핀다. 주소가 안 되면 문제만 적고 빈손으로 돌아온다."""
    if html_path:
        path = Path(html_path)
        if not path.exists():
            return ReferenceFindings(
                source=str(path), problems=[f"레퍼런스 파일이 없습니다: {path}"]
            )
        return analyze_html(path.read_text(encoding="utf-8", errors="replace"), source=str(path))

    if not url:
        return ReferenceFindings(problems=["레퍼런스가 지정되지 않았습니다"])
    if offline:
        return ReferenceFindings(source=url, problems=["오프라인 모드라 레퍼런스를 보지 않았습니다"])

    try:
        html = fetch(url)
    except ReferenceUnavailable as exc:
        return ReferenceFindings(source=url, problems=[str(exc)])
    base = url if "://" in url else "https://" + url
    return analyze_html(html, source=url, follow_css=follow_css, base_url=base)
