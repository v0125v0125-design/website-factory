"""공장 라인 — 주문서 한 장에서 배포 가능한 사이트 한 벌까지.

     주문서 읽기 → 레퍼런스 살피기 → 스타일 정하기
   → 템플릿 고르기 → 사진 챙기기 → 원고 채우기 → 파일 쓰기 → 보고서

각 칸이 무엇을 왜 했는지 보고서(build_report.json)와 납품 메모에 남긴다.
고객에게 "왜 이 디자인인가" 를 설명할 수 있어야 팔 수 있다.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import images, matching, reference, theming
from .catalog import TEMPLATES_DIR, get_template, load_catalog
from .content import build_content
from .intake import load_brief
from .models import Brief, BuildPlan, BuildResult, TemplateSpec
from .render import render_site

IMAGE_DIR = "assets/img"


def _stage_assets(
    brief: Brief, out_dir: Path, optimize: bool = True
) -> tuple[list[str], list[str], images.ImageReport]:
    """주문서가 가리키는 로컬 파일을 산출물 안으로 옮기고 경로를 고친다.

    사진이 들어갈 수 있는 칸이 여러 곳(로고·히어로·소개·서비스·시공사례·
    공유이미지·파비콘)이므로 한 군데서 전부 훑는다. 옮기면서 역할에 맞는
    크기로 줄이고 WebP 로 바꾼다 — 원본 파일은 건드리지 않는다.
    """
    copied: list[str] = []
    warnings: list[str] = []
    report = images.ImageReport()
    base = Path(brief.source_path).parent if brief.source_path else Path.cwd()
    target = out_dir / IMAGE_DIR
    seen: dict[str, tuple[str, int]] = {}   # 원본 경로 → (산출물 이름, 쓰인 최대폭)

    def move(src: str, role: str = "default") -> str:
        if not src or src.startswith(("http://", "https://", "data:", IMAGE_DIR + "/")):
            return src
        want = images.max_width_for(role)
        if src in seen:
            name, had = seen[src]
            if want <= had:
                return f"{IMAGE_DIR}/{name}"
            # 같은 사진을 더 큰 자리에서도 쓴다면 큰 쪽에 맞춰 다시 만든다
        found = next((c for c in (Path(src), base / src) if c.is_file()), None)
        if found is None:
            warnings.append(f"파일을 못 찾았습니다: {src} (주소를 그대로 둡니다)")
            seen[src] = (Path(src).name, 10 ** 6)
            return src
        name = images.optimize(found, target, role=role, enabled=optimize, report=report)
        moved = f"{IMAGE_DIR}/{name}"
        seen[src] = (name, want)
        if moved not in copied:
            copied.append(moved)
        return moved

    for image in brief.gallery:
        image.src = move(image.src, "gallery")
    brief.brand.logo = move(brief.brand.logo, "logo")
    brief.hero.image = move(brief.hero.image, "hero")
    brief.about.image = move(brief.about.image, "about")
    for item in brief.items:
        item.image = move(item.image, "service")
    for project in brief.projects:
        project.image = move(project.image, "project")
        project.images = [move(i, "project") for i in project.images]
    brief.seo.og_image = move(brief.seo.og_image, "og")
    brief.seo.favicon = move(brief.seo.favicon, "logo")
    warnings.extend(report.warnings)
    return copied, warnings, report


def make_plan(
    brief: Brief,
    templates_dir: str | Path = TEMPLATES_DIR,
    template_id: str = "",
    offline: bool = False,
    findings: reference.ReferenceFindings | None = None,
) -> tuple[BuildPlan, reference.ReferenceFindings]:
    """짓기 전에 무엇을 지을지 정한다 — 파일은 아직 쓰지 않는다."""
    if findings is None:
        if brief.reference.is_empty():
            findings = reference.ReferenceFindings(problems=["레퍼런스가 없습니다"])
        else:
            findings = reference.probe(
                url=brief.reference.url,
                html_path=brief.reference.html_path,
                offline=offline,
            )

    style = theming.build_style(brief, findings)
    tokens = theming.build_tokens(style)

    chosen = template_id or brief.site.template
    if chosen:
        template: TemplateSpec = get_template(chosen, templates_dir)
        match = matching.score_template(brief, template)
        match.reasons.insert(
            0, "사람이 직접 지정한 템플릿" if template_id else "주문서가 지정한 템플릿"
        )
    else:
        match = matching.choose(brief, load_catalog(templates_dir))
        template = match.template

    # 템플릿이 권하는 형태를 존중한다 — 레퍼런스가 말해 준 것이 없을 때만.
    changes: dict[str, str] = {}
    if style.hero != template.hero and not (brief.gallery or brief.projects or brief.hero.image):
        changes["hero"] = template.hero
        style.evidence.append(f"히어로: 템플릿 기본 {template.hero}형으로 맞춤")
    if style.density != template.density and not findings.max_block_padding:
        changes["density"] = template.density
        style.evidence.append(f"간격: 템플릿 기본 {template.density}로 맞춤")
    if changes:
        style = theming.StyleProfile(**{**style.__dict__, **changes})
        tokens = theming.build_tokens(style)

    content = build_content(brief, template, style)
    plan = BuildPlan(
        brief=brief, template=template, style=style, match=match, tokens=tokens, content=content
    )
    return plan, findings


def _report(
    plan: BuildPlan,
    findings: reference.ReferenceFindings,
    files: list[str],
    warnings: list[str],
) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "brief": {
            "name": plan.brief.business.name,
            "industry": plan.brief.business.industry,
            "slug": plan.brief.slug,
            "pages_requested": plan.brief.site.pages,
            "features_requested": plan.brief.site.features,
            "goals": plan.brief.site.goals,
            "source": plan.brief.source_path,
        },
        "template": {
            "id": plan.template.id,
            "name": plan.template.name,
            "page_count": plan.template.page_count,
            "score": plan.match.score,
            "reasons": plan.match.reasons,
            "penalties": plan.match.penalties,
        },
        "style": {
            "primary": plan.style.primary,
            "accent": plan.style.accent,
            "mode": plan.style.mode,
            "radius": plan.style.radius,
            "density": plan.style.density,
            "hero": plan.style.hero,
            "source": plan.style.source,
            "confidence": plan.style.confidence,
            "fonts": {"heading": plan.style.fonts.heading, "body": plan.style.fonts.body},
            "evidence": plan.style.evidence,
        },
        "reference": findings.as_dict(),
        "contrast": theming.contrast_audit(plan.tokens),
        "pages": [
            {
                "file": page.filename,
                "title": page.title,
                "sections": [s.kind for s in page.sections],
            }
            for page in plan.content.pages
        ],
        "weight_bytes": None,   # build() 가 다 쓴 뒤 채운다
        "todo": plan.content.meta.get("todo", []),
        "skipped": plan.content.meta.get("skipped", []),
        "warnings": warnings,
        "files": files,
    }


def _handoff(report: dict) -> str:
    """사람이 읽는 납품 메모."""
    lines: list[str] = []
    brief, template, style = report["brief"], report["template"], report["style"]
    lines.append(f"# {brief['name']} 홈페이지 — 납품 메모")
    lines.append("")
    lines.append(f"- 지은 시각: {report['generated_at']}")
    lines.append(f"- 템플릿: {template['name']} (`{template['id']}`, {template['page_count']}쪽, 적합도 {template['score']})")
    lines.append(f"- 스타일 출처: {style['source']} (확신도 {style['confidence']})")
    lines.append(f"- 주색 {style['primary']} · 강조색 {style['accent']} · {style['mode']} 배경 · 모서리 {style['radius']} · 간격 {style['density']}")
    lines.append("")

    lines.append("## 왜 이 템플릿인가")
    for reason in template["reasons"] or ["(근거 없음)"]:
        lines.append(f"- {reason}")
    if template["penalties"]:
        lines.append("")
        lines.append("맞지 않는 점:")
        for penalty in template["penalties"]:
            lines.append(f"- {penalty}")
    lines.append("")

    lines.append("## 왜 이 스타일인가")
    for item in style["evidence"]:
        lines.append(f"- {item}")
    lines.append("")

    if report["todo"]:
        lines.append("## 납품 전에 채워야 할 것")
        lines.append("")
        lines.append("본문에 `[...]` 로 남아 있는 자리입니다. 지어내지 않고 비워 두었습니다.")
        lines.append("")
        for item in report["todo"]:
            lines.append(f"- [ ] {item}")
        lines.append("")

    if report["skipped"]:
        lines.append("## 재료가 없어 뺀 섹션")
        for item in report["skipped"]:
            lines.append(f"- {item}")
        lines.append("")

    if report["warnings"]:
        lines.append("## 확인할 것")
        for item in report["warnings"]:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## 글자 대비 (WCAG)")
    lines.append("")
    lines.append("| 조합 | 대비 | 기준 |")
    lines.append("| --- | --- | --- |")
    for label, value in report["contrast"].items():
        need = 4.5 if "text" in label or "on-primary" in label else 3.0
        mark = "통과" if value >= need else f"미달 (기준 {need})"
        lines.append(f"| {label} | {value} | {mark} |")
    lines.append("")

    pictures = report.get("images") or {}
    if pictures.get("files"):
        saved = pictures["saved_bytes"] / 1024
        lines.append("## 사진")
        lines.append("")
        lines.append(
            f"- {pictures['files']}장 중 {pictures['converted']}장을 WebP 로 바꿔 "
            f"{pictures['bytes_before'] / 1024:.0f}KB → {pictures['bytes_after'] / 1024:.0f}KB "
            f"({saved:.0f}KB 절약)"
        )
        for row in pictures.get("largest", [])[:3]:
            lines.append(f"- 가장 무거운 것: `{row['file']}` {row['bytes'] / 1024:.0f}KB {row['px'] or ''}")
        for note in pictures.get("warnings", []):
            lines.append(f"- ⚠ {note}")
        lines.append("")

    lines.append("## 파일")
    for name in report["files"]:
        lines.append(f"- `{name}`")
    lines.append("")
    lines.append("## 올리는 방법")
    lines.append("")
    lines.append("이 폴더 전체가 정적 사이트입니다. 빌드 과정이 없습니다.")
    lines.append("")
    lines.append("- 미리보기: `python -m factory.cli serve <이 폴더>`")
    lines.append("- Netlify: 폴더를 그대로 끌어다 놓거나 `netlify deploy --dir=.`")
    lines.append("- Vercel: `vercel --prod`")
    lines.append("- 일반 웹호스팅: FTP 로 폴더 내용을 public_html 에 올립니다")
    return "\n".join(lines) + "\n"


def build(
    brief: Brief,
    out_dir: str | Path,
    templates_dir: str | Path = TEMPLATES_DIR,
    template_id: str = "",
    offline: bool = False,
    form_action: str = "",
    clean: bool = False,
    optimize: bool = True,
    extra_warnings: list[str] | None = None,
) -> BuildResult:
    """주문서 하나를 사이트 한 벌로."""
    out = Path(out_dir)
    if clean and out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    warnings = list(extra_warnings or [])
    copied, image_warnings, image_report = _stage_assets(brief, out, optimize=optimize)
    warnings.extend(image_warnings)

    plan, findings = make_plan(
        brief, templates_dir=templates_dir, template_id=template_id, offline=offline
    )
    warnings.extend(findings.problems)

    delivered = len(plan.content.pages)
    if delivered != brief.site.pages:
        warnings.append(
            f"{brief.site.pages}쪽을 요청했지만 {delivered}쪽을 냈습니다 — "
            "재료가 없어 뺀 장이 있습니다 (납품메모 참고)"
        )

    files = render_site(plan, out, form_action=form_action)
    files.extend(copied)

    report = _report(plan, findings, sorted(files), warnings)
    report["images"] = image_report.summary()
    (out / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report["weight_bytes"] = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    (out / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "납품메모.md").write_text(_handoff(report), encoding="utf-8")

    return BuildResult(
        plan=plan,
        out_dir=out,
        files=sorted(files + ["build_report.json", "납품메모.md"]),
        report=report,
    )


def build_from_file(
    brief_path: str | Path,
    out_dir: str | Path,
    **kwargs,
) -> BuildResult:
    brief, warnings = load_brief(brief_path)
    kwargs.setdefault("extra_warnings", [])
    kwargs["extra_warnings"] = list(kwargs["extra_warnings"]) + warnings
    return build(brief, out_dir, **kwargs)
