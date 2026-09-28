"""공장 조작대.

    python -m factory.cli templates                        찍을 수 있는 템플릿
    python -m factory.cli probe <주소|파일>                 레퍼런스에서 무엇이 읽히나
    python -m factory.cli plan <주문서>                     무엇을 지을지만 본다
    python -m factory.cli build <주문서> -o <폴더>           실제로 짓는다
    python -m factory.cli batch <주문서폴더> -o <폴더>        여러 건을 한 번에
    python -m factory.cli serve <폴더>                      브라우저로 확인
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import reference
from .catalog import TEMPLATES_DIR, load_catalog
from .intake import BriefError, load_brief
from .matching import rank
from .package import make_zip, write_deploy_configs
from .pipeline import build, make_plan
from .theming import contrast_audit

BRIEF_SUFFIXES = (".json", ".yaml", ".yml")


def _line(char: str = "─", width: int = 58) -> str:
    return char * width


def _print_block(title: str, rows: list[str]) -> None:
    print(f"\n{title}")
    print(_line())
    for row in rows:
        print(f"  {row}")


def cmd_templates(args: argparse.Namespace) -> int:
    for template in load_catalog(args.templates_dir):
        print(f"\n{template.id}  —  {template.name} ({template.page_count}쪽)")
        print(_line())
        print(f"  {template.summary}")
        print(f"  업종: {', '.join(template.industries) or '제한 없음'}")
        print(f"  분위기: {', '.join(template.moods) or '제한 없음'}")
        print(f"  담을 수 있는 기능: {', '.join(template.features)}")
        for page in template.pages:
            print(f"    · {page.filename:<14} {page.nav_label:<8} {' → '.join(page.sections)}")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    target = args.target
    is_file = Path(target).exists()
    findings = reference.probe(
        url="" if is_file else target,
        html_path=target if is_file else "",
        offline=args.offline,
    )
    print(f"\n레퍼런스: {findings.source or target}")
    print(_line())
    data = findings.as_dict()
    for key in ("title", "theme_color", "body_background", "brand_colors", "fonts",
                "google_fonts", "radius_px", "max_block_padding", "nav_links",
                "images", "css_bytes"):
        print(f"  {key:<20} {data.get(key)}")
    if findings.evidence:
        _print_block("읽어 낸 근거", findings.evidence)
    if findings.problems:
        _print_block("문제", findings.problems)
    return 0 if not findings.is_empty() else 1


def _print_plan(plan, warnings: list[str]) -> None:
    brief, style, match = plan.brief, plan.style, plan.match
    print(f"\n{brief.business.name} ({brief.business.industry}) — {brief.site.pages}쪽 요청")
    print(_line("═"))
    print(f"  템플릿   {match.template.name} [{match.template.id}] · 적합도 {match.score}")
    print(f"  스타일   주색 {style.primary} · 강조 {style.accent} · {style.mode} · "
          f"모서리 {style.radius} · 간격 {style.density} · 히어로 {style.hero}")
    print(f"  출처     {style.source} (확신도 {style.confidence})")

    _print_block("왜 이 템플릿인가", match.reasons or ["(근거 없음)"])
    if match.penalties:
        _print_block("맞지 않는 점", match.penalties)
    _print_block("왜 이 스타일인가", style.evidence)
    _print_block(
        "지을 장",
        [f"{p.filename:<14} {p.nav_label:<10} {' → '.join(s.kind for s in p.sections)}"
         for p in plan.content.pages],
    )
    audit = contrast_audit(plan.tokens)
    _print_block("글자 대비", [f"{k:<20} {v}" for k, v in audit.items()])
    todo = plan.content.meta.get("todo", [])
    if todo:
        _print_block("사람이 채워야 할 것", todo)
    skipped = plan.content.meta.get("skipped", [])
    if skipped:
        _print_block("재료가 없어 뺀 것", skipped)
    if warnings:
        _print_block("경고", warnings)


def cmd_validate(args: argparse.Namespace) -> int:
    """주문서가 SITE_CONFIG_SCHEMA_V1 에 맞는지만 본다. 파일은 쓰지 않는다."""
    import json as _json

    from .schema import SCHEMA_VERSION, validate

    path = Path(args.brief)
    if not path.exists():
        print(f"주문서 파일이 없습니다: {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml

        data = yaml.safe_load(text)
    else:
        try:
            data = _json.loads(text)
        except _json.JSONDecodeError as exc:
            print(f"\nJSON 을 읽을 수 없습니다 ({path.name} {exc.lineno}행): {exc.msg}", file=sys.stderr)
            return 2
    result = validate(data)
    print(f"\n{path.name}")
    print(_line())
    print(result.report())
    print(f"\n오류 {len(result.errors)}개 · 확인할 것 {len(result.warnings)}개 · 규격 {SCHEMA_VERSION}")
    return 0 if result.ok else 1


def cmd_plan(args: argparse.Namespace) -> int:
    brief, warnings = load_brief(args.brief)
    plan, findings = make_plan(
        brief,
        templates_dir=args.templates_dir,
        template_id=args.template,
        offline=args.offline,
    )
    _print_plan(plan, warnings + findings.problems)

    if args.all:
        _print_block(
            "다른 템플릿 점수",
            [f"{m.score:>7.2f}  {m.template.id:<20} {m.template.name}"
             for m in rank(brief, load_catalog(args.templates_dir))],
        )
    return 0


def _build_one(args: argparse.Namespace, brief_path: Path, out_dir: Path) -> int:
    brief, warnings = load_brief(brief_path)
    result = build(
        brief,
        out_dir,
        templates_dir=args.templates_dir,
        template_id=args.template,
        offline=args.offline,
        form_action=args.form_action,
        clean=args.clean,
        optimize=not args.no_optimize,
        extra_warnings=warnings,
    )
    if not args.no_deploy_config:
        result.files.extend(write_deploy_configs(result))
    if args.quiet:
        print(f"{brief.business.name}: {result.out_dir} ({len(result.plan.content.pages)}쪽)")
    else:
        _print_plan(result.plan, result.report["warnings"])
        _print_block("쓴 파일", sorted(result.files))
    if args.zip:
        archive = make_zip(result.out_dir)
        print(f"\n  묶음: {archive}")
    print(f"\n  → {result.out_dir}  (미리보기: python -m factory.cli serve {result.out_dir})")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    brief_path = Path(args.brief)
    out_dir = Path(args.out) if args.out else Path("out") / load_brief(brief_path)[0].slug
    return _build_one(args, brief_path, out_dir)


def cmd_batch(args: argparse.Namespace) -> int:
    root = Path(args.briefs_dir)
    briefs = sorted(p for p in root.iterdir() if p.suffix.lower() in BRIEF_SUFFIXES)
    if not briefs:
        print(f"{root} 안에 주문서가 없습니다 ({', '.join(BRIEF_SUFFIXES)})", file=sys.stderr)
        return 1
    out_root = Path(args.out)
    failures = 0
    for path in briefs:
        try:
            brief, _ = load_brief(path)
            code = _build_one(args, path, out_root / brief.slug)
            failures += 1 if code else 0
        except BriefError as exc:
            failures += 1
            print(f"\n[건너뜀] {path.name}\n{exc}", file=sys.stderr)
    print(f"\n{len(briefs) - failures}/{len(briefs)} 건 완료 → {out_root}")
    return 1 if failures else 0


def cmd_serve(args: argparse.Namespace) -> int:
    import functools
    import http.server
    import socketserver

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"폴더가 없습니다: {directory}", file=sys.stderr)
        return 1
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as server:
        print(f"http://127.0.0.1:{args.port}/  ({directory})  — 끝내려면 Ctrl+C")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n멈췄습니다")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="website-factory",
        description="주문서 한 장으로 홈페이지 한 벌을 짓는 공장",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--templates-dir", default=str(TEMPLATES_DIR), help="템플릿 폴더 (기본: 저장소의 templates/)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("templates", help="템플릿 목록")
    p.set_defaults(func=cmd_templates)

    p = sub.add_parser("probe", help="레퍼런스에서 읽히는 것 보기")
    p.add_argument("target", help="사이트 주소 또는 로컬 HTML 파일")
    p.add_argument("--offline", action="store_true", help="네트워크를 쓰지 않는다")
    p.set_defaults(func=cmd_probe)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--template", default="", help="템플릿을 직접 고른다 (id)")
    common.add_argument("--offline", action="store_true", help="레퍼런스를 가져오지 않는다")

    p = sub.add_parser("validate", help="주문서가 규격에 맞는지 본다")
    p.add_argument("brief", help="주문서 파일")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("plan", parents=[common], help="짓기 전에 계획만 본다")
    p.add_argument("brief", help="주문서 파일 (.json/.yaml)")
    p.add_argument("--all", action="store_true", help="모든 템플릿 점수도 함께")
    p.set_defaults(func=cmd_plan)

    build_common = argparse.ArgumentParser(add_help=False)
    build_common.add_argument("--form-action", default="", help="문의폼을 받을 주소")
    build_common.add_argument("--clean", action="store_true", help="산출물 폴더를 먼저 비운다")
    build_common.add_argument("--zip", action="store_true", help="다 지으면 zip 으로 묶는다")
    build_common.add_argument("--no-deploy-config", action="store_true", help="호스팅 설정 파일을 넣지 않는다")
    build_common.add_argument("--quiet", action="store_true", help="한 줄만 출력")
    build_common.add_argument("--no-optimize", action="store_true",
                              help="사진을 줄이지 않고 원본 그대로 쓴다")

    p = sub.add_parser("build", parents=[common, build_common], help="사이트를 짓는다")
    p.add_argument("brief", help="주문서 파일")
    p.add_argument("-o", "--out", default="", help="산출물 폴더 (기본: out/<slug>)")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("batch", parents=[common, build_common], help="폴더 안 주문서를 모두 짓는다")
    p.add_argument("briefs_dir", help="주문서들이 있는 폴더")
    p.add_argument("-o", "--out", default="out", help="산출물 상위 폴더")
    p.set_defaults(func=cmd_batch)

    p = sub.add_parser("serve", help="지은 폴더를 브라우저로 본다")
    p.add_argument("directory", help="산출물 폴더")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BriefError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2
    except (ValueError, FileNotFoundError) as exc:
        print(f"\n오류: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
