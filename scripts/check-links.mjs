// Verify internal links, media, and anchors against the complete published site.
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { getPosts } from '../src/lib/blog-posts.mjs';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const origin = new URL(process.env.SITE_URL || 'https://stacx-lab.github.io').origin;
const htmlFiles = [];
const cssFiles = [];
(function walk(dir) {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) { if (f !== 'pagefind') walk(p); }
    else if (f.endsWith('.html')) htmlFiles.push(p);
    else if (f.endsWith('.css')) cssFiles.push(p);
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

// Stylesheets can hide broken font/image dependencies even when HTML links work.
const stylesheets = cssFiles.map((file) => ({ file, css: readFileSync(file, 'utf8') }));
for (const file of htmlFiles) {
  for (const [, css] of readFileSync(file, 'utf8').matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)) stylesheets.push({ file, css });
}
for (const { file, css } of stylesheets) {
  const pageUrl = new URL('/' + relative(dist, file), origin);
  for (const [, ref] of css.matchAll(/url\(['"]?([^)'"\s]+)['"]?\)/g)) {
    const resolved = new URL(ref, pageUrl);
    if (resolved.origin === origin && !target(resolved.pathname)) fail(`${relative(dist, file)}: ${ref}`);
    const postPath = pageUrl.pathname.match(/^\/blog\/[^/]+\//)?.[0];
    if (postPath && !ref.startsWith('#') && (resolved.origin !== origin || !resolved.pathname.startsWith(postPath))) fail(`Post CSS asset is not self-contained: ${ref}`);
  }
}

// A post must carry every rendering dependency in its own directory.
for (const { id, data } of getPosts()) {
  const path = `/blog/${id}/`;
  const html = readFileSync(target(path), 'utf8');
  if (!html.includes(`<h1>${data.title}</h1>`)) fail(`Post title differs from metadata: ${id}`);
  for (const [tag] of html.matchAll(/<(?:link|script|img|source|video)\b[^>]*>/g)) {
    if (tag.startsWith('<link') && !/rel="(?:stylesheet|icon|preload)"/.test(tag)) continue;
    for (const [, ref] of tag.matchAll(/(?:href|src|poster)="([^"]+)"/g)) {
      if (ref.startsWith('data:')) continue;
      const resolved = new URL(ref, origin + path);
      if (resolved.origin !== origin || !resolved.pathname.startsWith(path)) fail(`Post asset is not self-contained: ${id}: ${ref}`);
    }
  }
}

// Lab pages ship their styles in the HTML, avoiding stale CSS chunk references.
for (const route of ['/', '/projects/', '/blog/']) {
  const html = readFileSync(target(route), 'utf8');
  if (/<link[^>]+rel="stylesheet"/.test(html)) fail(`Expected inline lab styles: ${route}`);
}

// Guard the organization-site layout against accidental base-path regressions.
const routes = ['/', '/projects/', '/blog/', ...getPosts().map((post) => `/blog/${post.id}/`), '/kinex/', '/kinex/docs/', '/kinex/docs/all/'];
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
