#!/usr/bin/env bash
# Заливає сайт на Cloudflare: бере закомічені файли (git archive HEAD), лишає тільки публічні
# й запускає wrangler із тимчасової теки — щоб не зачепити чужі налаштування й не залити службове.
# На комп'ютері: ./cloudflare/deploy.sh після коміту. У GitHub Actions: потрібні CLOUDFLARE_API_TOKEN і CLOUDFLARE_ACCOUNT_ID.
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
if [ -n "${CI:-}" ]; then
  npx --yes wrangler@4 deploy
else
  npx --prefix "$HOME/Documents/fitnessmama-platform" wrangler deploy
fi
