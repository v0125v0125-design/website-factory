#!/usr/bin/env bash
# 미리보기 발행 — 짓고 gh-pages 로 올린다.
#
#   tools/publish_preview.sh                     주문서 전부 (examples/master-interior-01.json + examples/customers/*)
#   tools/publish_preview.sh examples/customers/d-새고객.json ...   고른 것만
#
# 올라가는 곳: https://<계정>.github.io/<저장소>/<slug>/
# GitHub Actions 가 main 에서 자동으로 하는 일과 같습니다. 이 스크립트는
# 손으로 급히 올릴 때 씁니다.
set -euo pipefail

cd "$(dirname "$0")/.."
OUT="${OUT:-_site}"
REMOTE="$(git remote get-url origin)"

python3 tools/build_previews.py "$OUT" "$@"

cd "$OUT"
rm -rf .git
git init -q -b gh-pages
git add -A
git -c user.name="$(git -C .. config user.name || echo preview)" \
    -c user.email="$(git -C .. config user.email || echo preview@local)" \
    commit -qm "preview: $(date +%Y-%m-%d\ %H:%M) 기준 미리보기"
git push -q --force "$REMOTE" gh-pages

SLUG_LIST=$(ls -d */ | sed 's|/||')
BASE=$(printf '%s' "$REMOTE" | sed -E 's|.*github.com[:/]([^/]+)/(.+?)(\.git)?$|https://\1.github.io/\2|')
echo
echo "올렸습니다 → $BASE/"
for slug in $SLUG_LIST; do echo "  $BASE/$slug/"; done
echo "(반영까지 30초쯤 걸립니다)"
