#!/usr/bin/env bash
# Заливає сайт на Cloudflare: бере закомічені файли (git archive HEAD), лишає тільки публічні
# й запускає wrangler із тимчасової теки — щоб не зачепити чужі налаштування й не залити службове.
# На комп'ютері: ./cloudflare/deploy.sh після коміту. Cloudflare сам запускає цей скрипт після кожного git push
# (Workers Builds, команда заливки: bash cloudflare/deploy.sh) — так на сайт потрапляють і сторінки закладів від розкладу.
set -euo pipefail

# службові файли й теки, яким не місце на сайті
PRIVATE_PATHS=(tools cloudflare .github .gitignore)

SITE="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/public"

cd "$SITE"
git archive HEAD | tar -x -C "$STAGE/public"
cp "$STAGE/public/cloudflare/wrangler.jsonc" "$STAGE/wrangler.jsonc"
for path in "${PRIVATE_PATHS[@]}"; do rm -rf "$STAGE/public/$path"; done

if [ ! -f "$STAGE/public/index.html" ]; then
  echo "У зібраній копії немає index.html — зупиняюсь." >&2
  exit 1
fi

cd "$STAGE"
# у збірці Cloudflare (WORKERS_CI) чи GitHub (CI) беремо wrangler з мережі, на комп'ютері — уже встановлений
if [ -n "${CI:-}${WORKERS_CI:-}" ]; then
  npx --yes wrangler@4 deploy
else
  npx --prefix "$HOME/Documents/fitnessmama-platform" wrangler deploy
fi
