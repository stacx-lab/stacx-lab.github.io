// Verify every internal href/src in dist/ resolves to a built file (and #anchor, when given).
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const base = (process.env.BASE_PATH || '/').replace(/\/$/, '');

const htmlFiles = [];
(function walk(dir) {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) { if (f !== 'pagefind') walk(p); }
    else if (f.endsWith('.html')) htmlFiles.push(p);
  }
})(dist);

const idsCache = new Map();
const ids = (file) => {
  if (!idsCache.has(file)) idsCache.set(file, new Set([...readFileSync(file, 'utf8').matchAll(/\sid="([^"]+)"/g)].map((m) => m[1])));
  return idsCache.get(file);
};
const target = (path) => {
  const p = join(dist, decodeURIComponent(path));
  if (existsSync(p) && statSync(p).isFile()) return p;
  if (existsSync(join(p, 'index.html'))) return join(p, 'index.html');
  return null;
};

let bad = 0;
for (const file of htmlFiles) {
  const html = readFileSync(file, 'utf8');
  for (const [, ref] of html.matchAll(/\s(?:href|src)="([^"]+)"/g)) {
    if (/^(https?:|mailto:|data:|\/\/)/.test(ref)) continue;
    const [path, hash] = ref.split('#');
    let t = file;
    if (path) {
      if (!path.startsWith(base + '/')) { console.error(`✗ ${relative(dist, file)}: ${ref} (missing base)`); bad++; continue; }
      t = target(path.slice(base.length));
      if (!t) { console.error(`✗ ${relative(dist, file)}: ${ref}`); bad++; continue; }
    }
    if (hash && t.endsWith('.html') && !ids(t).has(decodeURIComponent(hash))) {
      console.error(`✗ ${relative(dist, file)}: ${ref} (no #${hash})`); bad++;
    }
  }
}
console.log(`${htmlFiles.length} pages checked, ${bad} broken link(s)`);
process.exit(bad ? 1 : 0);
