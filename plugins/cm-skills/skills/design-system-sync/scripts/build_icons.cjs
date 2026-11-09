// usage: node build_icons.cjs <design-system checkout> <used.json from scan_icons.mjs> <out fa-icons.js>
// Resolves every Font Awesome icon the web app imports from the design-system checkout's own
// node_modules (Pro packages need FONT_AWESOME_TOKEN at install) and writes window.ChartmetricIcons.
const fs = require('fs');
const path = require('path');
const [repo, usedPath, out] = process.argv.slice(2);
const used = JSON.parse(fs.readFileSync(usedPath, 'utf8'));
const STYLE = {
  '@fortawesome/pro-regular-svg-icons': 'regular',
  '@fortawesome/pro-solid-svg-icons': 'solid',
  '@fortawesome/pro-duotone-svg-icons': 'duotone',
  '@fortawesome/free-brands-svg-icons': 'brands',
};
const icons = {};
const missing = [];
for (const [pkg, list] of Object.entries(used)) {
  const style = STYLE[pkg];
  if (!style) continue;
  const mod = require(require.resolve(pkg, { paths: [repo] }));
  icons[style] = icons[style] || {};
  for (const [name] of list) {
    const def = mod[name];
    if (!def) { missing.push(`${style}:${name}`); continue; }
    icons[style][name] = { prefix: def.prefix, iconName: def.iconName, icon: def.icon };
  }
}
const counts = Object.fromEntries(Object.entries(icons).map(([k, v]) => [k, Object.keys(v).length]));
const js = '/* Font Awesome Pro 6 icon definitions used by the Chartmetric web app. Licensed to Chartmetric; internal use only, do not redistribute. */\n'
  + 'window.ChartmetricIcons=' + JSON.stringify({ ...icons, meta: { source: 'chartmetric/chartmetric-web-app@master usage', counts } }) + ';\n';
if (/<\/script|<!--/i.test(js)) throw new Error('icon file would break an inline <script>');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, js);
console.log(JSON.stringify({ counts, missing, kb: Math.round(js.length / 1024) }));
