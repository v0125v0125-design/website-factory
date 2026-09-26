"""템플릿 목록 — templates/ 밑의 template.json 들을 읽는다.

한 템플릿은 디렉터리 하나다. 그 안에 설명서(template.json)와
Jinja 파일들이 들어 있고, 공용 조각은 templates/_shared 에서 가져다 쓴다.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import PageSpec, TemplateSpec

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
SHARED_DIR = TEMPLATES_DIR / "_shared"
MANIFEST = "template.json"


class TemplateError(ValueError):
    """템플릿 설명서가 잘못됐다."""


def _page_from(raw: dict, index: int, template_id: str) -> PageSpec:
    if not isinstance(raw, dict):
        raise TemplateError(f"{template_id}: pages[{index}] 가 사전이 아닙니다")
    title = str(raw.get("title") or "").strip()
    if not title:
        raise TemplateError(f"{template_id}: pages[{index}].title 이 없습니다")
    sections = [str(s) for s in raw.get("sections", []) if str(s).strip()]
    if not sections:
        raise TemplateError(f"{template_id}: pages[{index}] 에 섹션이 없습니다")
    return PageSpec(
        slug=str(raw.get("slug") or "").strip().strip("/"),
        title=title,
        nav_label=str(raw.get("nav_label") or title).strip(),
        sections=sections,
        description=str(raw.get("description") or "").strip(),
    )


def load_template(directory: str | Path) -> TemplateSpec:
    root = Path(directory)
    manifest = root / MANIFEST
    if not manifest.exists():
        raise TemplateError(f"{root.name}: {MANIFEST} 이 없습니다")
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TemplateError(f"{root.name}/{MANIFEST} 를 읽을 수 없습니다: {exc}") from exc

    template_id = str(raw.get("id") or root.name)
    pages_raw = raw.get("pages") or []
    if not pages_raw:
        raise TemplateError(f"{template_id}: pages 가 비어 있습니다")
    pages = [_page_from(p, i, template_id) for i, p in enumerate(pages_raw)]
    if not any(p.slug == "" for p in pages):
        raise TemplateError(f"{template_id}: 첫 장(slug 없는 페이지) 이 없습니다")

    declared = raw.get("page_count")
    page_count = int(declared) if declared else len(pages)
    if page_count != len(pages):
        raise TemplateError(
            f"{template_id}: page_count({page_count}) 와 pages 수({len(pages)}) 가 다릅니다"
        )

    for page in pages:
        if not (root / page.filename).exists():
            raise TemplateError(f"{template_id}: {page.filename} 파일이 없습니다")

    return TemplateSpec(
        id=template_id,
        name=str(raw.get("name") or template_id),
        summary=str(raw.get("summary") or ""),
        page_count=page_count,
        pages=pages,
        industries=[str(v).lower() for v in raw.get("industries", [])],
        moods=[str(v).lower() for v in raw.get("moods", [])],
        features=[str(v).lower() for v in raw.get("features", [])],
        goals=[str(v).lower() for v in raw.get("goals", [])],
        hero=str(raw.get("hero") or "split"),
        density=str(raw.get("density") or "regular"),
        root=root,
    )


def load_catalog(templates_dir: str | Path = TEMPLATES_DIR) -> list[TemplateSpec]:
    """쓸 수 있는 템플릿 전부. 이름순으로 돌려준다."""
    base = Path(templates_dir)
    if not base.exists():
        raise TemplateError(f"템플릿 디렉터리가 없습니다: {base}")
    found = []
    for child in sorted(base.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        if not (child / MANIFEST).exists():
            continue
        found.append(load_template(child))
    if not found:
        raise TemplateError(f"{base} 에 템플릿이 하나도 없습니다")
    return found


def get_template(template_id: str, templates_dir: str | Path = TEMPLATES_DIR) -> TemplateSpec:
    for template in load_catalog(templates_dir):
        if template.id == template_id:
            return template
    available = ", ".join(t.id for t in load_catalog(templates_dir))
    raise TemplateError(f"그런 템플릿이 없습니다: {template_id} (있는 것: {available})")
