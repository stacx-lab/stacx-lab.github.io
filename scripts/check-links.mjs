// Verify internal links, media, and anchors against the complete published site.
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const origin = new URL(process.env.SITE_URL || 'https://stacx-lab.github.io').origin;
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
const fail = (message) => { console.error(`✗ ${message}`); bad++; };
for (const file of htmlFiles) {
  const html = readFileSync(file, 'utf8');
  const pageUrl = new URL('/' + relative(dist, file).replace(/index\.html$/, ''), origin);
  for (const [, ref] of html.matchAll(/\s(?:href|src|poster)="([^"]+)"/g)) {
    const resolved = new URL(ref.replaceAll('&amp;', '&'), pageUrl);
    if (resolved.origin !== origin) continue;
    const t = target(resolved.pathname);
    if (!t) { fail(`${relative(dist, file)}: ${ref}`); continue; }
    if (resolved.hash && t.endsWith('.html') && !ids(t).has(decodeURIComponent(resolved.hash.slice(1)))) {
      fail(`${relative(dist, file)}: ${ref} (missing anchor)`);
    }
  }
}

// Guard the organization-site layout against accidental base-path regressions.
const routes = ['/', '/blog/', '/blog/who-improves-the-improver/', '/kinex/', '/kinex/docs/', '/kinex/docs/all/'];
const sitemap = readFileSync(join(dist, 'sitemap-0.xml'), 'utf8');
for (const route of routes) {
  const file = target(route);
  if (!file) { fail(`Missing route: ${route}`); continue; }
  const html = readFileSync(file, 'utf8');
  if (!html.includes(`rel="canonical" href="${origin}${route}"`)) fail(`Incorrect canonical: ${route}`);
  if (!sitemap.includes(`<loc>${origin}${route}</loc>`)) fail(`Missing sitemap entry: ${route}`);
}
if (!target('/404.html')) fail('Missing root 404 page');
if (!target('/kinex/pagefind/pagefind.js')) fail('Missing Kinex search bundle');
console.log(`${htmlFiles.length} pages checked, ${bad} broken link(s) or routing error(s)`);
process.exit(bad ? 1 : 0);
