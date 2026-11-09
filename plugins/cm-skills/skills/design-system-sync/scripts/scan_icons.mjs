import { execFileSync } from 'child_process';
const cwd = process.argv[2];
const files = execFileSync('git', ['grep', '-l', '@fortawesome/', 'origin/master', '--', '*.ts', '*.tsx', '*.js', '*.jsx'], { cwd, maxBuffer: 1 << 26 }).toString().trim().split('\n');
const used = {}; // pkg -> Map(name -> count)
const re = /import\s*(?:type\s*)?\{([^}]*)\}\s*from\s*['"](@fortawesome\/[a-z-]+-svg-icons)(?:\/(fa[A-Za-z0-9]+))?['"]/g;
const re2 = /import\s+(fa[A-Za-z0-9]+)\s+from\s*['"](@fortawesome\/[a-z-]+-svg-icons)\/(fa[A-Za-z0-9]+)['"]/g;
for (const ref of files) {
  const src = execFileSync('git', ['show', ref], { cwd, maxBuffer: 1 << 26 }).toString();
  const add = (pkg, n) => { (used[pkg] ??= new Map()).set(n, (used[pkg].get(n) ?? 0) + 1); };
  for (const m of src.matchAll(re)) for (const part of m[1].split(',')) { const n = part.trim().split(/\s+as\s+/)[0].trim(); if (/^fa[A-Z]/.test(n)) add(m[2], n); }
  for (const m of src.matchAll(re2)) add(m[2], m[3]);
}
const out = Object.fromEntries(Object.entries(used).map(([k, v]) => [k, [...v].sort((a, b) => b[1] - a[1])]));
console.log(JSON.stringify(out));
