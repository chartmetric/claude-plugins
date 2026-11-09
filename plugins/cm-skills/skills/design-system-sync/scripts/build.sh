#!/bin/bash
# Repo -> Claude Design: build the files a Design System artifact holds from a chartmetric-design-system checkout.
# usage: REPO=<clean design-system clone> WEBAPP=<chartmetric-web-app checkout> OUT=<dir> bash build.sh
# Needs FONT_AWESOME_TOKEN in the environment (Pro icon packages). Never runs in the user's own checkout:
# pass a fresh clone, because `npm ci` replaces node_modules.
# Writes under $OUT/project: tokens.json, components/bundle.js, components/bundle.css, components/index.d.ts,
# components/lib/fa-icons.js, fonts/InterVariable*.woff2, licenses/Inter-OFL.txt. READMEs and previews are left alone.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${REPO:?}" "${WEBAPP:?}" "${OUT:?}" "${FONT_AWESOME_TOKEN:?FONT_AWESOME_TOKEN is required for the Pro icon packages}"
INTER=4.1.1   # inter-ui on npm; pinned, bump deliberately

cd "$REPO"
npm ci --ignore-scripts --no-audit --no-fund >/dev/null
npx vite build >/dev/null
SHA=$(git rev-parse --short HEAD)
mkdir -p "$OUT/project/components/lib" "$OUT/project/fonts" "$OUT/project/licenses"

# tokens.json from the CSS custom properties
python3 "$HERE/tokens.py" styles/index.css "$OUT/project/tokens.json" "main@$SHA"

# one IIFE bundle assigning window.Chartmetric (React from the page's globals)
{ for d in src/components/*/; do echo "export * from './dist/components/$(basename "$d")/index.js';"; done
  echo "export * from './dist/providers/I18nProvider.js';"; } > .ds-entry.js
REPO="$REPO" node "$HERE/bundle.mjs" .ds-entry.js "$OUT/bundle.raw.js"
rm -f .ds-entry.js
perl -pi -e 's/<!--/\\x3C!--/g' "$OUT/bundle.raw.js"
HDR=$(ls src/components | python3 -c "import json,sys;print(json.dumps({'format':4,'namespace':'Chartmetric','components':[{'name':x} for x in sys.stdin.read().split()]},separators=(',',':')))")
{ echo "/* @ds-bundle: $HDR */"; cat "$OUT/bundle.raw.js"; } > "$OUT/project/components/bundle.js"
rm "$OUT/bundle.raw.js"
if grep -q '</script' "$OUT/project/components/bundle.js"; then echo "bundle contains </script" >&2; exit 1; fi

# stylesheet: trimmed, then the host base rule. Components use font-family: inherit, so the page must set Inter
# (the web app does it in pages/_document.tsx); without this rule Claude Design renders the system font.
REPO="$REPO" node "$HERE/trimcss.mjs" dist/style.css "$OUT/bundle.trim.css" >/dev/null
{ printf '@charset "UTF-8";\n'
  printf '%s\n' '/* Chartmetric base: components inherit font-family (font-family: inherit), so the host sets Inter, as the web app does. */'
  printf '%s\n' 'html,body{font-family:var(--font-sans,"Inter",system-ui,-apple-system,"Segoe UI",sans-serif);-webkit-font-smoothing:antialiased}'
  sed '1s/^@charset "UTF-8";//' "$OUT/bundle.trim.css"; } > "$OUT/project/components/bundle.css"
rm "$OUT/bundle.trim.css"

python3 "$HERE/dts.py" dist/components "$OUT/project/components/index.d.ts"

# the Font Awesome icons the web app actually imports, as window.ChartmetricIcons
git -C "$WEBAPP" fetch -q origin master
node "$HERE/scan_icons.mjs" "$WEBAPP" > "$OUT/icons-used.json"
node "$HERE/build_icons.cjs" "$REPO" "$OUT/icons-used.json" "$OUT/project/components/lib/fa-icons.js"

# Inter (the repo ships no font files)
B="https://cdn.jsdelivr.net/npm/inter-ui@$INTER"
curl -sfL -o "$OUT/project/fonts/InterVariable.woff2" "$B/variable/InterVariable.woff2"
curl -sfL -o "$OUT/project/fonts/InterVariable-Italic.woff2" "$B/variable/InterVariable-Italic.woff2"
curl -sfL -o "$OUT/project/licenses/Inter-OFL.txt" "$B/LICENSE.txt"

echo "built main@$SHA into $OUT/project"
