"""사진 줄이기 — 고객이 휴대폰으로 찍은 8MB 사진을 그대로 올려도 되게.

역할마다 최대 폭이 다르다. 첫 화면 사진과 카드 썸네일에 같은 크기를 쓸 이유가 없다.

  히어로 1920 · 시공사례 1600 · 본문 1200 · 카드 900 · 썸네일 500

원본은 건드리지 않는다. 산출물 폴더에 WebP 를 새로 쓰고, 그것이 원본보다
크면 원본을 그대로 쓴다. Pillow 가 없거나 처리에 실패하면 **조용히 넘어가지
않고** 원본을 복사한 뒤 경고를 남긴다 — 사진이 무거운 채로 팔려 나가는 것을
사람이 알아야 하기 때문이다.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

# 역할 → 최대 가로폭(px)
ROLE_WIDTH = {
    "hero": 1920,
    "project": 1600,
    "about": 1200,
    "gallery": 1200,
    "og": 1200,
    "service": 900,
    "thumb": 500,
    "logo": 400,
    "default": 1200,
}
WEBP_QUALITY = 82
# 이미 벡터이거나 애니메이션인 것은 손대지 않는다.
PASS_THROUGH = {".svg", ".gif", ".ico", ".webp", ".avif"}
RASTER = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".heic", ".heif"}


@dataclass
class ImageReport:
    """무엇을 얼마나 줄였는지. 보고서에 그대로 실린다."""

    rows: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def saved_bytes(self) -> int:
        return sum(max(0, r["before"] - r["after"]) for r in self.rows)

    @property
    def total_after(self) -> int:
        return sum(r["after"] for r in self.rows)

    def summary(self) -> dict:
        converted = [r for r in self.rows if r["action"] == "webp"]
        return {
            "files": len(self.rows),
            "converted": len(converted),
            "bytes_before": sum(r["before"] for r in self.rows),
            "bytes_after": self.total_after,
            "saved_bytes": self.saved_bytes,
            "largest": sorted(
                ({"file": r["file"], "bytes": r["after"], "px": r["px"]} for r in self.rows),
                key=lambda r: -r["bytes"],
            )[:5],
            "warnings": self.warnings,
        }


def pillow() -> object | None:
    try:
        from PIL import Image  # noqa: PLC0415

        return Image
    except ImportError:
        return None


def max_width_for(role: str) -> int:
    return ROLE_WIDTH.get(role, ROLE_WIDTH["default"])


def optimize(
    source: Path,
    target_dir: Path,
    role: str = "default",
    enabled: bool = True,
    quality: int = WEBP_QUALITY,
    report: ImageReport | None = None,
) -> str:
    """사진 한 장을 산출물 폴더에 넣고, 거기서 쓸 파일 이름을 돌려준다."""
    report = report if report is not None else ImageReport()
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower()
    before = source.stat().st_size

    def keep(reason: str, name: str | None = None) -> str:
        destination = target_dir / (name or source.name)
        if destination.resolve() != source.resolve():
            shutil.copy2(source, destination)
        report.rows.append(
            {"file": destination.name, "before": before, "after": destination.stat().st_size,
             "action": reason, "px": None, "role": role}
        )
        return destination.name

    if not enabled or suffix in PASS_THROUGH:
        return keep("copy")
    if suffix not in RASTER:
        report.warnings.append(f"{source.name}: 모르는 형식이라 그대로 복사했습니다")
        return keep("copy")

    Image = pillow()
    if Image is None:
        note = "Pillow 가 없어 사진을 줄이지 못했습니다 — `pip install Pillow` (원본을 그대로 씁니다)"
        if note not in report.warnings:
            report.warnings.append(note)
        return keep("copy")

    try:
        from PIL import ImageOps

        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)  # 휴대폰 사진의 회전 정보를 실제로 적용
            image.load()
            width, height = image.size
            limit = max_width_for(role)
            if width > limit:  # 키우지는 않는다
                new_height = max(1, round(height * limit / width))
                image = image.resize((limit, new_height), Image.LANCZOS)
            if image.mode in ("P", "LA"):
                image = image.convert("RGBA")
            elif image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")
            destination = target_dir / (source.stem + ".webp")
            image.save(destination, "WEBP", quality=quality, method=6)
            after = destination.stat().st_size
            if after >= before and max(image.size) <= max(width, height):
                # 줄이지 못했으면 원본이 낫다
                destination.unlink(missing_ok=True)
                return keep("copy")
            report.rows.append(
                {"file": destination.name, "before": before, "after": after,
                 "action": "webp", "px": f"{image.size[0]}×{image.size[1]}", "role": role}
            )
            return destination.name
    except Exception as exc:  # 사진 하나 때문에 납품 전체가 막히면 안 된다
        report.warnings.append(f"{source.name}: 사진을 줄이지 못했습니다 ({exc}) — 원본을 그대로 씁니다")
        return keep("copy")
