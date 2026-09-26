"""내보내기 — 지은 폴더를 그대로 올릴 수 있게 만든다.

정적 파일뿐이므로 빌드 단계가 없다. 흔히 쓰는 호스팅 세 곳의
설정 파일을 같이 넣어 준다. 필요 없으면 지우면 된다.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from .models import BuildResult

NETLIFY = """# Netlify — 이 폴더를 그대로 올립니다.
[build]
  publish = "."
  command = ""

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/*.html"
  [headers.values]
    Cache-Control = "public, max-age=0, must-revalidate"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
"""

VERCEL = """{
  "cleanUrls": true,
  "trailingSlash": false,
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }]
    },
    {
      "source": "/(.*).html",
      "headers": [{ "key": "X-Content-Type-Options", "value": "nosniff" }]
    }
  ]
}
"""


def write_deploy_configs(result: BuildResult) -> list[str]:
    """호스팅 설정 파일을 산출물 폴더에 넣는다. 넣은 파일 이름을 돌려준다."""
    out = result.out_dir
    written: list[str] = []

    (out / "netlify.toml").write_text(NETLIFY, encoding="utf-8")
    written.append("netlify.toml")
    (out / "vercel.json").write_text(VERCEL, encoding="utf-8")
    written.append("vercel.json")

    # GitHub Pages 는 밑줄로 시작하는 폴더를 건너뛰므로 Jekyll 을 끈다.
    (out / ".nojekyll").write_text("", encoding="utf-8")
    written.append(".nojekyll")

    domain = result.plan.brief.site.domain.strip()
    if domain:
        host = domain.replace("https://", "").replace("http://", "").strip("/")
        (out / "CNAME").write_text(host + "\n", encoding="utf-8")
        written.append("CNAME")
    return written


def make_zip(out_dir: str | Path, dest: str | Path | None = None) -> Path:
    """폴더 하나를 zip 한 개로. 고객에게 파일로 넘길 때 쓴다."""
    source = Path(out_dir)
    if not source.is_dir():
        raise FileNotFoundError(f"폴더가 없습니다: {source}")
    target = Path(dest) if dest else source.with_suffix(".zip")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.resolve() != target.resolve():
                archive.write(path, path.relative_to(source))
    return target
